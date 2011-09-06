from elementtree import ElementTree
from xml.parsers.expat import ExpatError

import os
import xbmc
import glob

try:
    # Used by Eden/external python
    from sqlite3 import dbapi2 as sqlite3
except ImportError:
    # Used by Dharma/internal python
    from pysqlite2 import dbapi2 as sqlite3

__author__ = 'twinther'

class Database(object):
    """Base class for the various databases"""
    def __init__(self, allowedRatings, onlyWatched):
        self.conn = None

        self.defaultMovieViewClause = ''
        self.defaultTVShowViewClause = ''
        if allowedRatings:
            self.defaultMovieViewClause += " AND TRIM(c12) IN ('%s')" % '\',\''.join(allowedRatings)
            self.defaultTVShowViewClause += " AND TRIM(tv.c13) IN ('%s')" % '\',\''.join(allowedRatings)
        if onlyWatched:
            self.defaultMovieViewClause += " AND mv.playCount IS NOT NULL"
            self.defaultTVShowViewClause += " AND ev.playCount IS NOT NULL"

    def __del__(self):
        self.close()

    def postInit(self):
        self._fixMissingTVShowView()

    def _fixMissingTVShowView(self):
        self.conn.execute("""
        CREATE VIEW IF NOT EXISTS tvshowview AS
            SELECT tvshow.*, path.strPath AS strPath, NULLIF(COUNT(episode.c12), 0) AS totalCount, COUNT(files.playCount) AS watchedcount, NULLIF(COUNT(DISTINCT(episode.c12)), 0) AS totalSeasons
            FROM tvshow
                LEFT JOIN tvshowlinkpath ON tvshowlinkpath.idShow=tvshow.idShow
                LEFT JOIN path ON path.idPath=tvshowlinkpath.idPath
                LEFT JOIN tvshowlinkepisode ON tvshowlinkepisode.idShow=tvshow.idShow
                LEFT JOIN episode ON episode.idEpisode=tvshowlinkepisode.idEpisode
                LEFT JOIN files ON files.idFile=episode.idFile
            GROUP BY tvshow.idShow;
        """)

    def close(self):
        self.conn.close()
        print "Database closed"

    def fetchall(self, sql, parameters = tuple()):
        if isinstance(parameters, list):
            parameters = tuple(parameters)
        elif not isinstance(parameters, tuple):
            parameters = [parameters]

        parameters = self._prepareParameters(parameters)
        sql = self._prepareSql(sql)

        xbmc.log("Executing fetchall SQL [%s]" % sql)

        c = self._createCursor()
        c.execute(sql, parameters)
        result = c.fetchall()

        if result is None:
            raise DbException(sql)

        return result

    def fetchone(self, sql, parameters = tuple()):
        if isinstance(parameters, list):
            parameters = tuple(parameters)
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        parameters = self._prepareParameters(parameters)
        sql = self._prepareSql(sql)

        xbmc.log("Executing fetchone SQL [%s]" % sql)

        c = self._createCursor()
        c.execute(sql, parameters)
        result = c.fetchone()

        if result is None:
            raise DbException(sql)

        return result

    def execute(self, sql, parameters = tuple()):
        if isinstance(parameters, list):
            parameters = tuple(parameters)
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        parameters = self._prepareParameters(parameters)
        sql = self._prepareSql(sql)

        c = self._createCursor()
        c.execute(sql, parameters)
        self.conn.commit()
        c.close()

    def _prepareParameters(self, parameters):
        return parameters

    def _prepareSql(self, sql):
        return sql

    def _createCursor(self):
        return self.conn.cursor()

    def hasMovies(self):
        row = self.fetchone("SELECT COUNT(*) AS cnt FROM movieview")
        return int(row['cnt']) > 0

    def hasTVShows(self):
        row = self.fetchone("SELECT COUNT(*) AS cnt FROM tvshowview")
        return int(row['cnt']) > 0



    def getRandomMovies(self, maxResults, setId = None, genres = None, excludeMovieIds = None, actorIdInMovie = None, actorIdNotInMovie = None,
                        directorId = None, excludeDirectorId = None, studioId = None, minYear = None, maxYear = None, mustHaveTagline = False,
                        minActorCount = None, mustHaveRuntime = False, maxRuntime = None):
        """
        Retrieves random movies from XBMC's video library.
        For each movie the following information is returned:
        * idMovie
        * idFile
        * title
        * genre
        * strPath
        * strFileName
        * idSet

        @param self: database instance
        @type self: Database
        @param maxResults: Retrieves this number of movies at most (actual number may be less than this)
        @type maxResults: int
        @param setId: Only retrieve movies included in this set
        @type setId: int
        @param genres: Only retrieve movies in this/these genres
        @type genres: str
        @param excludeMovieIds: Exclude the provided movie Ids from the list of movies candidiates
        @type excludeMovieIds: array of int
        """
        params = list()
        query = """
            SELECT mv.idMovie, mv.idFile, mv.c00 AS title, mv.c03 AS tagline, mv.c07 AS year, mv.c11 AS runtime, mv.c14 AS genre, mv.strPath, mv.strFileName, slm.idSet
            FROM movieview mv LEFT JOIN setlinkmovie slm ON mv.idMovie = slm.idMovie
            WHERE mv.strFileName NOT LIKE '%%.nfo'
            """ + self.defaultMovieViewClause

        if setId:
            query += " AND slm.idSet = ?"
            params.append(setId)

        if genres:
            query += " AND mv.c14 = ?"
            params.append(genres)

        if excludeMovieIds:
            if isinstance(excludeMovieIds, list):
                excludeMovieString = ','.join(map(str, excludeMovieIds))
            else:
                excludeMovieString = excludeMovieIds
            query += " AND mv.idMovie NOT IN (%s)" % excludeMovieString
            # different title
            query += " AND mv.c00 NOT IN (SELECT c00 FROM movieview WHERE idMovie IN (%s))" % excludeMovieString

        if actorIdNotInMovie:
            query += " AND mv.idMovie NOT IN (SELECT alm.idMovie FROM actorlinkmovie alm WHERE alm.idActor = ?)"
            params.append(actorIdInMovie)

        if actorIdInMovie:
            query += " AND mv.idMovie IN (SELECT alm.idMovie FROM actorlinkmovie alm WHERE alm.idActor = ?)"
            params.append(actorIdInMovie)

        if mustHaveTagline:
            query += " AND TRIM(mv.c03) != ''"

        if mustHaveRuntime:
            query += " AND TRIM(mv.c11) != ''"

        if maxRuntime:
            query += " AND CAST(mv.c11 AS INTEGER) < ?"
            params.append(maxRuntime)

        if minYear:
            query += " AND mv.c07 > ?"
            params.append(minYear)

        if maxYear:
            query += " AND mv.c07 < ?"
            params.append(maxYear)

        if directorId:
            query += " AND mv.idMovie IN (SELECT dlm.idMovie FROM directorlinkmovie dlm WHERE dlm.idDirector = ?)"
            params.append(directorId)

        if excludeDirectorId:
            query += " AND mv.idMovie NOT IN (SELECT dlm.idMovie FROM directorlinkmovie dlm WHERE dlm.idDirector = ?)"
            params.append(excludeDirectorId)

        if studioId:
            query += " AND mv.idMovie IN (SELECT slm.idMovie FROM studiolinkmovie slm WHERE slm.idStudio = ?)"
            params.append(studioId)

        if minActorCount:
            query += "AND (SELECT COUNT(DISTINCT alm.idActor) FROM actorlinkmovie alm WHERE alm.idMovie = mv.idMovie) >= ?"
            params.append(minActorCount)

        query += " ORDER BY random()"
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getRandomActors(self, maxResults = None, minMovieCount = None, excludeActorId = None, selectDistinct = None,
                        movieId = None, appendDefaultClause = True, mustHaveRole = False, excludeMovieIds = None):
        params = []
        if selectDistinct:
            query = "SELECT DISTINCT "
        else:
            query = "SELECT "

        query += """
            a.idActor, a.strActor, alm.strRole
            FROM movieview mv, actorlinkmovie alm, actors a
            WHERE mv.idMovie = alm.idMovie AND alm.idActor = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            """
        if appendDefaultClause:
            query += self.defaultMovieViewClause

        if minMovieCount:
            query += "GROUP BY alm.idActor HAVING count(mv.idMovie) >= ?"
            params.append(minMovieCount)

        if excludeActorId:
            query += " AND alm.idActor != ?"
            params.append(excludeActorId)

        if mustHaveRole:
            query += " AND alm.strRole != ''"

        if movieId:
            query += " AND mv.idMovie = ?"
            params.append(movieId)

        if excludeMovieIds:
            if isinstance(excludeMovieIds, list):
                excludeMovieString = ','.join(map(str, excludeMovieIds))
            else:
                excludeMovieString = excludeMovieIds
            query += " AND mv.idMovie NOT IN (%s)" % excludeMovieString
            # different title
            query += " AND mv.c00 NOT IN (SELECT c00 FROM movieview WHERE idMovie IN (%s))" % excludeMovieString

        query += " ORDER BY random()"
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getRandomDirectors(self, maxResults = None, minMovieCount = None, excludeDirectorId = None):
        params = []
        query = """
            SELECT a.idActor, a.strActor
            FROM movieview mv, directorlinkmovie dlm, actors a
            WHERE mv.idMovie = dlm.idMovie AND dlm.idDirector = a.idActor AND mv.strFileName NOT LIKE '%%.nfo'
            """ + self.defaultMovieViewClause

        if minMovieCount:
            query += "GROUP BY dlm.idDirector HAVING count(mv.idMovie) >= ?"
            params.append(minMovieCount)

        if excludeDirectorId:
            query += " AND dlm.idDirector != ?"
            params.append(excludeDirectorId)


        query += " ORDER BY random()"
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getRandomStudios(self, maxResults = None, excludeStudioId = None):
        params = []
        query = """
            SELECT s.idStudio, s.strStudio
            FROM movieview mv, studiolinkmovie slm, studio s
            WHERE mv.idMovie = slm.idMovie AND slm.idStudio = s.idStudio AND mv.strFileName NOT LIKE '%%.nfo'
            """ + self.defaultMovieViewClause

        if excludeStudioId:
            query += " AND slm.idStudio != ?"
            params.append(excludeStudioId)

        query += " ORDER BY random()"
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getRandomTVShows(self, maxResults = None, excludeTVShowId = None, excludeSpecials = False, episode = None, mustHaveFirstAired = False):
        params = []
        query = """
            SELECT ev.idFile, tv.c00 AS title, ev.c05 AS firstAired, ev.c12 AS season, ev.c13 AS episode, ev.idShow, ev.strPath, ev.strFileName, tv.strPath AS tvShowPath
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND ev.strFileName NOT LIKE '%%.nfo'
            """ + self.defaultTVShowViewClause

        if excludeTVShowId:
            query += " AND tv.idShow != ?"
            params.append(excludeTVShowId)

        if excludeSpecials:
            query += " AND ev.c12 != 0"

        if episode:
            query += " AND ev.c13 = ?"
            params.append(episode)

        if mustHaveFirstAired:
            query += " AND ev.c05 != ''"

        query += " ORDER BY random()"
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getRandomSeasons(self, maxResults = None, minSeasonCount = None, showId = None, excludeSeason = None, onlySelectSeason = False):
        params = []
        if onlySelectSeason:
            query = "SELECT DISTINCT ev.c12 AS season"
        else:
            query = """
                SELECT ev.idFile, ev.c12 AS season, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFileName, tv.strPath AS tvShowPath,
                (SELECT COUNT(DISTINCT c12) FROM episodeview WHERE idShow=ev.idShow) AS seasons
                """

        query += """
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND ev.strFileName NOT LIKE '%%.nfo'
            """

        if minSeasonCount:
            query += " AND seasons >= ?"
            params.append(minSeasonCount)

        if showId:
            query += " AND ev.idShow = ?"
            params.append(showId)

        if excludeSeason:
            query += " AND ev.c12 != ?"
            params.append(excludeSeason)

        query += " ORDER BY random()"
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)

    def getRandomEpisodes(self, maxResults = None, minEpisodeCount = None, idShow = None, season = None, excludeEpisode = None):
        params = []
        query = """
            SELECT ev.idFile, ev.c00 AS episodeTitle, ev.c12 AS season, ev.c13 AS episode, tv.c00 AS title, ev.idShow, ev.strPath, ev.strFileName,
                (SELECT COUNT(DISTINCT c13) FROM episodeview WHERE idShow=ev.idShow) AS episodes
            FROM episodeview ev, tvshowview tv
            WHERE ev.idShow=tv.idShow AND episodes > 2 AND ev.strFileName NOT LIKE '%%.nfo'
            """

        if minEpisodeCount:
            query += " AND episodes >= ?"
            params.append(minEpisodeCount)

        if idShow:
            query += " AND ev.idShow = ?"
            params.append(idShow)

        if season:
            query += " AND ev.c12 = ?"
            params.append(season)

        if excludeEpisode:
            query += " AND ev.c13 != ?"
            params.append(excludeEpisode)


        query += " ORDER BY random()"
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


    def getRandomTVShowActors(self, maxResults = None, excludeActorId = None, selectDistinct = None,
                        showId = None, appendDefaultClause = True, mustHaveRole = False, onlySelectActor = False):
        params = []
        if selectDistinct:
            query = "SELECT DISTINCT "
        else:
            query = "SELECT "

        if onlySelectActor:
            query += """
                alt.idActor, a.strActor, alt.strRole
                FROM actorlinktvshow alt, actors a
                WHERE alt.idActor=a.idActor
                """
        else:
            query += """
                alt.idActor, a.strActor, alt.strRole, tv.idShow, tv.c00 AS title, tv.strPath, tv.c08 AS genre
                FROM tvshowview tv, actorlinktvshow alt, actors a, episodeview ev
                WHERE tv.idShow = alt.idShow AND alt.idActor=a.idActor AND tv.idShow=ev.idShow AND ev.strFileName NOT LIKE '%%.nfo'
                """
        if appendDefaultClause:
            query += self.defaultTVShowViewClause

        if excludeActorId:
            query += " AND alt.idActor != ?"
            params.append(excludeActorId)

        if mustHaveRole:
            query += " AND alt.strRole != ''"

        if showId:
            query += " AND alt.idShow = ?"
            params.append(showId)

        query += " ORDER BY random()"
        if maxResults:
            query += " LIMIT " + str(maxResults)

        return self.fetchall(query, params)


