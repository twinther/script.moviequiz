import mmap
import re
import random
import os
import urllib
import urllib2
import sys
import StringIO
import gzip


class Imdb(object):
    QUOTES_DOWNLOAD_URL = 'http://ftp.sunet.se/pub/tv+movies/imdb/quotes.list.gz'
#    QUOTES_DOWNLOAD_URL = 'http://localhost/~twi/VRMHOEM_DA.iso'
    QUOTES_LIST = 'quotes.list'

    def __init__(self, listsPath):
        self.path = listsPath

    def downloadFiles(self):
        u = urllib2.urlopen(self.QUOTES_DOWNLOAD_URL)
        f = open(self.QUOTES_LIST, 'wb')

        compressedStream = StringIO.StringIO(u)
        gzipper = gzip.GzipFile(fileobj=compressedStream)

	contentReceived = 0
	contentLength = int(u.info()['Content-Length'])
        while True:
            chunk = gzipper.read(8192)
            if not chunk:
		break
            contentReceived += len(chunk)
            f.write(chunk)

            percentage = int(contentReceived * 100 / contentLength)
            print 'contentReceived = %d, contentLength = %d, percentage = %d' % (contentReceived, contentLength, percentage)

        f.close()
        u.close()

        print 'Done.'

    def _downloadProgress(self, count, blockSize, totalSize):
        percent = int(count * blockSize * 100 / totalSize)

        print "%d cnt, %d blockSize, %d totalSize, percent %d" % (count, blockSize, totalSize, percent) 

#        sys.stdout.write('\rDownloading... %d%%' % percent)
#	sys.stdout.flush()


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
    i.downloadFiles()

#    q = i.getRandomQuote('Back to the Future')
#    print q
#    print '---'
#    print i.obfuscateQuote(q)
