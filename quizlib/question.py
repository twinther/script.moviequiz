import os
import random
import datetime
import thumb
import db
import time
import re
import quote

from strings import *

TYPE_MOVIE = 1
TYPE_TV = 2

DISPLAY_VIDEO = 1
DISPLAY_PHOTO = 2
DISPLAY_QUOTE = 3

class Answer(object):
    def __init__(self, correct, id, text, idFile = None):
        self.correct = correct
        self.id = id
        self.text = text
        self.idFile = idFile

        self.coverFile = None

    def __str__(self):
        return "Answer(id=%s, text=%s, correct=%s)" % (self.id, self.text, self.correct)
        
    def setCoverFile(self, path, filename = None):
        if filename is None:
            self.coverFile = path
        else:
            if filename[0:8] == 'stack://':
                videoFile = filename
            else:
                videoFile = os.path.join(path, filename)

            self.coverFile = thumb.getCachedThumb(videoFile)


class Question(object):
    def __init__(self, database, display, maxRating, onlyWatchedMovies):
        self.database = database
        self.answers = list()
        self.text = None
        self.videoFile = None
        self.photoFile = None
        self.quoteText = None

        self.display = display
        # Maximum allowed MPAA rating
        self.maxRating = maxRating
        self.onlyWatchedMovies = onlyWatchedMovies

    def getDisplay(self):
        return self.display

    def getText(self):
        return self.text

    def getAnswers(self):
        return self.answers

    def getAnswer(self, idx):
        if idx < len(self.answers):
            return self.answers[idx]
        else:
            return None

    def getCorrectAnswer(self):
        for answer in self.answers:
            if answer.correct:
                return answer
        return None

    def getUniqueIdentifier(self):
        return "%s-%s" % (self.__class__.__name__, str(self.getCorrectAnswer().id))

    def setVideoFile(self, path, filename):
        if filename[0:8] == 'stack://':
            self.videoFile = filename
        else:
            self.videoFile = os.path.join(path, filename)

    def getVideoFile(self):
        return self.videoFile

    def setPhotoFile(self, photoFile):
        self.photoFile = photoFile

    def getPhotoFile(self):
        return self.photoFile

    def setQuoteText(self, quoteText):
        self.quoteText = quoteText

    def getQuoteText(self):
        return self.quoteText

    def _get_movie_ids(self):
        movieIds = list()
        for movie in self.answers:
            movieIds.append(movie.id)
        return ','.join(map(str, movieIds))

#
# MOVIE QUESTIONS
#

class MovieQuestion(Question):
    MPAA_RATINGS = ['R', 'Rated R', 'PG-13', 'Rated PG-13', 'PG', 'Rated PG', 'G', 'Rated G']

    def __init__(self, database, display, maxRating, onlyWatchedMovies):
        Question.__init__(self, database, display, maxRating, onlyWatchedMovies)

    def _get_max_rating_clause(self):
        if self.maxRating is None:
            return ''

        idx = self.MPAA_RATINGS.index(self.maxRating)
        ratings = self.MPAA_RATINGS[idx:]

        return ' AND TRIM(c12) IN (\'%s\')' % '\',\''.join(ratings)

    def _get_watched_movies_clause(self):
        if self.onlyWatchedMovies:
            return ' AND mv.playCount IS NOT NULL'
        else:
            return ''



