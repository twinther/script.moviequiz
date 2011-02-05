import os
import random
import datetime
import thumb

from strings import *

class Answer(object):
    def __init__(self, correct, id, text, videoPath = None, videoFilename = None, photoFile = None):
        self.correct = correct
        self.id = id
        self.text = text
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
    def __init__(self, database):
        self.database = database
        self.text = None
        self.answers = list()

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


class WhatMovieIsThisQuestion(Question):
    """
        WhatMovieIsThisQuestion
    """

    def __init__(self, database):
        Question.__init__(self, database)

        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.c00 AS title, mv.c14 AS genre, mv.strPath, mv.strFilename, slm.idSet
            FROM movieview mv, setlinkmovie slm
            WHERE mv.idMovie = slm.idMovie ORDER BY random() LIMIT 1
            """)
        self.answers.append(Answer(True, row['idMovie'], row['title'], row['strPath'], row['strFilename']))

        # Find other movies in set
        otherMoviesInSet = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, setlinkmovie slm WHERE mv.idMovie = slm.idMovie AND slm.idSet = ? AND mv.idMovie != ?
            ORDER BY random() LIMIT 3
            """, (row['idSet'], row['idMovie']))
        for movie in otherMoviesInSet:
            self.answers.append(Answer(False, movie['idMovie'], movie['title'], movie['strPath'], movie['strFilename']))
        print self._get_movie_ids()

        # Find other movies in genre
        if len(self.answers) < 4:
            otherMoviesInGenre = self.database.fetchall("""
                SELECT mv.idMovie, mv.c00 AS title, mv.c14 AS genre, mv.strPath, mv.strFilename
                FROM movieview mv WHERE genre = ? AND mv.idMovie NOT IN (%s)
                ORDER BY random() LIMIT ?
                """ % self._get_movie_ids(), (row['genre'], 4 - len(self.answers)))
            for movie in otherMoviesInGenre:
                self.answers.append(Answer(False, movie['idMovie'], movie['title'], movie['strPath'], movie['strFilename']))
            print self._get_movie_ids()

        # Fill with random movies
        if len(self.answers) < 4:
            theRest = self.database.fetchall("""
                SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
                FROM movieview mv WHERE mv.idMovie NOT IN (?)
                ORDER BY random() LIMIT ?
                """, (self._get_movie_ids(), 4 - len(self.answers)))
            for movie in theRest:
                self.answers.append(Answer(False, movie['idMovie'], movie['title'], movie['strPath'], movie['strFilename']))
            print self._get_movie_ids()

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_THIS)


