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
from cline import CScanSplit
try:
    import readline
except ImportError:
    print 'Readline not available; no command history'

PROMPT = '> '
SEPARATORS = ' \t'

class ExpansionFailedError(Exception):
    pass


def capture_output():
    sys.stdout = UnicodeOut(sys.stdout)
    sys.stderr = UnicodeOut(sys.stderr)


class CaptureOutput():
    def __init__(self):
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        self.out = sys.stdout = SaveOut()
        self.err = sys.stderr = SaveOut()

    def restore(self):
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr

class REPL():

    def __init__(self, welcome=None):
        if welcome:
            print welcome
        self.repl()

    def get_history(self):
        try:
            n = readline.get_current_history_length()
        except NameError:
            return []
        return [readline.get_history_item(i) for i in range(1, n + 1)]

    def repl(self):
        finished = False
        while not finished:
            try:
                line = raw_input(PROMPT)
                line = CScanSplit(line, SEPARATORS, quotes='"\'`')
                if line.words:
                    if line.words[0] in ('history', 'h'):
                        print '\n'.join(self.get_history())
                    else:
                        self.expand(line)
                        go(line.words)
            except EOFError:
                print 'quit'
                finished = True

    def expand(self, line):
        i = 0
        while i < len(line.words):
            word = line.words[i]
            if line.info[i] == '`':
                wordline = CScanSplit(line.words[i], SEPARATORS, quotes='"\'')
                if wordline.words:
                     line.ExpandTerm(i, captured_go(wordline.words))
            elif len(word) > 2 and word[0] == word[-1] == '`':
                wordline = CScanSplit(word[1:-1], SEPARATORS, quotes='"\'')
                line.ExpandTerm(i, captured_go(wordline.words))
            i += 1
                

def captured_go(args):
     c = CaptureOutput()
     try:
         go(args)
         result = (' '.join(c.out.buffer)).strip()
         c.out.clear()
         c.err.clear()
         c.restore()
         print '>>>"%s"<<<' % result
         return result
     except:
         c.restore()
         raise
#         raise ExpansionFailedError('Could not expand `%s`' % ' '.join(args))
                                    


def go(args=None):
    action, args, options, parser = parse_args(args)

    if action.startswith('test'):
        cases = {
            'testcli': TestCLI,
            'testdb': TestFluidDB,
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
        execute_command_line(action, args, options, parser)


def repl_or_go():
    if len(sys.argv) < 2:
        REPL('This is fish version %s.' % VERSION)
    else:
        go()


if __name__ == '__main__':
    go_or_repl()
