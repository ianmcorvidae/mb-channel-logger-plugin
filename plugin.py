###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009-2010, James Vega
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import os
import time
from cStringIO import StringIO

import supybot.conf as conf
import supybot.world as world
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
import supybot.commands as commands
import cgi
import re
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('MBChannelLogger')

def replaceurls(text):
    urls = '(?: %s)' % '|'.join("""http https telnet gopher file wais ftp""".split())
    ltrs = r'\w'              # Letters
    gunk = r'/#~:.?+=&%@!\-'  # General/Unknown
    punc = r'.:;?\-'          # Punctuation
    any = "%(ltrs)s%(gunk)s%(punc)s" % { 'ltrs' : ltrs,
                                         'gunk' : gunk,
                                         'punc' : punc }
    url = r"""
        \b                            # start at word boundary
            %(urls)s    :             # need resource and a colon
            [%(any)s]  +?             # followed by one or more
                                      #  of any valid character, but
                                      #  be conservative and take only
                                      #  what you need to....
        (?=                           # look-ahead non-consumptive assertion
                [%(punc)s]*           # either 0 or more punctuation
                (?:   [^%(any)s]      #  followed by a non-url char
                    |                 #   or end of the string
                      $
                )
        )
        """ % {'urls' : urls,
               'any' : any,
               'punc' : punc }
    url_re = re.compile(url, re.VERBOSE | re.MULTILINE)
    return re.sub(url_re, '<a href="\g<0>">\g<0></a>', text)

class FakeLog(object):
    def flush(self):
        return
    def close(self):
        return
    def write(self, s):
        return