class WhatMovieIsThisQuestion(MovieQuestion):
    """
        WhatMovieIsThisQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c14 AS genre, mv.strPath, mv.strFilename, slm.idSet
            FROM movieview mv LEFT JOIN setlinkmovie slm ON mv.idMovie = slm.idMovie
            WHERE 1=1
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idMovie'], row['title'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFilename'])
        self.answers.append(a)

        # Find other movies in set
        if row['idSet'] is not None:
            otherMoviesInSet = self.database.fetchall("""
                SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFilename
                FROM movieview mv, setlinkmovie slm WHERE mv.idMovie = slm.idMovie AND slm.idSet = ? AND mv.idMovie != ?
                %s %s
                ORDER BY random() LIMIT 3
                """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), (row['idSet'], row['idMovie']))
            for movie in otherMoviesInSet:
                a = Answer(False, movie['idMovie'], movie['title'], movie['idFile'])
                a.setCoverFile(movie['strPath'], movie['strFilename'])
                self.answers.append(a)

        # Find other movies in genre
        if len(self.answers) < 4:
            try:
                otherMoviesInGenre = self.database.fetchall("""
                    SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c14 AS genre, mv.strPath, mv.strFilename
                    FROM movieview mv WHERE genre = ? AND mv.idMovie NOT IN (%s)
                    %s %s
                    ORDER BY random() LIMIT ?
                    """ % (self._get_movie_ids(), self._get_max_rating_clause(), self._get_watched_movies_clause()),
                        (row['genre'], 4 - len(self.answers)))
                for movie in otherMoviesInGenre:
                    a = Answer(False, movie['idMovie'], movie['title'], movie['idFile'])
                    a.setCoverFile(movie['strPath'], movie['strFilename'])
                    self.answers.append(a)
            except db.DbException:
                pass # ignore in case user has no other movies in genre

        # Fill with random movies
        if len(self.answers) < 4:
            theRest = self.database.fetchall("""
                SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFilename
                FROM movieview mv WHERE mv.idMovie NOT IN (%s)
                %s %s
                ORDER BY random() LIMIT ?
                """ % (self._get_movie_ids(), self._get_max_rating_clause(), self._get_watched_movies_clause()),
                         4 - len(self.answers))
            for movie in theRest:
                a = Answer(False, movie['idMovie'], movie['title'], movie['idFile'])
                a.setCoverFile(movie['strPath'], movie['strFilename'])
                self.answers.append(a)
            print self._get_movie_ids()

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS)
        self.setVideoFile(row['strPath'], row['strFilename'])


class ActorNotInMovieQuestion(MovieQuestion):
    """
        ActorNotInMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_PHOTO, maxRating, onlyWatchedMovies)

        actor = None
        photoFile = None
        rows = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = a.idActor
            %s %s
            GROUP BY alm.idActor HAVING count(mv.idMovie) > 3 ORDER BY random() LIMIT 10
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        # try to find an actor with a cached photo (if non are found we baily out)
        for row in rows:
            photoFile = thumb.getCachedActorThumb(row['strActor'])
            if os.path.exists(photoFile):
                actor = row
                break
            else:
                photoFile = None

        if actor is None:
            raise QuestionException("Didn't find any actors with photoFile")

        # Movies actor is not in
        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv WHERE mv.idMovie NOT IN (
                SELECT DISTINCT alm.idMovie FROM actorlinkmovie alm WHERE alm.idActor = ?
            ) %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), actor['idActor'])
        a = Answer(True, row['idMovie'], row['title'])
        a.setCoverFile(row['strPath'], row['strFilename'])
        self.answers.append(a)

        # Movie actor is in
        movies = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, actorlinkmovie alm WHERE mv.idMovie = alm.idMovie AND alm.idActor = ?
            %s %s
            ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), actor['idActor'])
        for movie in movies:
            a = Answer(False, movie['idMovie'], movie['title'])
            a.setCoverFile(movie['strPath'], movie['strFilename'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_ACTOR_NOT_IN, actor['strActor'])
        self.setPhotoFile(photoFile)



class WhatYearWasMovieReleasedQuestion(MovieQuestion):
    """
        WhatYearWasMovieReleasedQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT mv.idFile, mv.c00 AS title, mv.c07 AS year, mv.strPath, mv.strFilename
            FROM movieview mv WHERE year > 1900
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))

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
            a = Answer(year == int(row['year']), row['idFile'], str(year), row['idFile'])
            a.setCoverFile(row['strPath'], row['strFilename'])
            self.answers.append(a)

        self.text = strings(Q_WHAT_YEAR_WAS_MOVIE_RELEASED, row['title'])
        self.setVideoFile(row['strPath'], row['strFilename'])


class WhatTagLineBelongsToMovieQuestion(MovieQuestion):
    """
        WhatTagLineBelongsToMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c03 AS tagline, mv.strPath, mv.strFilename
            FROM movieview mv WHERE TRIM(tagline) != \'\'
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idMovie'], row['tagline'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFilename'])
        self.answers.append(a)

        otherAnswers = self.database.fetchall("""
            SELECT mv.idMovie, mv.idFile, mv.c03 AS tagline, mv.strPath, mv.strFilename
            FROM movieview mv WHERE TRIM(tagline) != \'\' AND mv.idMovie != ?
            %s %s
            ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()), row['idMovie'])
        for movie in otherAnswers:
            a = Answer(False, movie['idMovie'], movie['tagline'], row['idFile'])
            a.setCoverFile(row['strPath'], row['strFilename'])
            self.answers.append(a)

        if len(self.answers) < 3:
            raise QuestionException('Not enough taglines; got %d taglines' % len(self.answers))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TAGLINE_BELONGS_TO_MOVIE, row['title'])
        self.setVideoFile(row['strPath'], row['strFilename'])


class WhoDirectedThisMovieQuestion(MovieQuestion):
    """
        WhoDirectedThisMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT idActor, a.strActor, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor
            %s %s
            ORDER BY random() LIMIT 1
        """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idActor'], row['strActor'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFilename'])
        self.answers.append(a)

        otherAnswers = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM actors a
            WHERE a.idActor != ?
            ORDER BY random() LIMIT 3
        """, row['idActor'])
        for movie in otherAnswers:
            a = Answer(False, movie['idActor'], movie['strActor'], row['idFile'])
            a.setCoverFile(row['strPath'], row['strFilename'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_DIRECTED_THIS_MOVIE, row['title'])
        self.setVideoFile(row['strPath'], row['strFilename'])


class WhatStudioReleasedMovieQuestion(MovieQuestion):
    """
        WhatStudioReleasedMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT s.idStudio, s.strStudio, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, studiolinkmovie slm, studio s
            WHERE mv.idMovie = slm.idMovie AND slm.idStudio = s.idStudio
            %s %s
            ORDER BY random() LIMIT 1
        """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        a = Answer(True, row['idStudio'], row['strStudio'], row['idFile'])
        a.setCoverFile(row['strPath'], row['strFilename'])
        self.answers.append(a)

        otherAnswers = self.database.fetchall("""
            SELECT s.idStudio, s.strStudio
            FROM studio s
            WHERE s.idStudio != ?
            ORDER BY random() LIMIT 3
        """, row['idStudio'])
        for movie in otherAnswers:
            a = Answer(False, movie['idStudio'], movie['strStudio'], row['idFile'])
            a.setCoverFile(row['strPath'], row['strFilename'])
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_STUDIO_RELEASED_MOVIE, row['title'])
        self.setVideoFile(row['strPath'], row['strFilename'])


