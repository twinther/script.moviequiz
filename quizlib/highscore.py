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
    def addHighscore(self, nickname, score, gameType, correctAnswers, numberOfQuestions):
        raise

    def getHighscores(self, gameType):
        raise

    def getHighscoresNear(self, gameType, highscoreId):
        raise

class GlobalHighscoreDatabase(HighscoreDatabase):
    SERVICE_URL = 'http://moviequiz.xbmc.info/service.json.php'

    def addHighscore(self, nickname, score, gameType, correctAnswers, numberOfQuestions):
        if score <= 0:
            return -1

        req = {
            'action' : 'submit',
            'entry' : {
                'type' : gameType.getIdentifier(),
                'nickname' : nickname,
                'score' : score,
                'correctAnswers' : correctAnswers,
                'numberOfQuestions' : numberOfQuestions
            }
        }

        resp = self._request(req)
        return int(resp['newHighscoreId'])


    def getHighscores(self, gameType):
        req = {
            'action' : 'highscores',
            'type' : gameType.getIdentifier()
        }

        resp = self._request(req)
        return resp['highscores']

    def getHighscoresNear(self, gameType, highscoreId):
        return self.getHighscores(gameType)


    def _request(self, data):
        jsonData = simplejson.dumps(data)

        req = urllib2.Request(self.SERVICE_URL, jsonData)
        req.add_header('X-MovieQuiz-Checksum', md5.new(jsonData).hexdigest())
        req.add_header('Content-Type', 'text/json')

        u = urllib2.urlopen(req)
        resp = u.read()
        u.close()

        return simplejson.loads(resp)



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

    def addHighscore(self, nickname, score, gameType, correctAnswers, numberOfQuestions):
        if score <= 0:
            return -1

        c = self.conn.cursor()
        c.execute("INSERT INTO highscore(type, nickname, score, correctAnswers, numberOfQuestions, timestamp) VALUES(?, ?, ?, ?, ?, datetime('now'))",
            [gameType.getIdentifier(), nickname, score, correctAnswers, numberOfQuestions])
        self.conn.commit()
        rowid = c.lastrowid

        # reposition highscore
        highscores = self.getHighscores(gameType)
        for idx, highscore in enumerate(highscores):
            c.execute("UPDATE highscore SET position=? WHERE id=?", [idx + 1, highscore['id']])
        self.conn.commit()
        c.close()

        return rowid

    def getHighscores(self, gameType):
        c = self.conn.cursor()
        c.execute('SELECT * FROM highscore WHERE type=? ORDER BY score DESC, timestamp ASC',
            [gameType.getIdentifier()])
        return c.fetchall()

    def getHighscoresNear(self, gameType, highscoreId):
        c = self.conn.cursor()
        c.execute('SELECT position FROM highscore WHERE id=?', [highscoreId])
        r = c.fetchone()
        position = r['position']

        c.execute("SELECT * FROM highscore WHERE type=? AND position > ? AND position < ? ORDER BY position",
            [gameType.getIdentifier(), position - 5, position + 5])
        return c.fetchall()


    def _createTables(self):
        xbmc.log('HighscoreDatabase._createTables()')
        c = self.conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS highscore ('
            + 'id INTEGER PRIMARY KEY,'
            + 'type TEXT,'
            + 'position INTEGER,'
            + 'nickname TEXT,'
            + 'score REAL,'
            + 'correctAnswers INTEGER,'
            + 'numberOfQuestions INTEGER,'
            + 'timestamp INTEGER )'
        )
        self.conn.commit()
        c.close()



if __name__ == '__main__':
    import gametype
    gt = gametype.UnlimitedGameType()

    hs = GlobalHighscoreDatabase()
    #hs.submitHighscore('Tommy', 123.4, gt, 10, 24)
    for entry in hs.getHighscores(gt):
        print entry



