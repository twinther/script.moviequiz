import urllib2
import re
import os

class Downloader(object):
    
    def __init__(self, cachePath):
        self.cachePath = cachePath

    def downloadQuotes(self, title, year):
        return self._downloadQuotes(title, year)

    def _downloadQuotes(self, title, year):
        return None # implemented in subclasses

    def downloadAndCacheUrl(self, url, cacheFilename):
        # TODO expire cache?
        cache = os.path.join(self.cachePath, cacheFilename)

        if os.path.exists(cache):
            f = open(cache)
            html = f.read()
            f.close()
        else:
            u = urllib2.urlopen(url)
            html = u.read()
            u.close()

            f = open(cache, 'w')
            f.write(html)
            f.close()

        return html



class MovieQuotesDownloader(Downloader):
    BASE_URL = 'http://www.moviequotes.com/%s'
    REPOSITORY_URL = BASE_URL % 'repository.cgi'
    REPOSITORY_PAGE_URL = BASE_URL % 'repository.cgi?pg=t&tt=%d'

    def _downloadQuotes(self, title, year):
        preparedTitle = self._prepareTitle(title)
        page = self._findAlphabeticalPage(preparedTitle)
        print page
        if page is None:
            return None
        url = self._findMoviePageUrl(page, preparedTitle, year)
        print url
        if url is None:
            return None

        quotes = self._findQuotes(url, title, year)
        return self._filterAndCleanup(quotes)

    def _prepareTitle(self, title):
        if title[0:4] == 'The ':
            title = title[4:] + ', The'
        return title

    def _findAlphabeticalPage(self, title):
        pages = []

        html = self.downloadAndCacheUrl(self.REPOSITORY_URL, 'repository.html')
        for m in re.finditer('<a href="(repository.cgi\?pg=t&tt=[0-9]+)" id="[^"]+">(.*?)(-(.*?))?</a>', html):
            pages.append({'url' : m.group(1), 'from' : m.group(2), 'to' : m.group(4)})

        lowercaseTitle = title.lower()
        for page in pages:
            f = page['from']
            t = page['to']
            if t is None:
                t = f

            f = f.lower()
            t = t.lower()

            if lowercaseTitle[0:len(f)] >= f and lowercaseTitle[0:len(t)] <= t:
                return page

        return None

    def _findMoviePageUrl(self, page, title, year):
        html = self.downloadAndCacheUrl(self.BASE_URL % page['url'], 'listing_%s-%s.html' % (page['from'], page['to']))
        m = re.search('<a href="(repository.cgi\?pg=[0-9]+&tt=[0-9]+)" id="[^"]+">%s - %s</a>' % (title, year), html, re.IGNORECASE)
        if m is not None:
            url = m.group(1)

            return self.BASE_URL % url
        else:
            return None


    def _findQuotes(self, url, title, year):
        cacheFilename = '%s-%s.html' % (re.sub('[^a-z]', '_', title.lower()), year)
        html = self.downloadAndCacheUrl(url, cacheFilename)
        quotes = []
        for m in re.finditer('<td class="MovLst">(.*?)<a href="fullquote', html, re.DOTALL):
            quote = m.group(1).strip()
            quote = re.sub('<br>', '\n', quote)
            quote = re.sub('<[^>]+>' , '', quote)

            quotes.append(quote)

        return quotes

    def _filterAndCleanup(self, quotes):
        filteredQuotes =  []

        for quote in quotes:
            if len(quote) <= 100:
                quote = quote[0:1].upper() + quote[1:]
                if not filteredQuotes.count(quote):
                    filteredQuotes.append(quote)

        return filteredQuotes

    def insert_quote(title, year, quote):
        params = [title, year, str(quote)]
        c = conn.cursor()
        c.execute('INSERT INTO moviequote(title, year, quote) VALUES(?, ?, ?)', params)
        conn.commit()



d = MovieQuotesDownloader('/tmp')
print d.downloadQuotes('interview with the vampire', '1994')