class WhatActorIsThisQuestion(MovieQuestion):
    """
        WhatActorIsThisQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_PHOTO, maxRating, onlyWatchedMovies)

        actor = None
        photoFile = None
        rows = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM actors a, actorlinkmovie alm WHERE a.idActor = alm.idActor
            ORDER BY random() LIMIT 10
            """)
        # try to find an actor with a cached photo (if non are found we simply use the last actor selected)
        for row in rows:
            photoFile = thumb.getCachedActorThumb(row['strActor'])
            if os.path.exists(photoFile):
                actor = row
                break
            else:
                photoFile = None

        if actor is None:
            raise QuestionException("Didn't find any actors with photoFile")

        # The actor
        a = Answer(True, actor['idActor'], actor['strActor'])
        self.answers.append(a)

        # Other actors
        actors = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM actors a, actorlinkmovie alm WHERE a.idActor = alm.idActor AND a.idActor != ?
            ORDER BY random() LIMIT 3
            """, actor['idActor'])
        for actor in actors:
            self.answers.append(Answer(False, actor['idActor'], actor['strActor']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_ACTOR_IS_THIS)
        self.setPhotoFile(photoFile)

class WhoPlayedRoleInMovieQuestion(MovieQuestion):
    """
        WhoPlayedRoleInMovieQuestion
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT alm.idActor, a.strActor, alm.strRole, mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie=alm.idMovie AND alm.idActor=a.idActor AND alm.strRole != ''
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))
        role = row['strRole']
        if re.search('[|/]', role):
            roles = re.split('[|/]', role)
            # find random role
            role = roles[random.randint(0, len(roles)-1)]

        a = Answer(True, row['idActor'], row['strActor'])
        a.setCoverFile(thumb.getCachedActorThumb(row['strActor']))
        self.answers.append(a)

        shows = self.database.fetchall("""
            SELECT alm.idActor, a.strActor, alm.strRole
            FROM actorlinkmovie alm, actors a
            WHERE alm.idActor=a.idActor AND alm.idMovie = ? AND alm.idActor != ?
            ORDER BY random() LIMIT 3
            """, (row['idMovie'], row['idActor']))
        for show in shows:
            a = Answer(False, show['idActor'], show['strActor'])
            a.setCoverFile(thumb.getCachedActorThumb(show['strActor']))
            self.answers.append(a)

        random.shuffle(self.answers)

        self.text = strings(Q_WHO_PLAYED_ROLE_IN_MOVIE) % (role, row['title'])
        self.setVideoFile(row['strPath'], row['strFilename'])

        
