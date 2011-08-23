import simplejson
import urllib2
import md5
import os

import xbmc

import db

try:
    # Used by Eden/external python
    from sqlite3 import dbapi2 as sqlite3
except ImportError:
    # Used by Dharma/internal python
    from pysqlite2 import dbapi2 as sqlite3

class HighscoreDatabase(object):
    def addHighscore(self, nickname, game):
        raise

    def getHighscores(self, game):
        raise

    def getHighscoresNear(self, game, highscoreId):
        raise

class GlobalHighscoreDatabase(HighscoreDatabase):
    STATUS_OK = 'OK'
    SERVICE_URL = 'http://moviequiz.xbmc.info/service.json.php'

    def addHighscore(self, nickname, game):
        if game.getPoints() <= 0:
            return -1

        req = {
            'action' : 'submit',
            'entry' : {
                'type' : game.getType(),
                'gameType' : game.getGameType(),
                'gameSubType' : game.getGameSubType(),
                'nickname' : nickname,
                'score' : game.getPoints(),
                'correctAnswers' : game.getCorrectAnswers(),
                'numberOfQuestions' : game.getTotalAnswers()
            }
        }

        resp = self._request(req)

        if resp['status'] == self.STATUS_OK:
            return int(resp['newHighscoreId'])
        else:
            return -1


    def getHighscores(self, game):
        req = {
            'action' : 'highscores',
            'type' : game.getType(),
            'gameType' : game.getGameType(),
            'gameSubType' : game.getGameSubType()
        }

        resp = self._request(req)
        if resp['status'] == 'OK':
            return resp['highscores']
        else:
            return []

    def getHighscoresNear(self, game, highscoreId):
        return self.getHighscores(game)


    def _request(self, data):
        jsonData = simplejson.dumps(data)
        xbmc.log("GlobalHighscore request: " + jsonData)

        req = urllib2.Request(self.SERVICE_URL, jsonData)
        req.add_header('X-MovieQuiz-Checksum', md5.new(jsonData).hexdigest())
        req.add_header('Content-Type', 'text/json')

        try:
            u = urllib2.urlopen(req)
            resp = u.read()
            u.close()
            xbmc.log("GlobalHighscore response: " + resp)
            return simplejson.loads(resp)
        except urllib2.URLError:
            return {'status' : 'error'}


class LocalHighscoreDatabase(HighscoreDatabase):
    HIGHSCORE_DB = 'highscore.db'
    def __init__(self, path):
        highscoreDbPath = os.path.join(path, LocalHighscoreDatabase.HIGHSCORE_DB)

        self.conn = sqlite3.connect(highscoreDbPath, check_same_thread = False)
        self.conn.row_factory = db._sqlite_dict_factory
        xbmc.log("HighscoreDatabase opened: " + highscoreDbPath)

        self._createTables()

    def __del__(self):
        self.close()

    def close(self):
        self.conn.close()

        
    def addHighscore(self, nickname, game):
        if game.getPoints() <= 0:
            return -1

        c = self.conn.cursor()
        c.execute("INSERT INTO highscore(type, gameType, gameSubType, nickname, score, correctAnswers, numberOfQuestions, timestamp)"
            + " VALUES(?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            [game.getType(), game.getGameType(), game.getGameSubType(), nickname, game.getPoints(), game.getCorrectAnswers(), game.getTotalAnswers()])
        self.conn.commit()
        rowid = c.lastrowid

        # reposition highscore
        highscores = self.getHighscores(game)
        for idx, highscore in enumerate(highscores):
            c.execute("UPDATE highscore SET position=? WHERE id=?", [idx + 1, highscore['id']])
        self.conn.commit()
        c.close()

        return rowid

    def getHighscores(self, game):
        c = self.conn.cursor()
        c.execute('SELECT * FROM highscore WHERE type=? AND gameType=? and gameSubType=? ORDER BY score DESC, timestamp ASC',
            [game.getType(), game.getGameType(), game.getGameSubType()])
        return c.fetchall()

    def getHighscoresNear(self, game, highscoreId):
        c = self.conn.cursor()
        c.execute('SELECT position FROM highscore WHERE id=?', [highscoreId])
        r = c.fetchone()
        position = r['position']

        c.execute("SELECT * FROM highscore WHERE type=? AND gameType=? and gameSubType=? AND position > ? AND position < ? ORDER BY position",
            [game.getType(), game.getGameType(), game.getGameSubType(), position - 5, position + 5])
        return c.fetchall()


    def _createTables(self):
        xbmc.log('HighscoreDatabase._createTables()')
        c = self.conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS highscore ('
            + 'id INTEGER PRIMARY KEY,'
            + 'type TEXT,'
            + 'gameType TEXT,'
            + 'gameSubType TEXT,'
            + 'position INTEGER,'
            + 'nickname TEXT,'
            + 'score REAL,'
            + 'correctAnswers INTEGER,'
            + 'numberOfQuestions INTEGER,'
            + 'timestamp INTEGER )'
        )
        self.conn.commit()
        c.close()