#
# SQLite
#

class SQLiteDatabase(Database):
    def __init__(self, maxRating, onlyWatched, settings):
        super(SQLiteDatabase, self).__init__(maxRating, onlyWatched)
        found = True
        db_file = None

        # Find newest MyVideos.db and use that
        candidates = glob.glob(settings['host'] + '/MyVideos*.db')
        list.sort(candidates, reverse=True)
        if settings.has_key('name') and settings['name'] is not None:
            candidates.insert(0, settings['name'] + '.db') # defined in settings

        for candidate in candidates:
            db_file = os.path.join(settings['host'], candidate)
            if os.path.exists(db_file):
                found = True
                break

        if not found:
            xbmc.log("Unable to find any known SQLiteDatabase files!")
            return

        xbmc.log("Connecting to SQLite database file: %s" % db_file)
        self.conn = sqlite3.connect(db_file, check_same_thread = False)
        self.conn.row_factory = _sqlite_dict_factory
        xbmc.log("SQLiteDatabase opened")

        super(SQLiteDatabase, self).postInit()

    def hasMovies(self):
        row = self.fetchone("SELECT COUNT(*) AS cnt FROM sqlite_master WHERE name='movieview'")
        if int(row['cnt']) > 0:
            return Database.hasMovies(self)
        else:
            return False

    def hasTVShows(self):
        row = self.fetchone("SELECT COUNT(*) AS cnt FROM sqlite_master WHERE name='tvshowview'")
        if int(row['cnt']) > 0:
            return Database.hasTVShows(self)
        else:
            return False