class WhatMovieIsThisQuoteFrom(MovieQuestion):
    """
        WhatQuoteIsThisFrom
    """
    def __init__(self, database, maxRating, onlyWatchedMovies):
        MovieQuestion.__init__(self, database, DISPLAY_QUOTE, maxRating, onlyWatchedMovies)

        rows = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.c07 AS year, mv.strPath, mv.strFilename
            FROM movieview mv
            WHERE year > 1900
            %s %s
            ORDER BY random() LIMIT 10
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()))

        addon = xbmcaddon.Addon(id = 'script.moviequiz') # TODO
        qd = quote.MovieQuotesDownloader(addon.getAddonInfo('profile'))
        quotes = None
        row = None
        for r in rows:
            quotes = qd.downloadQuotes(r['title'], r['year'])

            if quotes is not None:
                row = r
                break

        if quotes is None:
            raise QuestionException('Did not find any question')

        a = Answer(True, row['idMovie'], row['title'])
        a.setCoverFile(row['strPath'], row['strFilename'])
        self.answers.append(a)

        theRest = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv WHERE mv.idMovie != ?
            %s %s
            ORDER BY random() LIMIT 3
            """ % (self._get_max_rating_clause(), self._get_watched_movies_clause()),
                     row['idMovie'])
        for movie in theRest:
            a = Answer(False, movie['idMovie'], movie['title'])
            a.setCoverFile(movie['strPath'], movie['strFilename'])
            self.answers.append(a)

        quoteText = quotes[random.randint(0, len(quotes)-1)]

        random.shuffle(self.answers)
        self.setQuoteText(quoteText)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS_QUOTE_FROM)


#
# TV QUESTIONS
#

class TVQuestion(Question):
    CONTENT_RATINGS = ['TV-MA', 'TV-14', 'TV-PG', 'TV-G', 'TV-Y7-FV', 'TV-Y7', 'TV-Y']
    
    def __init__(self, database, display, maxRating, onlyWatchedMovies):
        Question.__init__(self, database, display, maxRating, onlyWatchedMovies)

    def _get_watched_episodes_clause(self):
        if self.onlyWatchedMovies:
            return ' AND ev.playCount IS NOT NULL'
        else:
            return ''

    def _get_max_rating_clause(self):
        if self.maxRating is None:
            return ''

        idx = self.CONTENT_RATINGS.index(self.maxRating)
        ratings = self.CONTENT_RATINGS[idx:]

        return ' AND TRIM(tv.c13) IN (\'%s\')' % '\',\''.join(ratings)

    def _get_season_title(self, season):
        if not int(season):
            return strings(Q_SPECIALS)
        else:
            return strings(Q_SEASON_NO) % int(season)

    def _get_episode_title(self, season, episode, title):
        return "%dx%02d - %s" % (int(season), int(episode), title)


class WhatTVShowIsThisQuestion(TVQuestion):
    """
        WhatTVShowIsThisQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFilename, tv.strPath AS showPath
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))
        a = Answer(True, row['idShow'], row['title'], row['idFile'])
        a.setCoverFile(thumb.getCachedTVShowThumb(row['showPath']))
        self.answers.append(a)

        # Fill with random episodes from other shows
        shows = self.database.fetchall("""
            SELECT tv.idShow, tv.c00 AS title, tv.strPath
            FROM tvshowview tv
            WHERE tv.idShow != ?
            ORDER BY random() LIMIT 3
            """, row['idShow'])
        for show in shows:
            a = Answer(False, show['idShow'], show['title'])
            a.setCoverFile(thumb.getCachedTVShowThumb(show['strPath']))
            self.answers.append(a)

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TVSHOW_IS_THIS)
        self.setVideoFile(row['strPath'], row['strFilename'])


