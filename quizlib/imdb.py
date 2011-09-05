import re
import random
import os
import urllib2
import zlib
import threading
import time

from strings import *

import xbmc
import xbmcgui
import xbmcaddon

class Imdb(object):
    ACTOR_PATTERN = re.compile('^([^\t\(]+)( \([^\)]+\))?\t.*?$')

    QUOTES_INDEX = 'quotes.index'
    QUOTES_LIST = 'quotes.list'
    QUOTES_URL = 'http://ftp.sunet.se/pub/tv+movies/imdb/quotes.list.gz'
    ACTORS_LIST = 'actors.list'
    ACTORS_URL = 'http://ftp.sunet.se/pub/tv+movies/imdb/actors.list.gz' 

    def __init__(self, listsPath, preloadData = True):
        self.path = listsPath
        self.actorsPath = os.path.join(self.path, self.ACTORS_LIST)
        self.quotesIndexPath = os.path.join(self.path, self.QUOTES_INDEX)
        self.quotesListPath = os.path.join(self.path, self.QUOTES_LIST)

        self.actorNames = None
        self.quotesIndex = None

        if preloadData:
            ImdbLoader(self).start()

    def __del__(self):
        self.actorNames = None
        self.quotes = None


    def downloadFiles(self, progressCallback = None):
        self._downloadGzipFile(self.QUOTES_URL, self.QUOTES_LIST, progressCallback, self._createQuotesIndex)
        self._downloadGzipFile(self.ACTORS_URL, self.ACTORS_LIST, progressCallback, self._postprocessActorNames)

    def _postprocessActorNames(self, line):
        if not hasattr(self, 'previousLastnameFirstname'):
            self.previousLastnameFirstname = None

        m = self.ACTOR_PATTERN.search(line)
        if m is not None:
            lastnameFirstname = m.group(1).strip()
            if lastnameFirstname != self.previousLastnameFirstname:
                self.previousLastnameFirstname = lastnameFirstname

                parts = lastnameFirstname.split(', ', 2)
                if len(parts) == 2:
                    firstnameLastname = "%s %s\n" % (parts[1], parts[0])
                    return firstnameLastname

        return ''

    def _createQuotesIndex(self, line):
        if not hasattr(self, 'indexFile'):
            self.bytesProcessed = 0
            self.indexFile = open(os.path.join(self.path, 'quotes.index'), 'w')

        if line.startswith('#'):
            self.indexFile.write(line[2:].strip() + "\t" + str(self.bytesProcessed) + "\n")

        self.bytesProcessed += len(line)
        return line


    def _downloadGzipFile(self, url, destination, progressCallback = None, postprocessLineCallback = None):
        """
        Downloads a gzip compressed file and extracts it on the fly.

        Keyword parameters:
        url -- The full url of the gzip file
        destination -- the full path of the destination file
        progressCallback -- a callback function which is invoked periodically with progress information
        """
        response = urllib2.urlopen(url)
        file = open(os.path.join(self.path, destination), 'wb')
        decompressor = zlib.decompressobj(16+zlib.MAX_WBITS)

        partialLine = None
        contentReceived = 0
        contentLength = int(response.info()['Content-Length'])
        while True:
            chunk = response.read(8192)
            if not chunk:
                break
            contentReceived += len(chunk)
            decompressedChunk = decompressor.decompress(chunk)

            if postprocessLineCallback is not None:
                if partialLine is not None:
                    decompressedChunk = partialLine + decompressedChunk
                    partialLine = None

                lines = decompressedChunk.splitlines(True)
                processedChunk = ''
                
                for line in lines:
                    if line[-1:] == '\n': # We have a complete line
                        processedLine = postprocessLineCallback(line)
                        if processedLine != '':
                            processedChunk += processedLine
                    else: # partial line
                        partialLine = line
                file.write(processedChunk)
            
            else:
                file.write(decompressedChunk)

            if progressCallback is not None:
                percentage = int(contentReceived * 100 / contentLength)
                if not progressCallback(contentReceived, contentLength, percentage):
                    break

        file.close()
        response.close()

    def getRandomQuote(self, movie, maxLength = None):
        quotes = self._loadQuotesForMovie(movie)
        if quotes is None:
            return None

        quote = None
        retries = 0
        while retries < 10:
            retries += 1
            quote = quotes[random.randint(0, len(quotes)-1)]
            if maxLength is None or len(quote) < maxLength:
                break

        # filter and cleanup
        return re.sub('\n  ', ' ', quote)

    def _loadQuotesForMovie(self, movie):
        # find position using index
        pattern = '\n%s [^\t]+\t([0-9]+)\n[^\t]+\t([0-9]+)' % movie
        m = re.search(pattern, self.quotesIndex, re.DOTALL)
        if m is None:
            return None

        # load quotes based on position
        f = open(os.path.join(self.path, self.QUOTES_LIST))
        f.seek(int(m.group(1)))
        quotes = f.read(int(m.group(2)) - int(m.group(1)))
        f.close()

        # remove first line and split on double new lines
        return quotes[quotes.find('\n')+1:-2].split('\n\n')

    def isActor(self, name):
        if self.actorNames:
            #m = re.search('^%s$' % name, self.actorNames, re.MULTILINE)
            return name in self.actorNames
        else:
            xbmc.log("%s does not exists, has it been downloaded yet?" % self.ACTORS_LIST)
            return None

class ImdbLoader(threading.Thread):
    def __init__(self, imdb):
        super(ImdbLoader, self).__init__()
        self.imdb = imdb

    def run(self):
        if os.path.exists(self.imdb.actorsPath):
            startTime = time.time()
            f = open(self.imdb.actorsPath)
            self.imdb.actorNames = f.read().decode('iso-8859-1').splitlines()
            f.close()
            xbmc.log("Loaded %d actor names in %d seconds" % (len(self.imdb.actorNames), (time.time() - startTime)))

        if os.path.exists(self.imdb.quotesIndexPath):
            startTime = time.time()
            f = open(self.imdb.quotesIndexPath)
            self.imdb.quotesIndex = f.read()
            f.close()
            xbmc.log("Loaded %d MB quotes index in %d seconds" % (len(self.imdb.quotesIndex) / 1024000, (time.time() - startTime)))



if __name__ == '__main__':
    # this script is invoked from addon settings

    def progress(received, size, percentage):
        line1 = strings(S_RETRIEVED_X_OF_Y_MB) % (received / 1048576, size / 1048576)
        d.update(percentage, line1)
        return not d.iscanceled()


    addon = xbmcaddon.Addon(id = 'script.moviequiz')
    path = xbmc.translatePath(addon.getAddonInfo('profile'))
    if not os.path.exists(path):
        os.mkdir(path)
    i = Imdb(path, preloadData = False)

    d = xbmcgui.DialogProgress()
    try:
        d.create(strings(S_DOWNLOADING_IMDB_DATA))
        i.downloadFiles(progress)
    finally:
        d.close()
        del d
