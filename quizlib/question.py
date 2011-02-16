import os
import random
import datetime
import thumb
import db

from strings import *


class Answer(object):
    def __init__(self, correct, id, text, idFile = None, videoPath = None, videoFilename = None, photoFile = None):
        self.correct = correct
        self.id = id
        self.text = text
        self.idFile = idFile
        if videoPath is not None and videoFilename is not None:
            self.setVideoFile(videoPath, videoFilename)
            self.coverFile = thumb.getCachedThumb(self.videoFile)
        else:
            self.videoFile = None
            self.coverFile = None

        if photoFile is not None:
            self.photoFile = photoFile
        else:
            self.photoFile = None

    def __str__(self):
        return "Answer(id=%s, text=%s, correct=%s)" % (self.id, self.text, self.correct)
        
    def setVideoFile(self, path, filename):
        if filename[0:8] == 'stack://':
            self.videoFile = filename
        else:
            self.videoFile = os.path.join(path, filename)


class Question(object):
    MPAA_RATINGS = ['R', 'Rated R', 'PG-13', 'Rated PG-13', 'PG', 'Rated PG', 'G', 'Rated G']

    def __init__(self, database, maxRating):
        self.database = database
        self.text = None
        self.answers = list()

        # Maximum allowed MPAA rating
        self.maxRating = maxRating

    def getText(self):
        return self.text

    def getAnswers(self):
        return self.answers

    def getAnswer(self, idx):
        return self.answers[idx]

    def getCorrectAnswer(self):
        for answer in self.answers:
            if answer.correct:
                return answer
        return None

    def getVideoFile(self):
        return self.getCorrectAnswer().videoFile

    def getPhotoFile(self):
        return self.getCorrectAnswer().photoFile

    def _get_movie_ids(self):
        movieIds = list()
        for movie in self.answers:
            movieIds.append(movie.id)
        return ','.join(map(str, movieIds))

    def _get_max_rating_clause(self):
        if self.maxRating is None:
            return ''

        idx = self.MPAA_RATINGS.index(self.maxRating)
        ratings = self.MPAA_RATINGS[idx:]

        return ' AND TRIM(c12) IN (\'%s\')' % '\',\''.join(ratings)