class MBChannelLogger(callbacks.Plugin):
    noIgnore = True
    def __init__(self, irc):
        self.__parent = super(MBChannelLogger, self)
        self.__parent.__init__(irc)
        self.lastMsgs = {}
        self.lastStates = {}
        self.logs = {}
        self.flusher = self.flush
        self.logging_disabled = {}
        world.flushers.append(self.flusher)

    def die(self):
        for log in self._logs():
            # Do we need to print out html_end() here?
            log.close()
        world.flushers = [x for x in world.flushers if x is not self.flusher]

    def logging(self, irc, msg, args, channel):
        """[<channel>]

        Tells if logging is enabled for this channel.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if not self.logging_disabled.get(channel):
            irc.reply("I'm logging %s." % channel)
        else:
            irc.reply("I'm not logging %s." % channel)
    logging = commands.wrap(logging, ['channel'])

    def off(self, irc, msg, args, channel):
        """[<channel>]

        Turns off logging for this channel.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self.logging_disabled[channel] = True
        irc.reply("Logging is off for %s." % channel)
    off = commands.wrap(off, ['channel'])

    def on(self, irc, msg, args, channel):
        """[<channel>]

        Turns on logging for this channel.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if self.logging_disabled.get(channel):
            #irc.reply("[off] Logging is on for %s." % channel)
            irc.queueMsg(ircmsgs.privmsg(channel, "[off] Logging is now on for %s."
                % channel))
            irc.noReply()
            del self.logging_disabled[channel]
        else:
            irc.reply("I'm already logging %s." % channel)
    on = commands.wrap(on, ['channel'])

    def __call__(self, irc, msg):
        try:
            # I don't know why I put this in, but it doesn't work, because it
            # doesn't call doNick or doQuit.
            # if msg.args and irc.isChannel(msg.args[0]):
            self.__parent.__call__(irc, msg)
            if irc in self.lastMsgs:
                if irc not in self.lastStates:
                    self.lastStates[irc] = irc.state.copy()
                self.lastStates[irc].addMsg(irc, self.lastMsgs[irc])
        finally:
            # We must make sure this always gets updated.
            self.lastMsgs[irc] = msg

    def reset(self):
        for log in self._logs():
            # Do We need to print out html_end() here?
            log.close()
        self.logs.clear()
        self.lastMsgs.clear()
        self.lastStates.clear()

    def _logs(self):
        for logs in self.logs.itervalues():
            for channel in logs.itervalues():
                for log in channel.itervalues():
                    yield log

    def flush(self):
        self.checkLogNames()
        for log in self._logs():
            try:
                log.flush()
            except ValueError, e:
                if e.args[0] != 'I/O operation on a closed file':
                    self.log.exception('Odd exception:')

    def logNameTimestamp(self, channel):
        format = self.registryValue('filenameTimestamp', channel)
        return time.strftime(format, time.gmtime())

    def getLogName(self, channel, fmt):
        if self.registryValue('rotateLogs', channel):
            return '%s.%s.%s' % (channel, self.logNameTimestamp(channel), fmt)
        else:
            return '%s.%s' % (channel, fmt)

    def getLogDir(self, irc, channel):
        logDir = conf.supybot.directories.log.dirize(self.name())
        if self.registryValue('directories'):
            if self.registryValue('directories.network'):
                logDir = os.path.join(logDir,  irc.network)
            if self.registryValue('directories.channel'):
                logDir = os.path.join(logDir, channel)
            if self.registryValue('directories.timestamp'):
                format = self.registryValue('directories.timestamp.format')
                timeDir =time.strftime(format, time.gmtime())
                logDir = os.path.join(logDir, timeDir)
        if not os.path.exists(logDir):
            os.makedirs(logDir)
        return logDir

    def checkLogNames(self):
        for (irc, logs) in self.logs.items():
            for (channel, formats) in logs.items():
                for (fmt, log) in formats.items():
                    if self.registryValue('rotateLogs', channel):
                        name = self.getLogName(channel, fmt)
                        if name != os.path.split(log.name)[-1]:
                            if fmt == 'html':
                                log.write(self.html_end())
                            log.close()
                            del logs[channel]

    def getLog(self, irc, channel, fmt):
        self.checkLogNames()
        try:
            logs = self.logs[irc]
        except KeyError:
            logs = ircutils.IrcDict()
            self.logs[irc] = logs
        if channel in logs and fmt in logs[channel]:
                return logs[channel][fmt]
        else:
            if channel not in logs:
                logs[channel] = {}
            try:
                name = self.getLogName(channel, fmt)
                logDir = self.getLogDir(irc, channel)
                logPath = os.path.join(logDir, name)
                writeHtml = False
                if fmt == 'html':
                    try:
                        with file(logPath, 'r') as log:
                            # Only write start_html() if it's not already there.
                            writeHtml = True
                            for line in log.readlines():
                                if re.search('<head>', line):
                                    writeHtml = False
                    except IOError:
                        writeHtml = True
                log = file(logPath, 'a')
                if writeHtml: log.write(self.html_start(channel, time.gmtime()))
                logs[channel][fmt] = log
                return log
            except IOError:
                self.log.exception('Error opening log:')
                return FakeLog()

    def timestamp(self, log, fmt):
        curtime = time.gmtime()
        lineid = time.strftime('%H-%M-%S-', curtime) + repr(time.time()).split('.')[-1]
        format = conf.supybot.log.timestampFormat()
        if fmt == 'log':
            stringfmt = '%s  ';
        elif fmt == 'html':
            stringfmt = '<a id="%s" href="#%s" class="timestamp" title="%s">%s</a> ' % (lineid, lineid, '%s', time.strftime('%H:%M:%S', curtime))
        if format:
            log.write(stringfmt % time.strftime(format, curtime))

    def normalizeChannel(self, irc, channel):
        return ircutils.toLower(channel)

    def doPreface(self, log, irc, channel, fmt, **kwargs):
        if fmt == 'html':
            if kwargs.get('cls', False):
                log.write('<p class="%s">' % kwargs.get('cls'))
            else:
                log.write('<p>')

    def doEpilogue(self, log, irc, channel, fmt, **kwargs):
        if fmt == 'html':
            log.write('</p>')
        log.write('\n')

    def html_start(self, channel, date):
        """HTML to write at the start of individual log files."""
        dateformat = self.registryValue('directories.timestamp.format')
        title = 'IRC log of {channel} on {date}'.format(**{
            'channel': channel,
            'date': time.strftime(dateformat, date),
        })
        html = """<!DOCTYPE html>
        <html>
        <head>
         <title>{title}</title>
         <link rel="stylesheet" href="/musicbrainz/style.css" type="text/css" />
         <script src="/musicbrainz/chatlogs.js" type="text/javascript"></script>
         <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        </head>
        <body>
        <h1>{title}</h1>
        <p>Timestamps are in UTC.</p>
        """.format(title = title)
        return html

    def html_end(self):
        """HTML to write at the end of individual log files."""
        html = """
        </body>
        </html>
        """
        return html

    def doLog(self, irc, channel, fmt, s, *args, **kwargs):
        if not self.registryValue('enable', channel):
            return
        s = format(s, *args)
        channel = self.normalizeChannel(irc, channel)
        log = self.getLog(irc, channel, fmt)
        self.doPreface(log, irc, channel, fmt, **kwargs)
        if self.registryValue('timestamp', channel):
            self.timestamp(log, fmt)
        if self.registryValue('stripFormatting', channel):
            s = ircutils.stripFormatting(s)
        log.write(s)
        self.doEpilogue(log, irc, channel, fmt, **kwargs)
        if self.registryValue('flushImmediately'):
            log.flush()

    def doPrivmsg(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if irc.isChannel(channel) and not self.logging_disabled.get(channel):
                noLogPrefix = self.registryValue('noLogPrefix', channel)
                if ((noLogPrefix and text.startswith(noLogPrefix)) or
                   (text.startswith('@on')) or
                   (text.startswith('mb-chat-logger: on')) or
                   (text.startswith('mb-chat-logger, on'))):
                    return
                nick = msg.nick or irc.nick
                if ircmsgs.isAction(msg):
                    self.doLog(irc, channel, 'log',
                               '* %s %s', nick, ircmsgs.unAction(msg))
                    self.doLog(irc, channel, 'html',
                               '<span>&bull; <span class="nick">%s</span> %s</span>', 
                               cgi.escape(nick),
                               replaceurls(cgi.escape(ircmsgs.unAction(msg))),
                               cls="action privmsg")
                else:
                    self.doLog(irc, channel, 'log', '<%s> %s', nick, text)
                    self.doLog(irc, channel, 'html', 
                               '<span><span class="nick">&lt;%s&gt;</span> %s</span>', 
                               cgi.escape(nick), 
                               replaceurls(cgi.escape(text)),
                               cls="privmsg")

    def doNotice(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if irc.isChannel(channel):
                self.doLog(irc, channel, 'log', '-%s- %s', msg.nick, text)
                self.doLog(irc, channel, 'html', 
                    '<span><span class="nick">-%s-</span> %s</span>', 
                    cgi.escape(msg.nick), 
                    replaceurls(cgi.escape(text)),
                    cls="notice")

    def doNick(self, irc, msg):
        oldNick = msg.nick
        newNick = msg.args[0]
        for (channel, c) in irc.state.channels.iteritems():
            if newNick in c.users:
                self.doLog(irc, channel, 'log',
                           '*** %s is now known as %s', oldNick, newNick)
                self.doLog(irc, channel, 'html',
                           '<span>&bull;&bull;&bull; <span class="nick">%s</span> is now known as <span class="nick">%s</span></span>', 
                           cgi.escape(oldNick), cgi.escape(newNick),
                           cls="nickchange")

    def doJoin(self, irc, msg):
        for channel in msg.args[0].split(','):
            self.doLog(irc, channel, 'log',
                       '*** %s <%s> has joined %s',
                       msg.nick, msg.prefix, channel)
            self.doLog(irc, channel, 'html',
                       '<span>&rarr; <span class="nick">%s</span> <span class="hostmask">&lt;%s&gt;</span> has joined <span class="channel">%s</span></span>',
                       cgi.escape(msg.nick), cgi.escape(msg.prefix), 
                       cgi.escape(channel),
                       cls="join")

    def doKick(self, irc, msg):
        if len(msg.args) == 3:
            (channel, target, kickmsg) = msg.args
        else:
            (channel, target) = msg.args
            kickmsg = ''
        if kickmsg:
            self.doLog(irc, channel, 'log',
                       '*** %s was kicked by %s (%s)',
                       target, msg.nick, kickmsg)
            self.doLog(irc, channel, 'html',
                       '<span>&larr; <span class="nick">%s</span> was kicked by <span class="nick">%s</span> <span class="kickmessage">(%s)</span></span>',
                       cgi.escape(target), cgi.escape(msg.nick), 
                       replaceurls(cgi.escape(kickmsg)),
                       cls="kick")
        else:
            self.doLog(irc, channel, 'log',
                       '*** %s was kicked by %s', target, msg.nick)
            self.doLog(irc, channel, 'html',
                       '<span>&larr; <span class="nick">%s</span> was kicked by <span class="nick">%s</span></span>',
                       cgi.escape(target), cgi.escape(msg.nick),
                       cls="kick")

    def doPart(self, irc, msg):
        if len(msg.args) > 1:
            reason = " (%s)" % msg.args[1]
        else:
            reason = ""
        for channel in msg.args[0].split(','):
            self.doLog(irc, channel, 'log', 
                       '*** %s <%s> has left %s%s',
                       msg.nick, msg.prefix, channel, reason)
            self.doLog(irc, channel, 'html', 
                       '<span>&larr; <span class="nick">%s</span> <span class="hostmask">&lt;%s&gt;</span> has left <span class="channel">%s</span><span class="reason">%s</span></span>',
                       cgi.escape(msg.nick), cgi.escape(msg.prefix), 
                       cgi.escape(channel), 
                       replaceurls(cgi.escape(reason)),
                       cls="part")

    def doMode(self, irc, msg):
        channel = msg.args[0]
        if irc.isChannel(channel) and msg.args[1:]:
            self.doLog(irc, channel, 'log',
                       '*** %s sets mode: %s %s',
                       msg.nick or msg.prefix, msg.args[1],
                        ' '.join(msg.args[2:]))
            self.doLog(irc, channel, 'html',
                       '<span>&bull;&bull;&bull; <span class="nick">%s</span> sets mode: <span class="channel">%s</span> <span class="modes">%s</span></span>',
                       cgi.escape(msg.nick or msg.prefix),
                       cgi.escape(msg.args[1]),
                       cgi.escape(' '.join(msg.args[2:])),
                       cls="modechange")

    def doTopic(self, irc, msg):
        if len(msg.args) == 1:
            return # It's an empty TOPIC just to get the current topic.
        channel = msg.args[0]
        self.doLog(irc, channel, 'log',
                   '*** %s changes topic to "%s"', msg.nick, msg.args[1])
        self.doLog(irc, channel, 'html',
                   '<span>&bull;&bull;&bull; <span class="nick">%s</span> changes topic to <span class="topic">"%s"</span></span>', 
                   cgi.escape(msg.nick), 
                   replaceurls(cgi.escape(msg.args[1])),
                   cls="topicchange")

    def doQuit(self, irc, msg):
        if len(msg.args) == 1:
            reason = " (%s)" % msg.args[0]
        else:
            reason = ""
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        for (channel, chan) in self.lastStates[irc].channels.iteritems():
            if msg.nick in chan.users:
                self.doLog(irc, channel, 'log',
                           '*** %s <%s> has quit IRC%s',
                           msg.nick, msg.prefix, reason)
                self.doLog(irc, channel, 'html',
                           '<span>&larr; <span class="nick">%s</span> <span class="hostmask">&lt;%s&gt;</span> has quit IRC<span class="reason">%s</span></span>',
                           cgi.escape(msg.nick), cgi.escape(msg.prefix), 
                           replaceurls(cgi.escape(reason)),
                           cls="quit")

    def outFilter(self, irc, msg):
        # First, process the message if it was sent with [off]
        noLogPrefix = self.registryValue('noLogPrefix', msg.args[0])
        newarg = False
        if 'inReplyTo' in msg.tags:
            msgreply = msg.tags['inReplyTo']
            if (msgreply.args[1].startswith(noLogPrefix) and
               not msg.args[1].startswith(noLogPrefix)):
                newarg = '%s %s' % (noLogPrefix, msg.args[1])

        msgnew = msg
        if newarg:
            newargs = list(msg.args)
            newargs[1] = newarg 
            msgnew = ircmsgs.IrcMsg(msg=msg, args=tuple(newargs))

        # Gotta catch my own messages *somehow* :)
        # Let's try this little trick...
        if msg.command in ('PRIVMSG', 'NOTICE'):
            # Other messages should be sent back to us.
            m = ircmsgs.IrcMsg(msg=msgnew, prefix=irc.prefix)
            self(irc, m)

        return msgnew


Class = MBChannelLogger
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