class WhatSeasonIsThisQuestion(TVQuestion):
    """
        WhatSeasonIsThisQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, ev.c12 AS season, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFilename, tv.strPath AS showPath,
                (SELECT COUNT(DISTINCT c12) FROM episodeview WHERE idShow=ev.idShow) AS seasons
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND seasons > 2
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))
        a = Answer(True, "%s-%s" % (row['idShow'], row['season']), self._get_season_title(row['season']), row['idFile'])
        a.setCoverFile(thumb.getCachedSeasonThumb(row['strPath'], self._get_season_title(row['season'])))
        self.answers.append(a)

        # Fill with random seasons from this show
        shows = self.database.fetchall("""
            SELECT DISTINCT ev.c12 AS season
            FROM episodeview ev
            WHERE ev.idShow = ? AND season != ?
            ORDER BY random() LIMIT 3
            """, (row['idShow'], row['season']))
        for show in shows:
            a = Answer(False, "%s-%s" % (row['idShow'], show['season']), self._get_season_title(show['season']))
            a.setCoverFile(thumb.getCachedSeasonThumb(row['strPath'], self._get_season_title(show['season'])))
            self.answers.append(a)

        self.answers = sorted(self.answers, key=lambda answer: int(answer.id))

        self.text = strings(Q_WHAT_SEASON_IS_THIS) % row['title']
        self.setVideoFile(row['strPath'], row['strFilename'])

class WhatEpisodeIsThisQuestion(TVQuestion):
    """
        WhatEpisodeIsThisQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, ev.c00 AS episodeTitle, ev.c12 AS season, ev.c13 AS episode, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFilename,
                (SELECT COUNT(DISTINCT c13) FROM episodeview WHERE idShow=ev.idShow) AS episodes
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND episodes > 2
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))
        answerText = self._get_episode_title(row['season'], row['episode'], row['episodeTitle'])
        id = "%s-%s-%s" % (row['idShow'], row['season'], row['episode'])
        a = Answer(True, id, answerText, row['idFile'])
        a.setCoverFile(thumb.getCachedTVShowThumb(row['strPath']))
        self.answers.append(a)

        # Fill with random episodes from this show
        shows = self.database.fetchall("""
            SELECT ev.c00 AS episodeTitle, ev.c12 AS season, ev.c13 AS episode
            FROM episodeview ev
            WHERE ev.idShow = ? AND season = ? AND episode != ?
            ORDER BY random() LIMIT 3
            """, (row['idShow'], row['season'], row['episode']))
        for show in shows:
            answerText = self._get_episode_title(show['season'], show['episode'], show['episodeTitle'])
            id = "%s-%s-%s" % (row['idShow'], row['season'], show['episode'])
            a = Answer(False, id, answerText)
            a.setCoverFile(thumb.getCachedTVShowThumb(row['strPath']))
            self.answers.append(a)

        self.answers = sorted(self.answers, key=lambda answer: int(answer.id))

        self.text = strings(Q_WHAT_EPISODE_IS_THIS) % row['title']
        self.setVideoFile(row['strPath'], row['strFilename'])


