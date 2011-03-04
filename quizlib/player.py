import random
import threading
import db

__author__ = 'tommy'

import xbmc

class TenSecondPlayer(xbmc.Player):
    def __init__(self, database = None):
        xbmc.Player.__init__(self)
        self.tenSecondTimer = None
        self.startTime = None

        self.database = database
        self.bookmark = None
        self.startingPlayback = False

    def stop(self):
        xbmc.log(">> TenSecondPlayer.stop()")
        # call xbmc.Player.stop() in a seperate thread to attempt to avoid xbmc lockups/crashes
        threading.Timer(0.5, self.delayedStop).start()
        if self.tenSecondTimer is not None:
            self.tenSecondTimer.cancel()
    
    def delayedStop(self):
        xbmc.log(">> TenSecondPlayer.delayedStop()")
        if not self.startingPlayback and self.isPlaying():
            xbmc.Player.stop(self)
        xbmc.log(">> TenSecondPlayer.delayedStop() - end")


    def playWindowed(self, file, idFile):
        xbmc.log(">> TenSecondPlayer.playWindowed()")
        self.startingPlayback = True
        if self.tenSecondTimer is not None:
            #self.stop()
            self.tenSecondTimer.cancel()

        # Get bookmark details, so we can restore after playback
        try:
            self.bookmark = self.database.fetchone("""
                SELECT idBookmark, timeInSeconds FROM bookmark WHERE idFile = ?
            """, idFile)
        except db.DbException:
            self.bookmark = {'idFile' : idFile}

        self.play(item = file, windowed = True)

        retries = 0
        while not self.isPlaying() and retries < 20:
            xbmc.sleep(250) # keep sleeping to get onPlayBackStarted() event
            retries += 1
        xbmc.log(">> TenSecondPlayer.playWindowed() - end")


    def onTenSecondsPassed(self):
        xbmc.log(">> TenSecondPlayer.onTenSecondsPassed()")
        if self.startingPlayback:
            return

        xbmc.sleep(250)
        if self.isPlaying():
            xbmc.Player.stop(self)

        retries = 0
        while self.isPlaying() and retries < 20 and not self.startingPlayback:
            xbmc.sleep(250) # keep sleeping to get onPlayBackStopped() event
            retries += 1


    def onPlayBackStarted(self):
        xbmc.log(">> TenSecondPlayer.onPlayBackStarted()")

        totalTime = self.getTotalTime()
        # find start time, ignore first 10% and last 20% of movie
        self.startTime = random.randint(int(totalTime * 0.1), int(totalTime * 0.8))

        xbmc.log(">> Playback from %d secs. to %d secs." % (self.startTime, self.startTime + 10))
        self.seekTime(self.startTime)

        self.tenSecondTimer = threading.Timer(10.0, self.onTenSecondsPassed)
        self.tenSecondTimer.start()

        self.startingPlayback = False
        xbmc.log(">> TenSecondPlayer.onPlayBackStarted() - end")

    def onPlayBackStopped(self):
        xbmc.log(">> TenSecondPlayer.onPlayBackStopped()")
        if self.tenSecondTimer is not None:
            self.tenSecondTimer.cancel()

        # Restore bookmark details
        if self.bookmark is not None:
            xbmc.sleep(1000) # Delay to allow XBMC to store the bookmark before we reset it
            if self.bookmark.has_key('idFile'):
                try:
                    self.database.execute("""
                        DELETE FROM bookmark WHERE idFile = ?
                    """, self.bookmark['idFile'])
                except db.DbException:
                    pass
            else:
                try:
                    self.database.execute("""
                        UPDATE bookmark SET timeInSeconds = ? WHERE idBookmark = ?
                    """, (self.bookmark['timeInSeconds'], self.bookmark['idBookmark']))
                except db.DbException:
                    pass