class WhatMovieIsThisQuestion(Question):
    """
        WhatMovieIsThisQuestion
    """

    def __init__(self, database, maxRating):
        Question.__init__(self, database, maxRating)

        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c14 AS genre, mv.strPath, mv.strFilename, slm.idSet
            FROM movieview mv, setlinkmovie slm
            WHERE mv.idMovie = slm.idMovie
            %s
            ORDER BY random() LIMIT 1
            """ % self._get_max_rating_clause())
        self.answers.append(Answer(True, row['idMovie'], row['title'], row['idFile'], row['strPath'], row['strFilename']))

        # Find other movies in set
        otherMoviesInSet = self.database.fetchall("""
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, setlinkmovie slm WHERE mv.idMovie = slm.idMovie AND slm.idSet = ? AND mv.idMovie != ?
            %s
            ORDER BY random() LIMIT 3
            """ % self._get_max_rating_clause(), (row['idSet'], row['idMovie']))
        for movie in otherMoviesInSet:
            self.answers.append(Answer(False, movie['idMovie'], movie['title'], movie['idFile'], movie['strPath'], movie['strFilename']))
        print self._get_movie_ids()

        # Find other movies in genre
        if len(self.answers) < 4:
            otherMoviesInGenre = self.database.fetchall("""
                SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c14 AS genre, mv.strPath, mv.strFilename
                FROM movieview mv WHERE genre = ? AND mv.idMovie NOT IN (%s)
                %s
                ORDER BY random() LIMIT ?
                """ % (self._get_movie_ids(), self._get_max_rating_clause()), (row['genre'], 4 - len(self.answers)))
            for movie in otherMoviesInGenre:
                self.answers.append(Answer(False, movie['idMovie'], movie['title'], movie['idFile'], movie['strPath'], movie['strFilename']))
            print self._get_movie_ids()

        # Fill with random movies
        if len(self.answers) < 4:
            theRest = self.database.fetchall("""
                SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFilename
                FROM movieview mv WHERE mv.idMovie NOT IN (%s)
                %s
                ORDER BY random() LIMIT ?
                """ % (self._get_movie_ids(), self._get_max_rating_clause()), 4 - len(self.answers))
            for movie in theRest:
                self.answers.append(Answer(False, movie['idMovie'], movie['title'], movie['idFile'], movie['strPath'], movie['strFilename']))
            print self._get_movie_ids()

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS)


class ActorNotInMovieQuestion(Question):
    """
        ActorNotInMovieQuestion
    """
    def __init__(self, database, maxRating):
        Question.__init__(self, database, maxRating)

        actor = None
        photoFile = None
        rows = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = a.idActor
            %s
            GROUP BY alm.idActor HAVING count(mv.idMovie) > 3 ORDER BY random() LIMIT 10
            """ % self._get_max_rating_clause())
        # try to find an actor with a cached photo (if non are found we simply use the last actor selected)
        for row in rows:
            photoFile = thumb.getCachedThumb('actor' + row['strActor'])
            if os.path.exists(photoFile):
                actor = row
                break
            else:
                photoFile = None

        # Movies actor is not in
        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv WHERE mv.idMovie NOT IN (
                SELECT DISTINCT alm.idMovie FROM actorlinkmovie alm WHERE alm.idActor = ?
            ) %s
            ORDER BY random() LIMIT 1
            """ % self._get_max_rating_clause(), actor['idActor'])
        self.answers.append(Answer(True, row['idMovie'], row['title'], photoFile = photoFile))

        # Movie actor is in
        movies = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, actorlinkmovie alm WHERE mv.idMovie = alm.idMovie AND alm.idActor = ?
            %s
            ORDER BY random() LIMIT 3
            """ % self._get_max_rating_clause(), actor['idActor'])
        for movie in movies:
            self.answers.append(Answer(False, movie['idMovie'], movie['title']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_ACTOR_NOT_IN, actor['strActor'])



class WhatYearWasMovieReleasedQuestion(Question):
    """
        WhatYearWasMovieReleasedQuestion
    """
    def __init__(self, database, maxRating):
        Question.__init__(self, database, maxRating)

        row = self.database.fetchone("""
            SELECT mv.idFile, mv.c00 AS title, mv.c07 AS year, mv.strPath, mv.strFilename
            FROM movieview mv WHERE year != 1900
            %s
            ORDER BY random() LIMIT 1
            """ % self._get_max_rating_clause())

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
            answer = Answer(year == int(row['year']), year, str(year), row['idFile'], row['strPath'], row['strFilename'])
            self.answers.append(answer)

        self.text = strings(Q_WHAT_YEAR_WAS_MOVIE_RELEASED, row['title'])


class WhatTagLineBelongsToMovieQuestion(Question):
    """
        WhatTagLineBelongsToMovieQuestion
    """
    def __init__(self, database, maxRating):
        Question.__init__(self, database, maxRating)

        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c03 AS tagline, mv.strPath, mv.strFilename
            FROM movieview mv WHERE TRIM(tagline) != \'\'
            %s
            ORDER BY random() LIMIT 1
            """ % self._get_max_rating_clause())
        self.answers.append(Answer(True, row['idMovie'], row['tagline'], row['idFile'], row['strPath'], row['strFilename']))

        otherAnswers = self.database.fetchall("""
            SELECT mv.idMovie, mv.idFile, mv.c03 AS tagline, mv.strPath, mv.strFilename
            FROM movieview mv WHERE TRIM(tagline) != \'\' AND mv.idMovie != ?
            %s
            ORDER BY random() LIMIT 3
            """ % self._get_max_rating_clause(), row['idMovie'])
        for movie in otherAnswers:
            self.answers.append(Answer(False, movie['idMovie'], movie['tagline'], row['idFile'], row['strPath'], row['strFilename']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TAGLINE_BELONGS_TO_MOVIE, row['title'])


class WhoDirectedThisMovieQuestion(Question):
    """
        WhoDirectedThisMovieQuestion
    """
    def __init__(self, database, maxRating):
        Question.__init__(self, database, maxRating)

        row = self.database.fetchone("""
            SELECT idActor, a.strActor, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor
            %s
            ORDER BY random() LIMIT 1
        """ % self._get_max_rating_clause())
        self.answers.append(Answer(True, row['idActor'], row['strActor'], row['idFile'], row['strPath'], row['strFilename']))

        otherAnswers = self.database.fetchall("""
            SELECT a.idActor, a.strActor, mv.strPath, mv.strFilename
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor AND a.idActor != ?
            %s
            ORDER BY random() LIMIT 3
        """ % self._get_max_rating_clause(), row['idActor'])
        for movie in otherAnswers:
            self.answers.append(Answer(False, movie['idActor'], movie['strActor'], row['idFile'], row['strPath'], row['strFilename']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_DIRECTED_THIS_MOVIE, row['title'])


class WhatStudioReleasedMovieQuestion(Question):
    """
        WhatStudioReleasedMovieQuestion
    """
    def __init__(self, database, maxRating):
        Question.__init__(self, database, maxRating)

        row = self.database.fetchone("""
            SELECT s.idStudio, s.strStudio, mv.idFile, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, studiolinkmovie slm, studio s
            WHERE mv.idMovie = slm.idMovie AND slm.idStudio = s.idStudio
            %s
            ORDER BY random() LIMIT 1
        """ % self._get_max_rating_clause())
        self.answers.append(Answer(True, row['idStudio'], row['strStudio'], row['idFile'], row['strPath'], row['strFilename']))

        otherAnswers = self.database.fetchall("""
            SELECT s.idStudio, s.strStudio, mv.strPath, mv.strFilename
            FROM movieview mv, studiolinkmovie slm, studio s
            WHERE mv.idMovie = slm.idMovie AND slm.idStudio = s.idStudio AND s.idStudio != ?
            %s
            ORDER BY random() LIMIT 3
        """ % self._get_max_rating_clause(), row['idStudio'])
        for movie in otherAnswers:
            self.answers.append(Answer(False, movie['idStudio'], movie['strStudio'], row['idFile'], row['strPath'], row['strFilename']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_STUDIO_RELEASED_MOVIE, row['title'])


class WhatActorIsThisQuestion(Question):
    """
        WhatActorIsThisQuestion
    """
    def __init__(self, database, maxRating):
        Question.__init__(self, database, maxRating)

        actor = None
        photoFile = None
        rows = self.database.fetchall("""
            SELECT a.idActor, a.strActor
            FROM actors a, actorlinkmovie alm WHERE a.idActor = alm.idActor
            ORDER BY random() LIMIT 10
            """)
        # try to find an actor with a cached photo (if non are found we simply use the last actor selected)
        for row in rows:
            photoFile = thumb.getCachedThumb('actor' + row['strActor'])
            if os.path.exists(photoFile):
                actor = row
                break
            else:
                photoFile = None

        # The actor
        self.answers.append(Answer(True, actor['idActor'], actor['strActor'], photoFile = photoFile))

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


class QuestionException(Exception):
    def __init__(self):
        pass

def getRandomQuestion(database, maxRating):
    """
        Gets random question from one of the Question subclasses.
    """
    subclasses = Question.__subclasses__()
    random.shuffle(subclasses)

    for subclass in subclasses:
        try:
            return subclass(database, maxRating)
        except db.DbException, ex:
            print "Exception in %s: %s" % (subclass, ex.message)