class WhenWasEpisodeFirstAiredQuestion(TVQuestion):
    """
        WhenWasEpisodeFirstAiredQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, ev.c00 AS episodeTitle, ev.c12 AS season, ev.c13 AS episode, ev.c05 AS firstAired, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFilename,
                (SELECT COUNT(DISTINCT c13) FROM episodeview WHERE idShow=ev.idShow) AS episodes
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND episodes > 2 AND firstAired != ''
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))
        a = Answer(True, row['episode'], self._format_date(row['firstAired']), row['idFile'])
        a.setCoverFile(row['strPath'], row['strFilename'])
        self.answers.append(a)

        # Fill with random episodes from this show
        shows = self.database.fetchall("""
            SELECT ev.c00 AS episodeTitle, ev.c12 AS season, ev.c13 AS episode, ev.c05 AS firstAired
            FROM episodeview ev
            WHERE ev.idShow = ? AND season = ? AND episode != ? AND firstAired != ''
            ORDER BY random() LIMIT 3
            """, (row['idShow'], row['season'], row['episode']))
        for show in shows:
            a = Answer(False, show['episode'], self._format_date(show['firstAired']))
            a.setCoverFile(row['strPath'], row['strFilename'])
            self.answers.append(a)

        self.answers = sorted(self.answers, key=lambda answer: int(answer.id))

        self.text = strings(Q_WHEN_WAS_EPISODE_FIRST_AIRED) % (self._get_episode_title(row['season'], row['episode'], row['episodeTitle']), row['title'])
        self.setVideoFile(row['strPath'], row['strFilename'])

    def _format_date(self, dateString):
        d = time.strptime(dateString, '%Y-%m-%d')
        return time.strftime(strings(Q_FIRST_AIRED_DATEFORMAT), d)

class WhenWasTVShowFirstAiredQuestion(TVQuestion):
    """
        WhenWasEpisodeFirstAiredQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_VIDEO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT ev.idFile, ev.c12 AS season, ev.c13 AS episode, ev.c05 AS firstAired, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFilename
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND episode = 1 AND episode != 0 AND firstAired != ''
            %s %s
            ORDER BY random() LIMIT 1
            """ % (self._get_watched_episodes_clause(), self._get_max_rating_clause()))

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
            a = Answer(year == int(row['year']), row['idFile'], str(year), row['idFile'])
            a.setCoverFile(thumb.getCachedTVShowThumb(row['strPath']))
            self.answers.append(a)

        self.text = strings(Q_WHEN_WAS_TVSHOW_FIRST_AIRED) % (row['title'] + ' - ' + self._get_season_title(row['season']))
        self.setVideoFile(row['strPath'], row['strFilename'])

class WhoPlayedRoleInTVShowQuestion(TVQuestion):
    """
        WhoPlayedRoleInTVShowQuestion
    """

    def __init__(self, database, maxRating, onlyWatchedMovies):
        TVQuestion.__init__(self, database, DISPLAY_PHOTO, maxRating, onlyWatchedMovies)

        row = self.database.fetchone("""
            SELECT alt.idActor, a.strActor, alt.strRole, tv.idShow, tv.c00 AS title, tv.strPath
            FROM tvshowview tv, actorlinktvshow alt, actors a
            WHERE tv.idShow = alt.idShow AND alt.idActor=a.idActor AND alt.strRole != ''
            ORDER BY random() LIMIT 1
            """)
        role = row['strRole']
        if re.search('[|/]', role):
            roles = re.split('[|/]', role)
            # find random role
            role = roles[random.randint(0, len(roles)-1)]

        a = Answer(True, row['idActor'], row['strActor'])
        a.setCoverFile(thumb.getCachedActorThumb(row['strActor']))
        self.answers.append(a)

        shows = self.database.fetchall("""
            SELECT alt.idActor, a.strActor, alt.strRole
            FROM actorlinktvshow alt, actors a
            WHERE alt.idActor=a.idActor AND alt.idShow = ?  AND alt.idActor != ?
            ORDER BY random() LIMIT 3
            """, (row['idShow'], row['idActor']))
        for show in shows:
            a = Answer(False, show['idActor'], show['strActor'])
            a.setCoverFile(thumb.getCachedActorThumb(show['strActor']))
            self.answers.append(a)

        random.shuffle(self.answers)

        self.text = strings(Q_WHO_PLAYED_ROLE_IN_TVSHOW) % (role, row['title'])
        self.setPhotoFile(thumb.getCachedTVShowThumb(row['strPath']))

class QuestionException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

def getRandomQuestion(type, database, maxRating, onlyWatchedMovies):
    """
        Gets random question from one of the Question subclasses.
    """
    subclasses = []
    if type == TYPE_MOVIE:
        subclasses = MovieQuestion.__subclasses__()
    elif type == TYPE_TV:
        subclasses = TVQuestion.__subclasses__()
    random.shuffle(subclasses)

    for subclass in subclasses:
        try:
            return subclass(database, maxRating, onlyWatchedMovies)
        except QuestionException, ex:
            print "QuestionException in %s: %s" % (subclass, ex)
        except db.DbException, ex:
            print "DbException in %s: %s" % (subclass, ex)

