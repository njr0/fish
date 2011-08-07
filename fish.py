#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# fish.py
#
#
# Copyright (c) Nicholas J. Radcliffe 2009-2011 and other authors specified
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

from testfish import *
import cline
try:
    import readline
except ImportError:
    if __name__ == '__main__':
        print 'Readline not available; no command history'

PROMPT = '> '
SEPARATORS = ' \t'

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
        line_go(u'sync')
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
            line_go(line)


class ExpandGo:
    def __init__(self, user=None, pwd=None, unixPaths=None, docbase=None):
        self.user = user
        self.pwd = pwd
        self.unixPaths = unixPaths
        self.docbase = docbase

    def e_go(self, lineArgs, saveOut=False):
        if lineArgs.words:
            if lineArgs.words[0] in ('history', 'h'):
                result = '\n'.join(self.get_history())
                if saveOut:
                    return result
                else:
                    print result
            else:
                self.expand(lineArgs)
                return go(lineArgs.words, self.user, self.pwd, self.unixPaths,
                          self.docbase, saveOut=saveOut)

    def expand(self, lineArgs):
        i = 0
        while i < len(lineArgs.words):
            word = lineArgs.words[i]
            if lineArgs.info[i] == '`':
                wordline = cline.CScanSplit(lineArgs.words[i], SEPARATORS,
                                            quotes='"\'')
                if wordline.words:
                     lineArgs.ExpandTerm(i, self.e_go(wordline,
                                                      saveOut=True))
            elif len(word) > 2 and word[0] == word[-1] == '`':
                wordline = cline.CScanSplit(word[1:-1], SEPARATORS,
                                            quotes='"\'')
                lineArgs.ExpandTerm(i, self.e_go(wordline, saveOut=True))
            i += 1


def line_go(line, user=None, pwd=None, unixPaths=None, docbase=None,
            saveOut=False):
    expander = ExpandGo(user, pwd, unixPaths, docbase)
    lineArgs = cline.CScanSplit(line, SEPARATORS, quotes='"\'`')
    return expander.e_go(lineArgs, saveOut=saveOut)


def go(rawargs=None, user=None, pwd=None, unixPaths=None, docbase=None,
       saveOut=False):
    action, args, options, parser = parse_args(rawargs)
    rawargs = [a.decode(DEFAULT_ENCODING) for a in sys.argv[1:]]
    if not saveOut and options.outform:
        if options.outform[0] in ('json', 'python'):
            saveOut = options.outform[0]
    if action.startswith('test') and not user:
        cases = {
            'testcli': TestCLI,
            'testdb': TestFluidinfo,
            'testutil': TestFDBUtilityFunctions,
        }
        try:
            cases = {action: cases[action]}
        except KeyError:
            pass
        suite = unittest.TestSuite()
        for c in cases.values():
            s = unittest.TestLoader().loadTestsFromTestCase(c)
            suite.addTest(s)
        v = 2 if options.hightestverbosity else 1
        unittest.TextTestRunner(verbosity=v).run(suite)
    else:
        if action == 'fish' and args:
           action, words = args[0], args[1:]
        else:
           words = args
        return execute_command_line(action, words, options, parser,
                                    user, pwd, unixPaths, docbase,
                                    saveOut=saveOut, rawargs=rawargs)


def repl_or_go():
    action, args, options, parser = parse_args(sys.argv)
    if len(args) == 0:
        REPL('This is fish version %s.' % VERSION)
    else:
        return go()


if __name__ == '__main__':
    r = repl_or_go()
    if r:
        print r

