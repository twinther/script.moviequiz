from elementtree import ElementTree
from pysqlite2 import dbapi2 as sqlite3
import os
import xbmc
import mysql.connector

__author__ = 'twinther'

class Database(object):
    """Base class for the various databases"""
    def __init__(self):
        self.conn = None

    def __del__(self):
        self.close()

    def close(self):
        self.conn.close()
        xbmc.log("Database closed")

    def fetchall(self, sql, parameters = tuple()):
        if not isinstance(parameters, tuple):
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

#
# MySQL
#

class MySQLDatabase(Database):
    def __init__(self, settings):
        Database.__init__(self)

        self.conn = mysql.connector.connect(
            host = settings['host'],
            user = settings['user'],
            passwd = settings['pass'],
            db = settings['name']
            )

        xbmc.log("MySQLDatabase opened")

    def hasMovies(self):
        row = self.fetchone("SELECT COUNT(table_name) AS cnt FROM information_schema.tables WHERE table_name='movieview'")
        if int(row['cnt']) > 0:
            return Database.hasMovies(self)
        else:
            return False

    def hasTVShows(self):
        row = self.fetchone("SELECT COUNT(table_name) AS cnt FROM information_schema.tables WHERE table_name='tvshowview'")
        if int(row['cnt']) > 0:
            return Database.hasTVShows(self)
        else:
            return False

    def _createCursor(self):
        return self.conn.cursor(cursor_class = MySQLCursorDict)

    def _prepareParameters(self, parameters):
        return map(str, parameters)

    def _prepareSql(self, sql):
        sql = sql.replace('%', '%%')
        sql = sql.replace('?', '%s')
        sql = sql.replace('random()', 'rand()')
        return sql

class MySQLCursorDict(mysql.connector.cursor.MySQLCursor):
    def fetchone(self):
        row = self._fetch_row()
        if row:
            return dict(zip(self.column_names, self._row_to_python(row)))
        return None

    def fetchall(self):
        if self._have_result is False:
            raise DbException("No result set to fetch from.")
        res = []
        (rows, eof) = self.db().protocol.get_rows()
        self.rowcount = len(rows)
        for i in xrange(0,self.rowcount):
            res.append(dict(zip(self.column_names, self._row_to_python(rows[i]))))
        self._handle_eof(eof)
        return res

#
# SQLite
#

class SQLiteDatabase(Database):
    def __init__(self, settings):
        Database.__init__(self)

        db_file = os.path.join(settings['host'], settings['name'] + '.db')
        print "db_file = %s" % db_file
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = self._sqlite_dict_factory
        xbmc.log("SQLiteDatabase opened")

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


def connect():
    settings = _loadSettings()

    if settings['type'].lower() == 'mysql':
        return MySQLDatabase(settings)
    else:
        return SQLiteDatabase(settings)

        
def _loadSettings():
    settings = {
        'type' : 'sqlite3',
        'host' : xbmc.translatePath('special://database/'),
        'name' : 'MyVideos34'
    }

    advancedSettings = xbmc.translatePath('special://userdata/advancedsettings.xml')
    if os.path.exists(advancedSettings):
        f = open(advancedSettings)
        doc = ElementTree.fromstring(f.read())
        f.close()

        typeNode = doc.find('videodatabase/type')
        hostNode = doc.find('videodatabase/host')
        databaseNameNode = doc.find('videodatabase/name')
        usernameNode = doc.find('videodatabase/user')
        passwordNode = doc.find('videodatabase/pass')

        if typeNode is not None:
            settings['type'] = typeNode.text
        if hostNode is not None:
            settings['host'] = hostNode.text
        if databaseNameNode is not None:
            settings['name'] = databaseNameNode.text
        if usernameNode is not None:
            settings['user'] = usernameNode.text
        if passwordNode is not None:
            settings['pass'] = passwordNode.text

    return settings
    