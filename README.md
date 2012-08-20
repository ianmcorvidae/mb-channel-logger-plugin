MBChannelLogger plugin
======================

This is a plugin for supybot that's a modification of the included ChannelLogger plugin to handle some specific needs of the #musicbrainz and #musicbrainz-devel channels on FreeNode.

Among the changes:

* Default to "&#91;off&#93;" for the noLogPrefix
* Add on/off commands to turn on/off logging completely
* Add logging command to tell if logging is on/off
* When messages are sent with noLogPrefix, don't log them at all (rather than logging a "this message not logged" message)
* When the bot responds to anything sent with noLogPrefix, have it respond with the same, so as to not leak information
* Change to logging timestamps using gmtime() rather than using localtime() implicitly
* Add a basic 'pre-html' format for logs, which can be wrapped with header/footer to make valid HTML (various &lt;span&gt; classes for different types of things, automatic adding of &lt;a&gt; to links, anchors to individual lines)
