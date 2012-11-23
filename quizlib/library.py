__author__ = 'tommy'

import xbmc
import json


def getMovies(properties  = None):
    params = {'sort' : {'method' : 'random'}}
    return Query('VideoLibrary.GetMovies', params, properties)

def getTVShows(properties = None):
    params = {'sort' : {'method' : 'random'}}
    return Query('VideoLibrary.GetTVShows', params, properties)

def getSeasons(properties = None):
    params = {'sort' : {'method' : 'random'}}
    return Query('VideoLibrary.GetSeasons', params, properties)

def getEpisodes(properties = None):
    params = {'sort' : {'method' : 'random'}}
    return Query('VideoLibrary.GetEpisodes', params, properties)

def getMovieCount():
    return getMovies().limitTo(1).getResponse()['result']['limits']['total']

def getTVShowsCount():
    return getTVShows().limitTo(1).getResponse()['result']['limits']['total']

def getSeasonsCount():
    return getSeasons().limitTo(1).getResponse()['result']['limits']['total']

def getEpisodesCount():
    return getEpisodes().limitTo(1).getResponse()['result']['limits']['total']

def hasMovies():
    return Query('XBMC.GetInfoBooleans', {'booleans' : ['Library.HasContent(Movies)']}).asList('Library.HasContent(Movies)')

def hasTVShows():
    return Query('XBMC.GetInfoBooleans', {'booleans' : ['Library.HasContent(TVShows)']}).asList('Library.HasContent(TVShows)')

def isAnyVideosWatched():
    return len(getMovies([]).minPlayCount(1).limitTo(1).asList()) > 0

def isAnyMPAARatingsAvailable():
    query = getMovies([]).limitTo(1)
    query.filters.append({
        'operator' : 'isnot',
        'field' : 'mpaarating',
        'value' : ''
    })
    return len(query.asList()) > 0

def isAnyContentRatingsAvailable():
    query = getTVShows([]).limitTo(1)
    query.filters.append({
        'operator' : 'isnot',
        'field' : 'rating',
        'value' : ''
    })
    return len(query.asList('tvshows')) > 0





class Query(object):
    def __init__(self, method, params, properties = None, id = 1):
        self.properties = properties
        self.params = params
        self.filters = list()
        self.query = {
            'jsonrpc' : '2.0',
            'id' : id,
            'method' : method
        }

    def getResponse(self):
        if self.filters:
            self.params['filter'] = {'and' : self.filters}
        if self.properties:
            self.params['properties'] = self.properties
        if self.params:
            self.query['params'] = self.params

        command = json.dumps(self.query)
        resp = xbmc.executeJSONRPC(command)
        print resp
        return json.loads(resp)

    def asList(self, key = 'movies'):
        return self.getResponse()['result'][key]

    def asItem(self, key = 'movies'):
        list = self.asList(key)
        if list:
            return list[0]
        else:
            return None

    def inSet(self, set):
        self.filters.append({
            'operator' : 'is',
            'field' : 'set',
            'value' : set
        })
        return self

    def inGenre(self, genre):
        self.filters.append({
            'operator' : 'contains',
            'field' : 'genre',
            'value' : genre
        })
        return self

    def excludeTitles(self, titles):
        self.filters.append({
            'operator' : 'doesnotcontain',
            'field' : 'title',
            'value' : titles
        })
        return self

    def withActor(self, actor):
        self.filters.append({
            'operator' : 'is',
            'field' : 'actor',
            'value' : actor
        })
        return self

    def withoutActor(self, actor):
        self.filters.append({
            'operator' : 'isnot',
            'field' : 'actor',
            'value' : actor
        })
        return self

    def fromYear(self, fromYear):
        self.filters.append({
            'operator' : 'greaterthan',
            'field' : 'year',
            'value' : str(fromYear)
        })
        return self

    def toYear(self, toYear):
        self.filters.append({
            'operator' : 'lessthan',
            'field' : 'year',
            'value' : str(toYear)
        })
        return self

    def directedBy(self, directedBy):
        self.filters.append({
            'operator' : 'is',
            'field' : 'director',
            'value' : directedBy
        })
        return self

    def notDirectedBy(self, notDirectedBy):
        self.filters.append({
            'operator' : 'isnot',
            'field' : 'director',
            'value' : str(notDirectedBy)
        })
        return self

    def minPlayCount(self, playCount):
        self.filters.append({
            'operator' : 'greaterthan',
            'field' : 'playcount',
            'value' : str(playCount - 1)
        })
        return self

    def limitTo(self, end):
        self.params['limits'] = {'start' : 0, 'end' : end}
        return self

    def limitToMPAARating(self, rating):
        self.filters.append({
            'operator' : 'isnot',
            'field' : 'mpaarating',
            'value' : rating
        })
        return self
