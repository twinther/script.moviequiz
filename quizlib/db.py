from pysqlite2 import dbapi2 as sqlite3
import xbmc

__author__ = 'twinther'

class Database(object):
    def __init__(self):
        self.db_file = xbmc.translatePath('special://profile/Database/MyVideos34.db')
        self.conn = sqlite3.connect(self.db_file, isolation_level = None)
        self.conn.row_factory = self._sqlite_dict_factory
        xbmc.log("Database opened")

    def __del__(self):
        self.conn.close()
        xbmc.log("Database closed")

    def fetchall(self, sql, parameters = tuple()):
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        c = self.conn.cursor()
        c.execute(sql, parameters)
        result = c.fetchall()

        if result is None:
            raise DbException(sql)

        return result

    def fetchone(self, sql, parameters = tuple()):
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        c = self.conn.cursor()
        c.execute(sql, parameters)
        result = c.fetchone()

        if result is None:
            raise DbException(sql)

        return result

    def execute(self, sql, parameters = tuple()):
        if not isinstance(parameters, tuple):
            parameters = [parameters]

        c = self.conn.cursor()
        print "before execute"
        c.execute(sql, parameters)
        print "before commit"
        self.conn.commit()
        print "commit"


    def _sqlite_dict_factory(self, cursor, row):
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
