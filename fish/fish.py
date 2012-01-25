#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# fish.py
#
#
# Copyright (c) Nicholas J. Radcliffe 2009-2012 and other authors specified
#               in the AUTHOR
# Licence terms in LICENCE.
#
# Notes:
#
#       Credentials (username and password) are normally read from
#       a plain text credentials file, or can be passed in explicitly.
#       The code assumes ~/.fluidDBcredentials on unix and
#       fluidDBcredentials.ini in the user's home folder on Windows.
#       The format is plain text with the username on the first line
#       and the password on the second, no whitespace.
#       Any further lines are ignored.
#
# Conventions in this code:
#
# The full path to a tag might be
#
#       http://fluidDB.fluidinfo.com/tags/njr/var/rating
#
# We call
#
# http://fluidDB.fluidinfo.com/tags/njr/var/rating --- the tag URI
# /tags/njr/var/rating                             --- the full tag path
# /njr/var/rating                                  --- the absolute tag path
# /njr/var                                         --- the absolute namespace
# var/rating                                       --- the relative tag path
# rating                                           --- the short tag name
#

import sys
import cli
import fishbase
import fishlib
import cline
try:
    import readline
except ImportError:
    if __name__ == '__main__':
        print 'Readline not available; no command history'

PROMPT = '> '

class ExpansionFailedError(Exception):
    pass


#def capture_output():
#    sys.stdout = UnicodeOut(sys.stdout)
#    sys.stderr = UnicodeOut(sys.stderr)


class REPL():

    def __init__(self, welcome=None):
        if welcome:
            print welcome
        print 'Synchronizing . . .',
        cli.line_go(u'sync')
        print 'synchronized.'
        self.repl()

    def get_history(self):
        try:
            n = readline.get_current_history_length()
        except NameError:
            return []
        return [readline.get_history_item(i) for i in range(1, n + 1)]

    def repl(self):
        while True:
            try:
                line = raw_input(PROMPT)
            except EOFError:
                print 'quit'
                break
            if line.strip() in ('exit', 'quit'):
                break
            cli.line_go(line)


def fish_command(line, username=None, raiseErrors=None):
    """
        Executes a fish command without reading the cache.
        If no user is give, default credentials are used;
        if a username is given that user's credentials file is read.
    """
    cred = Credentials(username)
    cache = Cache(None)
    return cli.line_go(line, cred.username, cred.password, cache=cache,
                   raiseErrors=raiseErrors)


def command(line, username=None):
    """
        Execute a fish command.
        Print to stdout.
        Raise exception on error.
    """
    return fish_command(line, username, raiseErrors=True)


def repl_or_go():
    action, args, options, parser = cli.parse_args(sys.argv)
    if len(args) == 0 and not options.version:
        REPL('This is fish version %s.' % fishlib.VERSION)
    else:
        return cli.go()


if __name__ == '__main__':
    r = repl_or_go()
    if r:
        print r

