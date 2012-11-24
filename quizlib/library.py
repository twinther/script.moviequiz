#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

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


def buildRatingsFilters(field, ratings):
    filters = list()
    for rating in ratings:
        filters.append({
            'operator' : 'isnot',
            'field' : field,
            'value' : rating
        })
    return filters

def buildOnlyWathcedFilter():
    return [{
                'operator' : 'greaterthan',
                'field' : 'playcount',
                'value' : '0'

            }]


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
        #print resp
        return json.loads(resp)

    def asList(self, key = 'movies'):
        response = self.getResponse()
        if response['result'].has_key(key):
            return self.getResponse()['result'][key]
        else:
            return list()

    def asItem(self, key = 'movies'):
        list = self.asList(key)
        if list:
            return list[0]
        else:
            return None

    def withFilters(self, filters):
        self.filters.extend(iter(filters))
        return self

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
        for title in titles:
            self.filters.append({
                'operator' : 'doesnotcontain',
                'field' : 'title',
                'value' : title
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
