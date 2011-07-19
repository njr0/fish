BASE_QUOTE_CHARS = '\'"'


class CScanSplit:
    """Split a string into words using the specified separator,
        but respecting quotes and escape characters.

        Special support for / at start of line (to allow /search).

        Python rules for " and '.

        Result is:

           self.words:      list of words
           self.info:       the quoting for the word
           self.AsQuoted(): returns word list including quotes

    """

    def __init__(self, s, sep=',', escChar='\\', quotes=BASE_QUOTE_CHARS):
        self.sep = sep
        self.escChar = escChar
        self.quotes = quotes
        s = s.strip()
        wordStart = 0
        quote = None
        words = []
        info = []
        pos = 0
        escape = False
        lastInfo = None
        if len(s) > 0 and (s[0] == '/' or s[-1] == '/'):
            quoteChars = '%s/' % quotes
            if s[0] == '/':
                words.append('/')
                info.append(lastInfo)
        else:
            quoteChars = quotes
        while pos < len(s):
            if s[pos] == escChar:
                if len(s) > pos + 1 and s[pos + 1] in quoteChars:
                    s = s[:pos] + s[pos + 1:]       # delete it
                    escape = True
            if s[pos] in sep:
                if quote:
                    pass
                else:
                    words.append(s[wordStart:pos])
                    info.append(lastInfo)
                    lastInfo = None
                    wordStart = pos + 1
                    if wordStart == len(s):  # ends with blank
                        words.append('')
                        info.append(lastInfo)
                        lastInfo = None
                        wordStart = pos + 1
                    while wordStart < len(s) and s[wordStart] in sep:
                        wordStart += 1   # reduce multiple separators to one
                        pos += 1         # change for double non-whitespace??
            elif s[pos] == quote:   # matching close
                if not escape:
                    s = s[:pos] + s[pos + 1:]       # delete it
                    quote = None
                    pos -= 1  # don't want to move on
            elif s[pos] in quoteChars and not escape:  # open quote or
                                                       # other quote in quote
                if quote:   # other quote
                    pos
                else:       # open quote
                    quote = s[pos]
                    lastInfo = quote
                    s = s[:pos] + s[pos + 1:]       # delete it
                    pos -= 1  # don't want to move on
            # else:
            #    pass
            pos += 1
            escape = False

        if wordStart < pos:
            words.append(s[wordStart:pos])
            info.append(lastInfo)

        while len(words) > 0 and words[-1] == '':  # TODO: shouldn't need this.
            words = words[:-1]                     # Caused by ) etc.

        self.words = words
        self.info = info

    def AsQuoted(self):
        return [(('%s%s%s' % (info, word, info)) if info else word)
                    for word, info in zip(self.words, self.info)]

    def AsQuotedOld(self, quote='"'):
        return [(('%s%s%s' % (quote, word, quote)) if info else word)
                    for word, info in zip(self.words, self.info)]

    def ExpandTerm(self, n, expansion, leftQuotes='`'):
        """
            Replaces the word at position n with the expansion text given.
            If the term being expanded is quoted with anything other then
            one of the quote characters in leftQuotes, the expansion
            text will not be expanded and the quote will remain in place;
            if the quote character was one of leftQuotes, it will be split.
        """

        if self.info[n] and self.info[n] in leftQuotes:  # expand
            terms = CScanSplit(expansion, self.sep, self.escChar, self.quotes)
            self.words = self.words[:n] + terms.words[:] + self.words[n+1:]
            self.info = self.info[:n] + terms.info[:] + self.info[n+1:]
        else:                              # no expansion required
            self.words[n] = expansion[:]
            self.info[n] = None            # not left quoted any more!


