###
# Copyright (c) 2005, Jeremiah Fincher
# Copyright (c) 2009, James Vega
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

import supybot.conf as conf
import supybot.registry as registry
#from supybot.i18n import PluginInternationalization, internationalizeDocstring
#_ = PluginInternationalization('MBChannelLogger')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('MBChannelLogger', True)

MBChannelLogger = conf.registerPlugin('MBChannelLogger')
conf.registerChannelValue(MBChannelLogger, 'enable',
    registry.Boolean(True, """Determines whether logging is enabled."""))
conf.registerGlobalValue(MBChannelLogger, 'flushImmediately',
    registry.Boolean(True, """Determines whether channel logfiles will be
    flushed anytime they're written to, rather than being buffered by the
    operating system."""))
conf.registerChannelValue(MBChannelLogger, 'stripFormatting',
    registry.Boolean(True, """Determines whether formatting characters (such
    as bolding, color, etc.) are removed when writing the logs to disk."""))
conf.registerChannelValue(MBChannelLogger, 'timestamp',
    registry.Boolean(True, """Determines whether the logs for this channel are
    timestamped with the timestamp in supybot.log.timestampFormat."""))
conf.registerChannelValue(MBChannelLogger, 'noLogPrefix',
    registry.String('[off]', """Determines what string a message should be
    prefixed with in order not to be logged.  If you don't want any such
    prefix, just set it to the empty string."""))
conf.registerChannelValue(MBChannelLogger, 'rotateLogs',
    registry.Boolean(True, """Determines whether the bot will automatically
    rotate the logs for this channel.  The bot will rotate logs when the
    timestamp for the log changes.  The timestamp is set according to
    the 'filenameTimestamp' configuration variable."""))
conf.registerChannelValue(MBChannelLogger, 'filenameTimestamp',
    registry.String('%Y-%m-%d', """Determines how to represent the timestamp
    used for the filename in rotated logs.  When this timestamp changes, the
    old logfiles will be closed and a new one started. The format characters
    for the timestamp are in the time.strftime docs at python.org.  In order
    for your logs to be rotated, you'll also have to enable
    supybot.plugins.MBChannelLogger.rotateLogs."""))

conf.registerGlobalValue(MBChannelLogger, 'directories',
    registry.Boolean(True, """Determines whether the bot will partition its
    channel logs into separate directories based on different criteria."""))
conf.registerGlobalValue(MBChannelLogger.directories, 'network',
    registry.Boolean(True, """Determines whether the bot will use a network
    directory if using directories."""))
conf.registerGlobalValue(MBChannelLogger.directories, 'channel',
    registry.Boolean(True, """Determines whether the bot will use a channel
    directory if using directories."""))
conf.registerGlobalValue(MBChannelLogger.directories, 'timestamp',
    registry.Boolean(True, """Determines whether the bot will use a timestamp
    (determined by supybot.plugins.MBChannelLogger.directories.timestamp.format)
    if using directories."""))
conf.registerGlobalValue(MBChannelLogger.directories.timestamp, 'format',
    registry.String('%Y-%m', """Determines what timestamp format will be used in
    the directory structure for channel logs if
    supybot.plugins.MBChannelLogger.directories.timestamp is True."""))
conf.registerGlobalValue(MBChannelLogger, 'cssLocation',
    registry.String('../../../../../plugins/MBChannelLogger/misc/style.css',
        """Defines the location for the log CSS file."""))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
