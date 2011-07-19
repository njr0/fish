from artists.giacometti.cline import CScanSplit
try:
    import readline
except ImportError:
    print 'Readline not available; no command history'

prompt = '> '
sep = ' \t'

class REPL():

    def __init__(self, welcome=None):
        if welcome:
            print welcome
        self.repl()

    def repl(self):
        finished = False
        while not finished:
            try:
                line = raw_input(prompt)
            except EOFError:
                finished = True
            s = CScanSplit(line, sep, quotes='"\'`')
            print 'Words:', s.words
            print 'Info:', s.info
            print s.AsQuoted()

REPL('This is a test version 0.0.1.')

    
