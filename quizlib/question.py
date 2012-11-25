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

import os
import random
import datetime
import thumb
import db
import time
import re
import imdb
import game
import library

import xbmcvfs

from strings import *

IMDB = imdb.Imdb()

class Answer(object):
    def __init__(self, id, text, image = None, sortWeight = None, correct = False):
        self.correct = correct
        self.id = id
        self.text = text
        self.coverFile = image
        self.sortWeight = sortWeight

    def setCoverFile(self, path, filename = None):
        if filename is None:
            self.coverFile = path
        else:
            self.coverFile = thumb.getCachedVideoThumb(path, filename)

    def __repr__(self):
        return "<Answer(id=%s, text=%s, correct=%s)>" % (self.id, self.text, self.correct)

class Question(object):
    def __init__(self, displayType = None):
        """
        Base class for Questions

        @type displayType: DisplayType
        @param displayType:
        """
        self.answers = list()
        self.text = None
        self.fanartFile = None
        self.displayType = displayType

    def getText(self):
        return self.text

    def getAnswers(self):
        return self.answers

    def getAnswer(self, idx):
        try:
            return self.answers[idx]
        except IndexError:
            return None

    def addCorrectAnswer(self, id, text, image = None, sortWeight = None):
        self.addAnswer(id, text, image, sortWeight, correct = True)

    def addAnswer(self, id, text, image = None, sortWeight = None, correct = False):
        a = Answer(id, text, image, sortWeight, correct)
        self.answers.append(a)


    def getCorrectAnswer(self):
        for answer in self.answers:
            if answer.correct:
                return answer
        return None

    def getUniqueIdentifier(self):
        return "%s-%s" % (self.__class__.__name__, str(self.getCorrectAnswer().id))

    def setFanartFile(self, fanartFile):
        self.fanartFile = fanartFile

    def getFanartFile(self):
        return self.fanartFile

    def getDisplayType(self):
        return self.displayType

    @staticmethod
    def isEnabled():
        raise

    def _getMovieIds(self):
        movieIds = list()
        for movie in self.answers:
            movieIds.append(str(movie.id))
        return movieIds

    def getAnswerTexts(self):
        texts = list()
        for answer in self.answers:
            texts.append(answer.text)
        return texts

    def _isAnimationGenre(self, genre):
        return "Animation" in genre # todo case insensitive

#
# DISPLAY TYPES
#

class DisplayType(object):
    pass

class VideoDisplayType(DisplayType):
    def setVideoFile(self, videoFile, resumePoint):
        self.videoFile = videoFile
        self.resumePoint = resumePoint
        if not xbmcvfs.exists(self.videoFile):
            raise QuestionException('Video file not found: %s' % self.videoFile.encode('utf-8', 'ignore'))

    def getVideoFile(self):
        return self.videoFile

    def getResumePoint(self):
        return self.resumePoint

class PhotoDisplayType(DisplayType):
    def setPhotoFile(self, photoFile):
        self.photoFile = photoFile

    def getPhotoFile(self):
        return self.photoFile

class ThreePhotoDisplayType(DisplayType):
    def addPhoto(self, photo, label):
        if not hasattr(self, 'photos'):
            self.photos = list()

        self.photos.append((photo, label))

    def getPhotoFile(self, index):
        return self.photos[index]

class QuoteDisplayType(DisplayType):
    def setQuoteText(self, quoteText):
        self.quoteText = quoteText

    def getQuoteText(self):
        return self.quoteText

class AudioDisplayType(DisplayType):
    def setAudioFile(self, audioFile):
        self.audioFile = audioFile

    def getAudioFile(self):
        return self.audioFile

#
# MOVIE QUESTIONS
#

class MovieQuestion(Question):
    pass

class WhatMovieIsThisQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        What movie is this?
        """
        videoDisplayType = VideoDisplayType()
        super(WhatMovieIsThisQuestion, self).__init__(videoDisplayType)

        correctAnswer = library.getMovies(['title', 'set', 'genre', 'file', 'resume', 'art']).withFilters(defaultFilters).limitTo(1).asItem()
        if not correctAnswer:
            raise QuestionException('No movies found')

        self.addCorrectAnswer(id = correctAnswer['movieid'], text = correctAnswer['title'], image = correctAnswer['art']['poster'])

        # Find other movies in set
        if correctAnswer['set'] is not None:
            otherMoviesInSet = library.getMovies(['title', 'art']).withFilters(defaultFilters).inSet(correctAnswer['set']).excludeTitles(self.getAnswerTexts()).limitTo(3).asList()
            for movie in otherMoviesInSet:
                self.addAnswer(id = movie['movieid'], text = movie['title'], image = movie['art']['poster'])

        # Find other movies in genre
        if len(self.answers) < 4:
            try:
                otherMoviesInGenre = library.getMovies(['title', 'art']).withFilters(defaultFilters).inGenre(correctAnswer['genre']).excludeTitles(self.getAnswerTexts()).limitTo(4 - len(self.answers)).asList()
                for movie in otherMoviesInGenre:
                    self.addAnswer(id = movie['movieid'], text = movie['title'], image = movie['art']['poster'])
            except db.DbException:
                pass # ignore in case user has no other movies in genre

        # Fill with random movies
        if len(self.answers) < 4:
            theRest = library.getMovies(['title', 'art']).withFilters(defaultFilters).excludeTitles(self.getAnswerTexts()).limitTo(4 - len(self.answers)).asList()
            for movie in theRest:
                self.addAnswer(id = movie['movieid'], text = movie['title'], image = movie['art']['poster'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS)
        videoDisplayType.setVideoFile(correctAnswer['file'], correctAnswer['resume']['position'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisthis.enabled') == 'true'

class WhatActorIsThisQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatActorIsThisQuestion
        """
        photoDisplayType = PhotoDisplayType()
        super(WhatActorIsThisQuestion, self).__init__(photoDisplayType)

        # Find a bunch of actors with thumbnails
        actors = list()
        names = list()
        for movie in library.getMovies(['cast']).withFilters(defaultFilters).limitTo(10).asList():
            for actor in movie['cast']:
                if actor.has_key('thumbnail') and actor['name'] not in names:
                    actors.append(actor)
                    names.append(actor['name'])

        if not actors:
            raise QuestionException("Didn't find any actors with thumbnail")

        random.shuffle(actors)
        actor = actors.pop()

        # The actor
        self.addCorrectAnswer(id = actor['name'], text = actor['name'])

        # Check gender
        actorGender = IMDB.isActor(actor['name'])

        for otherActor in actors:
            if IMDB.isActor(otherActor['name']) == actorGender:
                self.addAnswer(otherActor['name'], otherActor['name'])
                if len(self.answers) == 4:
                    break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_THIS)
        photoDisplayType.setPhotoFile(actor['thumbnail'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactoristhis.enabled') == 'true'


class ActorNotInMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        Actor not in movie?
        """
        photoDisplayType = PhotoDisplayType()
        super(ActorNotInMovieQuestion, self).__init__(photoDisplayType)

        actors = list()
        for movie in library.getMovies(['cast']).withFilters(defaultFilters).limitTo(10).asList():
            for actor in movie['cast']:
                if actor.has_key('thumbnail'):
                    actors.append(actor)

        if not actors:
            raise QuestionException("Didn't find any actors with thumbnail")

        random.shuffle(actors)

        actor = None
        for actor in actors:
            # Movie actor is in
            movies = library.getMovies(['title', 'art']).withFilters(defaultFilters).withActor(actor['name']).limitTo(3).asList()
            if len(movies) < 3:
                continue

            for movie in movies:
                self.addAnswer(-1, movie['title'], image = movie['art']['poster'])

            # Movies actor is not in
            correctAnswer = library.getMovies(['title', 'art']).withFilters(defaultFilters).withoutActor(actor['name']).limitTo(1).asItem()
            if not correctAnswer:
                raise QuestionException('No movies found')
            self.addCorrectAnswer(actor['name'], correctAnswer['title'], image = correctAnswer['art']['poster'])

            break

        if not self.answers:
            raise QuestionException("Didn't find any actors with at least three movies")

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_ACTOR_NOT_IN, actor['name'])
        photoDisplayType.setPhotoFile(actor['thumbnail'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.actornotinmovie.enabled') == 'true'


class WhatYearWasMovieReleasedQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatYearWasMovieReleasedQuestion
        """
        super(WhatYearWasMovieReleasedQuestion, self).__init__()

        movie = library.getMovies(['title', 'year', 'art']).withFilters(defaultFilters).fromYear(1900).limitTo(1).asItem()
        if not movie:
            raise QuestionException('No movies found')

        skew = random.randint(0, 10)
        minYear = int(movie['year']) - skew
        maxYear = int(movie['year']) + (10 - skew)

        thisYear = datetime.datetime.today().year
        if maxYear > thisYear:
            maxYear = thisYear
            minYear = thisYear - 10

        years = list()
        years.append(int(movie['year']))
        while len(years) < 4:
            year = random.randint(minYear, maxYear)
            if not year in years:
                years.append(year)

        list.sort(years)

        for year in years:
            self.addAnswer(id = movie['movieid'], text= str(year), correct = (year == int(movie['year'])))

        self.text = strings(Q_WHAT_YEAR_WAS_MOVIE_RELEASED, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatyearwasmoviereleased.enabled') == 'true'


class WhatTagLineBelongsToMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatTagLineBelongsToMovieQuestion
        """
        super(WhatTagLineBelongsToMovieQuestion, self).__init__()

        movie = None
        items = library.getMovies(['title', 'tagline', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item['tagline']:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')
        self.addCorrectAnswer(id = movie['movieid'], text = movie['tagline'])

        otherMovies = library.getMovies(['tagline']).withFilters(defaultFilters).excludeTitles(movie['title']).limitTo(10).asList()
        for otherMovie in otherMovies:
            if not otherMovie['tagline']:
                continue

            self.addAnswer(id = otherMovie['movieid'], text = otherMovie['tagline'])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TAGLINE_BELONGS_TO_MOVIE, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattaglinebelongstomovie.enabled') == 'true'


class WhatStudioReleasedMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatStudioReleasedMovieQuestion
        """
        super(WhatStudioReleasedMovieQuestion, self).__init__()

        movie = None
        items = library.getMovies(['title', 'studio', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item['studio']:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')

        studio = random.choice(movie['studio'])
        self.addCorrectAnswer(id = movie['movieid'], text = studio)

        otherMovies = library.getMovies(['studio']).withFilters(defaultFilters).excludeTitles(movie['title']).limitTo(10).asList()
        for otherMovie in otherMovies:
            if not otherMovie['studio']:
                continue

            studioFound = False
            for otherStudio in otherMovie['studio']:
                if otherStudio in self.getAnswerTexts():
                    studioFound = True
                    break

            if studioFound:
                continue

            self.addAnswer(id = otherMovie['movieid'], text = random.choice(otherMovie['studio']))
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_STUDIO_RELEASED_MOVIE, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatstudioreleasedmovie.enabled') == 'true'


class WhoPlayedRoleInMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhoPlayedRoleInMovieQuestion
        """
        super(WhoPlayedRoleInMovieQuestion, self).__init__()

        movie = None
        items = library.getMovies(['title', 'cast', 'genre', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if len(item['cast']) < 4:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No applicable movie found')

        actor = random.choice(movie['cast'])
        role = actor['role']
        # TODO nessecary? if re.search('[|/]', role):
        #    roles = re.split('[|/]', role)
            # find random role
        #    role = roles[random.randint(0, len(roles)-1)]

        self.addCorrectAnswer(actor['name'], actor['name'], image = actor['thumbnail'])

        for otherActor in movie['cast']:
            if otherActor['name'] == actor['name']:
                continue

            self.addAnswer(otherActor['name'], otherActor['name'], image = otherActor['thumbnail'])

            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)

        if self._isAnimationGenre(movie['genre']):
            self.text = strings(Q_WHO_VOICES_ROLE_IN_MOVIE) % (role, movie['title'])
        else:
            self.text = strings(Q_WHO_PLAYS_ROLE_IN_MOVIE) % (role, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whoplayedroleinmovie.enabled') == 'true'


class WhatMovieIsThisQuoteFrom(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatQuoteIsThisFrom
        """
        quoteDisplayType = QuoteDisplayType()
        super(WhatMovieIsThisQuoteFrom, self).__init__(quoteDisplayType)

        quoteText = None
        row = None
        for item in library.getMovies(['title', 'art']).withFilters(defaultFilters).limitTo(10).asList():
            quoteText = IMDB.getRandomQuote(item['title'], maxLength = 128)

            if quoteText is not None:
                row = item
                break

        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        self.addCorrectAnswer(row['movieid'], row['title'], image = row['art']['poster'])

        theRest = library.getMovies(['title', 'art']).withFilters(defaultFilters).excludeTitles(self.getAnswerTexts()).limitTo(3).asList()
        for movie in theRest:
            self.addAnswer(movie['movieid'], movie['title'], image = movie['art']['poster'])

        random.shuffle(self.answers)
        quoteDisplayType.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS_QUOTE_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisthisquotefrom.enabled') == 'true' and IMDB.isDataPresent()


class WhatMovieIsNewestQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatMovieIsNewestQuestion
        """
        super(WhatMovieIsNewestQuestion, self).__init__()

        movie = library.getMovies(['title', 'year', 'art']).withFilters(defaultFilters).fromYear(1900).limitTo(1).asItem()
        if not movie:
            raise QuestionException('No movies found')

        self.addCorrectAnswer(id = movie['movieid'], text = movie['title'], image = movie['art']['poster'])

        otherMovies = library.getMovies(['title', 'art']).withFilters(defaultFilters).fromYear(1900).toYear(movie['year']).limitTo(3).asList()
        if len(otherMovies) < 3:
            raise QuestionException("Less than 3 movies found; bailing out")

        for otherMovie in otherMovies:
            self.addAnswer(otherMovie['movieid'], otherMovie['title'], image = otherMovie['art']['poster'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THE_NEWEST)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisnewest.enabled') == 'true'


class WhoDirectedThisMovieQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhoDirectedThisMovieQuestion
        """
        super(WhoDirectedThisMovieQuestion, self).__init__()

        movie = None
        items = library.getMovies(['title', 'director', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            if not item['director']:
                continue

            movie = item
            break

        if not movie:
            raise QuestionException('No movies found')

        director = random.choice(movie['director'])
        self.addCorrectAnswer(id = movie['movieid'], text = director)

        otherMovies = library.getMovies(['director']).withFilters(defaultFilters).excludeTitles(movie['title']).limitTo(10).asList()
        for otherMovie in otherMovies:
            if not otherMovie['director']:
                continue

            directorFound = False
            for otherDirector in otherMovie['director']:
                if otherDirector in self.getAnswerTexts():
                    directorFound = True
                    break

            if directorFound:
                continue

            self.addAnswer(id = otherMovie['movieid'], text = random.choice(otherMovie['director']))
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_DIRECTED_THIS_MOVIE, movie['title'])
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whodirectedthismovie.enabled') == 'true'



class WhatMovieIsNotDirectedByQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatMovieIsNotDirectedByQuestion
        """
        super(WhatMovieIsNotDirectedByQuestion, self).__init__()

        # Find a bunch of directors
        directors = list()
        items = library.getMovies(['title', 'director']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            directors.extend(iter(item['director']))

        # Find one that has at least three movies
        movies = None
        director = None
        for director in directors:
#            if not director['thumbnail']:
#                continue
            movies = library.getMovies(['title', 'art']).withFilters(defaultFilters).directedBy(director).limitTo(3).asList()

            if len(movies) >= 3:
                break

        if len(movies) < 3:
            raise QuestionException("Didn't find a director with at least three movies")

        # Find movie not directed by director
        otherMovie = library.getMovies(['title', 'art']).withFilters(defaultFilters).notDirectedBy(director).limitTo(1).asItem()
        if not otherMovie:
            raise QuestionException('No movie found')
        self.addCorrectAnswer(director, otherMovie['title'], image = otherMovie['art']['poster'])

        for movie in movies:
            self.addAnswer(-1, movie['title'], image = movie['art']['poster'])

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_NOT_DIRECTED_BY, director)
        # todo perhaps set fanart instead?

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmovieisnotdirectedby.enabled') == 'true'


class WhatActorIsInTheseMoviesQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatActorIsInTheseMoviesQuestion
        """
        threePhotoDisplayType = ThreePhotoDisplayType()
        super(WhatActorIsInTheseMoviesQuestion, self).__init__(threePhotoDisplayType)

        # Find a bunch of actors
        actors = list()
        items = library.getMovies(['title', 'cast']).withFilters(defaultFilters).limitTo(10).asList()
        for item in items:
            actors.extend(iter(item['cast']))

        # Find one that has at least three movies
        movies = None
        actor = None
        for actor in actors:
            if not actor.has_key('thumbnail'):
                continue
            movies = library.getMovies(['title', 'art']).withFilters(defaultFilters).withActor(actor['name']).limitTo(3).asList()

            if len(movies) >= 3:
                break

        if len(movies) < 3:
            raise QuestionException("Didn't find an actor with at least three movies")

        # Setup the display with three movies
        for movie in movies:
            threePhotoDisplayType.addPhoto(movie['art']['poster'], movie['title'])

        # Find movie without actor
        otherMovie = library.getMovies(['title', 'art']).withFilters(defaultFilters).withoutActor(actor['name']).limitTo(1).asItem()
        if not otherMovie:
            raise QuestionException('No movie found')
        self.addCorrectAnswer(actor['name'], actor['title'], image = actor['thumbnail'])

        # Find another bunch of actors
        actors = list()
        items = library.getMovies(['title', 'cast']).withFilters(defaultFilters).withoutActor(actor['name']).limitTo(10).asList()
        for item in items:
            actors.extend(iter(item['cast']))

        random.shuffle(actors)
        for actor in actors:
            if not actor.has_key('thumbnail'):
                continue
            self.addAnswer(-1, actor['name'], image = actor['thumbnail'])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_IN_THESE_MOVIES)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactorisinthesemovies.enabled') == 'true'


class WhatActorIsInMovieBesidesOtherActorQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatActorIsInMovieBesidesOtherActorQuestion
        """
        super(WhatActorIsInMovieBesidesOtherActorQuestion, self).__init__()

        # Find a bunch of movies
        items = library.getMovies(['title', 'cast', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        movie = None
        for item in items:
            if len(item['cast']) >= 2:
                movie = item
                break

        if not movie:
            raise QuestionException('No movies with two actors found')

        actors = movie['cast']
        random.shuffle(actors)
        actorOne = actors[0]
        actorTwo = actors[1]
        self.addCorrectAnswer(actorOne['name'], actorOne['name'], image = actorOne['thumbnail'])

        # Find another bunch of actors
        otherActors = list()
        items = library.getMovies(['title', 'cast']).withFilters(defaultFilters).withoutActor(actorOne['name']).withoutActor(actorTwo['name']).limitTo(10).asList()
        for item in items:
            otherActors.extend(iter(item['cast']))
        random.shuffle(otherActors)

        for otherActor in otherActors:
            if not otherActor.has_key('thumbnail'):
                continue
            self.addAnswer(otherActor['name'], otherActor['name'], image = otherActor['thumbnail'])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_IN_MOVIE_BESIDES_OTHER_ACTOR, (movie['title'], actorTwo['name']))
        self.setFanartFile(movie['art']['fanart'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatactorisinmoviebesidesotheractor.enabled') == 'true'

class WhatMovieHasTheLongestRuntimeQuestion(MovieQuestion):
    def __init__(self, defaultFilters):
        """
        WhatMovieHasTheLongestRuntimeQuestion
        """
        super(WhatMovieHasTheLongestRuntimeQuestion, self).__init__()

        # Find a bunch of movies
        items = library.getMovies(['title', 'runtime', 'art']).withFilters(defaultFilters).limitTo(10).asList()
        movie = None
        otherMovies = list()
        for item in items:
            if movie is None or movie['runtime'] < item['runtime']:
                movie = item
            else:
                otherMovies.append(item)

        if not movie or len(otherMovies) < 3:
            raise QuestionException('Not enough movies found')

        self.addCorrectAnswer(id = movie['movieid'], text = movie['title'], image = movie['art']['poster'])

        for otherMovie in otherMovies:
            self.addAnswer(id = otherMovie['movieid'], text = otherMovie['title'], image = otherMovie['art']['poster'])
            if len(self.answers) == 4:
                break

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_HAS_THE_LONGEST_RUNTIME)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatmoviehaslongestruntime.enabled') == 'true'

#
# TV QUESTIONS
#

class TVQuestion(Question):
    def __init__(self, displayType = None):
        """

        @type displayType: DisplayType
        """
        super(TVQuestion, self).__init__(displayType)

    def _get_season_title(self, season):
        if not int(season):
            return strings(Q_SPECIALS)
        else:
            return strings(Q_SEASON_NO) % int(season)

    def _get_episode_title(self, season, episode, title):
        return "%dx%02d - %s" % (int(season), int(episode), title)


class WhatTVShowIsThisQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhatTVShowIsThisQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        videoDisplayType  = VideoDisplayType()
        super(WhatTVShowIsThisQuestion, self).__init__(videoDisplayType)

        shows = database.getTVShows(maxResults = 1)
        if not shows:
            raise QuestionException('No tvshows found')
        row = shows[0]
        self.addCorrectAnswer(row['idShow'], row['title'], row['idFile'], path = thumb.getCachedTVShowThumb(row['tvShowPath']))

        # Fill with random episodes from other shows
        shows = database.getTVShows(maxResults = 3, excludeTVShowId = row['idShow'], onlySelectTVShow = True)
        for show in shows:
            self.addAnswer(show['idShow'], show['title'], path = thumb.getCachedTVShowThumb(show['tvShowPath']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS)
        videoDisplayType.setVideoFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthis.enabled') == 'true'


class WhatSeasonIsThisQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhatSeasonIsThisQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        videoDisplayType  = VideoDisplayType()
        super(WhatSeasonIsThisQuestion, self).__init__(videoDisplayType)

        rows = database.getTVShowSeasons(maxResults = 1, minSeasonCount = 3)
        if not rows:
            raise QuestionException('No tvshow seasons found')
        row = rows[0]
        cover = thumb.getCachedSeasonThumb(row['strPath'], self._get_season_title(row['season']))
        self.addCorrectAnswer("%s-%s" % (row['idShow'], row['season']), self._get_season_title(row['season']), row['idFile'], path = cover, sortWeight = row['season'])

        # Fill with random seasons from this show
        shows = database.getTVShowSeasons(maxResults = 3, onlySelectSeason = True, showId = row['idShow'], excludeSeason = row['season'])
        for show in shows:
            cover = thumb.getCachedSeasonThumb(row['strPath'], self._get_season_title(show['season']))
            self.addAnswer("%s-%s" % (row['idShow'], show['season']), self._get_season_title(show['season']), path = cover, sortWeight = show['season'])

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_SEASON_IS_THIS) % row['title']
        videoDisplayType.setVideoFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatseasonisthis.enabled') == 'true'


class WhatEpisodeIsThisQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhatEpisodeIsThisQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        videoDisplayType  = VideoDisplayType()
        super(WhatEpisodeIsThisQuestion, self).__init__(videoDisplayType)

        rows = database.getTVShowEpisodes(maxResults = 1, minEpisodeCount = 3)
        if not rows:
            raise QuestionException('No tvshow episodes found')
        row = rows[0]
        answerText = self._get_episode_title(row['season'], row['episode'], row['episodeTitle'])
        id = "%s-%s-%s" % (row['idShow'], row['season'], row['episode'])
        cover = thumb.getCachedTVShowThumb(row['strPath'])
        self.addCorrectAnswer(id, answerText, row['idFile'], path = cover, sortWeight = row['episode'])

        # Fill with random episodes from this show
        episodes = database.getTVShowEpisodes(maxResults = 3, idShow = row['idShow'], season = row['season'], excludeEpisode = row['episode'])
        for episode in episodes:
            answerText = self._get_episode_title(episode['season'], episode['episode'], episode['episodeTitle'])
            id = "%s-%s-%s" % (row['idShow'], row['season'], episode['episode'])
            cover = thumb.getCachedTVShowThumb(row['strPath'])
            self.addAnswer(id, answerText, path = cover, sortWeight = episode['episode'])

        self.answers = sorted(self.answers, key=lambda answer: int(answer.sortWeight))

        self.text = strings(Q_WHAT_EPISODE_IS_THIS) % row['title']
        videoDisplayType.setVideoFile(row['strPath'], row['strFileName'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whatepisodeisthis.enabled') == 'true'


class WhenWasTVShowFirstAiredQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhenWasTVShowFirstAiredQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        super(WhenWasTVShowFirstAiredQuestion, self).__init__()

        rows = database.getTVShows(maxResults = 1, excludeSpecials = True, episode = 1, mustHaveFirstAired = True)
        if not rows:
            raise QuestionException('no tvshows found')
        row = rows[0]
        row['year'] = time.strptime(row['firstAired'], '%Y-%m-%d').tm_year

        skew = random.randint(0, 10)
        minYear = int(row['year']) - skew
        maxYear = int(row['year']) + (10 - skew)

        thisYear = datetime.datetime.today().year
        if maxYear > thisYear:
            maxYear = thisYear
            minYear = thisYear - 10

        years = list()
        years.append(int(row['year']))
        while len(years) < 4:
            year = random.randint(minYear, maxYear)
            if not year in years:
                years.append(year)

        list.sort(years)

        for year in years:
            coverFile = thumb.getCachedTVShowThumb(row['strPath'])
            self.addAnswer(row['idFile'], str(year), row['idFile'], path = coverFile, correct = (year == int(row['year'])))

        self.text = strings(Q_WHEN_WAS_TVSHOW_FIRST_AIRED) % (row['title'] + ' - ' + self._get_season_title(row['season']))
        self.setFanartFile(row['strPath'])

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whenwastvshowfirstaired.enabled') == 'true'


class WhoPlayedRoleInTVShowQuestion(TVQuestion):
    def __init__(self, database):
        """
        WhoPlayedRoleInTVShowQuestion

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        photoDisplayType = PhotoDisplayType()
        super(WhoPlayedRoleInTVShowQuestion, self).__init__(photoDisplayType)

        rows = database.getTVShowActors(maxResults = 1, mustHaveRole = True)
        if not rows:
            raise QuestionException('No tvshow actors found')
        row = rows[0]
        role = row['strRole']
        if re.search('[|/]', role):
            roles = re.split('[|/]', role)
            # find random role
            role = roles[random.randint(0, len(roles)-1)]

        self.addCorrectAnswer(row['idActor'], row['strActor'], path = thumb.getCachedActorThumb(row['strActor']))

        actors = database.getTVShowActors(maxResults = 3, onlySelectActor = True, showId = row['idShow'], excludeActorId = row['idActor'])
        for actor in actors:
            self.addAnswer(actor['idActor'], actor['strActor'], path = thumb.getCachedActorThumb(actor['strActor']))

        random.shuffle(self.answers)

        if self._isAnimationGenre(row['genre']):
            self.text = strings(Q_WHO_VOICES_ROLE_IN_TVSHOW) % (role, row['title'])
        else:
            self.text = strings(Q_WHO_PLAYS_ROLE_IN_TVSHOW) % (role, row['title'])
        photoDisplayType.setPhotoFile(thumb.getCachedTVShowThumb(row['strPath']))

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whoplayedroleintvshow.enabled') == 'true'

class WhatTVShowIsThisQuoteFrom(TVQuestion):
    def __init__(self, database):
        """
        WhatTVShowIsThisQuoteFrom

        @type database: quizlib.db.Database
        @param database: Database connection instance to use
        """
        quoteDisplayType = QuoteDisplayType()
        super(WhatTVShowIsThisQuoteFrom, self).__init__(quoteDisplayType)

        rows = database.getTVShows(maxResults = 1)
        if not rows:
            raise QuestionException('No tvshows found')
        row = rows[0]
        quoteText = IMDB.getRandomQuote(row['title'], season = row['season'], episode = row['episode'], maxLength = 128)
        if quoteText is None:
            raise QuestionException('Did not find any quotes')

        self.addCorrectAnswer(row['idShow'], row['title'], row['idFile'], path = thumb.getCachedTVShowThumb(row['tvShowPath']))

        # Fill with random episodes from other shows
        shows = database.getTVShows(maxResults = 3, excludeTVShowId = row['idShow'], onlySelectTVShow = True)
        for show in shows:
            self.addAnswer(show['idShow'], show['title'], path = thumb.getCachedTVShowThumb(show['tvShowPath']))

        random.shuffle(self.answers)
        quoteDisplayType.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS_QUOTE_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthisquotefrom.enabled') == 'true' and IMDB.isDataPresent()

class WhatTVShowIsThisThemeFromQuestion(TVQuestion):
    def __init__(self, database):
        audioDisplayType = AudioDisplayType()
        super(WhatTVShowIsThisThemeFromQuestion, self).__init__(audioDisplayType)

        tvShow = None
        themeSong = None
        rows = database.getTVShows(maxResults = 10)
        for row in rows:
            themeSong = os.path.join(row['tvShowPath'], 'theme.mp3')
            if xbmcvfs.exists(themeSong):
                tvShow = row
                break

        if tvShow is None:
            raise QuestionException('Unable to find any tv shows with a theme.mp3 file')

        self.addCorrectAnswer(tvShow['idShow'], tvShow['title'], tvShow['idFile'], path = thumb.getCachedTVShowThumb(tvShow['tvShowPath']))

        # Fill with random episodes from other shows
        shows = database.getTVShows(maxResults = 3, excludeTVShowId = tvShow['idShow'], onlySelectTVShow = True)
        for show in shows:
            self.addAnswer(show['idShow'], show['title'], path = thumb.getCachedTVShowThumb(show['tvShowPath']))

        random.shuffle(self.answers)
        audioDisplayType.setAudioFile(themeSong)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS_THEME_FROM)

    @staticmethod
    def isEnabled():
        return ADDON.getSetting('question.whattvshowisthisthemefrom.enabled') == 'true'

class QuestionException(Exception):
    pass


def getEnabledQuestionCandidates(gameInstance):
    """
        Gets random question from one of the Question subclasses.
    """
    questionCandidates = []
    if gameInstance.getType() == game.GAMETYPE_MOVIE:
        questionCandidates = MovieQuestion.__subclasses__()
    elif gameInstance.getType() == game.GAMETYPE_TVSHOW:
        questionCandidates = TVQuestion.__subclasses__()

    questionCandidates = [ candidate for candidate in questionCandidates if candidate.isEnabled() ]

    return questionCandidates





def isAnyMovieQuestionsEnabled():
    subclasses = MovieQuestion.__subclasses__()
    subclasses  = [ subclass for subclass in subclasses if subclass.isEnabled() ]
    return subclasses

def isAnyTVShowQuestionsEnabled():
    subclasses = TVQuestion.__subclasses__()
    subclasses  = [ subclass for subclass in subclasses if subclass.isEnabled() ]
    return subclasses
