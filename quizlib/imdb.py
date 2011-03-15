import mmap
import re
import random
import os


class Imdb(object):
    QUOTES_DOWNLOAD_URL = 'http://ftp.sunet.se/pub/tv+movies/imdb/quotes.list.gz'
    QUOTES_LIST = 'quotes.list'

    def __init__(self, listsPath):
        self.path = listsPath

    def getRandomQuote(self, movie):
        quotes = self._parseMovieQuotes(movie)
        quote = quotes[random.randint(0, len(quotes)-1)]
        return quote

    def obfuscateQuote(self, quote):
        names = list()
        for m in re.finditer('(.*?\:)', quote):
            name = m.group(1)
            if not name in names:
                names.append(name)

        print names
        for idx, name in enumerate(names):
            repl = '#%d:' % (idx + 1)
            quote = quote.replace(name, repl)

        return quote

    def _parseMovieQuotes(self, movie):
        pattern = '\n# %s [^\n]+\n(.*?)\n\n#' % movie

        path = os.path.join(self.path, self.QUOTES_LIST)
        f = open(path)
        data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        m = re.search(pattern, data, re.DOTALL)
        quotes = m.group(1).split('\n\n')
        data.close()
        f.close()

        return quotes

if __name__ == '__main__':
    i = Imdb('/home/tommy/development/')
    q = i.getRandomQuote('Back to the Future')
    print q
    print '---'
    print i.obfuscateQuote(q)