def _sqlite_dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        dot = col[0].find('.') + 1
        if dot != -1:
            d[col[0][dot:]] = row[idx]
        else:
            d[col[0]] = row[idx]
    return d


class DbException(Exception):
    def __init__(self, sql):
        Exception.__init__(self, sql)


def connect(maxRating = None, onlyUsedWatched = None):
    settings = _loadSettings()
    xbmc.log("Loaded DB settings: %s" % settings)

    if settings.has_key('type') and settings['type'] is not None and settings['type'].lower() == 'mysql':
        raise DbException('MySQL database is not supported')
    else:
        return SQLiteDatabase(maxRating, onlyUsedWatched, settings)


def _loadSettings():
    settings = {
        'type' : 'sqlite3',
        'host' : xbmc.translatePath('special://database/')
    }

    advancedSettings = xbmc.translatePath('special://userdata/advancedsettings.xml')
    if os.path.exists(advancedSettings):
        f = open(advancedSettings)
        xml = f.read()
        f.close()
        try:
            doc = ElementTree.fromstring(xml)

            if doc.findtext('videodatabase/type') is not None:
                settings['type'] = doc.findtext('videodatabase/type')
            if doc.findtext('videodatabase/host') is not None:
                settings['host'] = doc.findtext('videodatabase/host')
            if doc.findtext('videodatabase/name') is not None:
                settings['name'] = doc.findtext('videodatabase/name')
            if doc.findtext('videodatabase/user') is not None:
                settings['user'] = doc.findtext('videodatabase/user')
            if doc.findtext('videodatabase/pass') is not None:
                settings['pass'] = doc.findtext('videodatabase/pass')
        except ExpatError:
           xbmc.log("Unable to parse advancedsettings.xml")

    return settings