class ActorNotInMovieQuestion(Question):
    """
        ActorNotInMovieQuestion
    """
    def __init__(self, database):
        Question.__init__(self, database)
        
        actor = self.database.fetchone("""
            SELECT a.idActor, a.strActor
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = a.idActor
            GROUP BY alm.idActor HAVING count(mv.idMovie) > 3 ORDER BY random() LIMIT 1
            """)

        # Movies actor is not in
        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, actorlinkmovie alm
            WHERE mv.idMovie = alm.idMovie AND alm.idActor != ? ORDER BY random() LIMIT 1
            """, actor['idActor'])
        self.answers.append(Answer(True, row['idMovie'], row['title'], photoFile = thumb.getCachedThumb('actor' + actor['strActor'])))

        # Movie actor is in
        movies = self.database.fetchall("""
            SELECT mv.idMovie, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, actorlinkmovie alm
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = ? ORDER BY random() LIMIT 3
            """, actor['idActor'])
        for movie in movies:
            self.answers.append(Answer(False, movie['idMovie'], movie['title']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_MOVIE_IS_ACTOR_NOT_IN, actor['strActor'])



class WhatYearWasMovieReleasedQuestion(Question):
    """
        WhatYearWasMovieReleasedQuestion
    """
    def __init__(self, database):
        Question.__init__(self, database)

        row = self.database.fetchone("""
            SELECT mv.c00 AS title, mv.c07 AS year, mv.strPath, mv.strFilename
            FROM movieview mv WHERE year != 1900
            ORDER BY random() LIMIT 1
            """)

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
            answer = Answer(year == int(row['year']), year, str(year), row['strPath'], row['strFilename'])
            self.answers.append(answer)

        self.text = strings(Q_WHAT_YEAR_WAS_MOVIE_RELEASED, row['title'])


class WhatTagLineBelongsToMovieQuestion(Question):
    """
        WhatTagLineBelongsToMovieQuestion
    """
    def __init__(self, database):
        Question.__init__(self, database)

        row = self.database.fetchone("""
            SELECT mv.idMovie, mv.c00 AS title, mv.c03 AS tagline, mv.strPath, mv.strFilename
            FROM movieview mv WHERE TRIM(tagline) != \'\' ORDER BY random() LIMIT 1
            """)
        self.answers.append(Answer(True, row['idMovie'], row['tagline'], row['strPath'], row['strFilename']))

        otherAnswers = self.database.fetchall("""
            SELECT mv.idMovie, mv.c03 AS tagline, mv.strPath, mv.strFilename
            FROM movieview mv WHERE TRIM(tagline) != \'\' AND mv.idMovie != ? ORDER BY random() LIMIT 3
            """, row['idMovie'])
        for movie in otherAnswers:
            self.answers.append(Answer(False, movie['idMovie'], movie['tagline'], row['strPath'], row['strFilename']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_TAGLINE_BELONGS_TO_MOVIE, row['title'])


class WhoDirectedThisMovieQuestion(Question):
    """
        WhoDirectedThisMovieQuestion
    """
    def __init__(self, database):
        Question.__init__(self, database)

        row = self.database.fetchone("""
            SELECT idActor, a.strActor, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor
            ORDER BY random() LIMIT 1
        """)
        self.answers.append(Answer(True, row['idActor'], row['strActor'], row['strPath'], row['strFilename']))

        otherAnswers = self.database.fetchall("""
            SELECT a.idActor, a.strActor, mv.strPath, mv.strFilename
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor AND a.idActor != ?
            ORDER BY random() LIMIT 3
        """, row['idActor'])
        for movie in otherAnswers:
            self.answers.append(Answer(False, movie['idActor'], movie['strActor'], movie['strPath'], movie['strFilename']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHO_DIRECTED_THIS_MOVIE, row['title'])


class WhatStudioReleasedMovieQuestion(Question):
    """
        WhatStudioReleasedMovieQuestion
    """
    def __init__(self, database):
        Question.__init__(self, database)

        row = self.database.fetchone("""
            SELECT s.idStudio, s.strStudio, mv.c00 AS title, mv.strPath, mv.strFilename
            FROM movieview mv, studiolinkmovie slm, studio s
            WHERE mv.idMovie = slm.idMovie AND slm.idStudio = s.idStudio
            ORDER BY random() LIMIT 1
        """)
        self.answers.append(Answer(True, row['idStudio'], row['strStudio'], row['strPath'], row['strFilename']))

        otherAnswers = self.database.fetchall("""
            SELECT s.idStudio, s.strStudio, mv.strPath, mv.strFilename
            FROM movieview mv, studiolinkmovie slm, studio s
            WHERE mv.idMovie = slm.idMovie AND slm.idStudio = s.idStudio AND s.idStudio != ?
            ORDER BY random() LIMIT 3
        """, row['idStudio'])
        for movie in otherAnswers:
            self.answers.append(Answer(False, movie['idStudio'], movie['strStudio'], movie['strPath'], movie['strFilename']))

        random.shuffle(self.answers)
        self.text = strings(Q_WHAT_STUDIO_RELEASED_MOVIE, row['title'])


def getRandomQuestion():
    """
        Gets random question from one of the Question subclasses.
    """
    subclasses = Question.__subclasses__()
    return subclasses[random.randint(0, len(subclasses) - 1)]



