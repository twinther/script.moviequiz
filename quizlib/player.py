import random
import threading

__author__ = 'tommy'

import xbmc

class TenSecondPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.tenSecondTimer = None

    def stop(self):
        print "cancel"
        self.tenSecondTimer.cancel()
        if self.isPlaying():
            xbmc.Player.stop(self)


    def playWindowed(self, file):
        print "!!!!!!!!!!!!! PlayWindowed"
        if self.tenSecondTimer is not None:
            self.stop()

        self.play(item = file, windowed = True)

        retries = 0
        while not self.isPlaying() and retries < 8:
            xbmc.sleep(250)
            retries += 1
            print "retries %d" % retries

        if self.isPlaying():
            totalTime = self.getTotalTime()
            # find start time, ignore first and last 10% of movie
            startTime = random.randint(int(totalTime * 0.1), int(totalTime * 0.9))
            endTime = startTime + 10

            print "Playback from: %d to %d" % (startTime, endTime)
            self.seekTime(startTime)

            self.tenSecondTimer = threading.Timer(10.0, self.stopPlayback)
            self.tenSecondTimer.start()

        print "playWindowed end"

    def stopPlayback(self):
        if self.isPlaying():
            self.stop()

        retries = 0
        while self.isPlaying() and retires < 8:
            xbmc.sleep(250)
            retries += 1
            print "retries %d" % retries

        print "stopPlayback end"



    def onPlayBackStarted(self):
        print "!!!!!!!!!!!!PlayBack Started"

    def onPlayBackEnded(self):
        print "!!!!!!!!!!!!PlayBack Ended"

    def onPlayBackStopped(self):
        print "!!!!!!!!!!!!PlayBack Stopped"

    def onPlayBackPaused(self):
        print "!!!!!!!!!!!!PlayBack Paused"

    def onPlayBackResumed(self):
        print "!!!!!!!!!!!!PlayBack Resumed"

