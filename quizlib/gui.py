import os
import threading

import xbmc
import xbmcgui

from player import TenSecondPlayer
from db import Database
import question

__author__ = 'twinther'

class QuizGui(xbmcgui.WindowXML):
    question = None

    def __init__(self, xmlFilename, scriptPath):
        xbmcgui.WindowXML.__init__(self, xmlFilename, scriptPath)


    def onInit(self):
        print "onInit"
        try:
            xbmcgui.lock()
            self.database = Database()

            self.getControl(5000).setVisible(False)
            self.getControl(5001).setVisible(False)
            self.getControl(5002).setVisible(False)
            self.getControl(5003).setVisible(False)

            splash = SplashDialog('script-moviequiz-splash.xml', os.getcwd(), database = self.database)
        finally:
            xbmcgui.unlock()
            splash.doModal()
            del splash

        self.correctAnswer = None
        self.player = TenSecondPlayer()

        self.score = {'correct' : 0, 'wrong' : 0}
        self.thumbnails = [None, None, None, None]

        self._update_score()
        self._setup_question()


    def onAction(self, action):
        print "onAction " + str(action)

        print "onAction 2 " + str(action.getId())
        if action.getId() == 9 or action.getId() == 10:
            if self.player is not None and self.player.isPlaying():
                self.player.stop()
            self.close()

        print action.getId()


    def onClick(self, controlId):
        print "onClick " + str(controlId)

        if controlId >= 4000 or controlId <= 4003:
            answer = self.question.getAnswer(controlId - 4000)
            if answer.correct:
                self.score['correct'] += 1
                self.getControl(5002).setVisible(True)
            else:
                self.score['wrong'] += 1
                self.getControl(5003).setVisible(True)
            self._update_score()

            if self.player.isPlaying():
                self.player.stop()
            self._setup_question()

            threading.Timer(3.0, self._hide_icons).start()


    def onFocus(self, controlId):
        print "onFocus " + str(controlId)

        self._update_thumb()

    def _setup_question(self):
        self.question = question.WhichStudioReleasedMovieQuestion(self.database)
        #self.question = question.getRandomQuestion()(self.database)
        self.getControl(4300).setLabel(self.question.getText())

        for idx, answer in enumerate(self.question.getAnswers()):
            self.getControl(4000 + idx).setLabel(answer.text + " (" + str(answer.correct) + ")")

        self._update_thumb()

        correctAnswer = self.question.getCorrectAnswer()
        if correctAnswer.videoFile is not None:
            print "videoFile: %s" % correctAnswer.videoFile
            self.getControl(5000).setVisible(True)
            self.getControl(5001).setVisible(False)
            xbmc.sleep(1500) # give skin animation time to execute
            self.player.playWindowed("/home/tommy/Videos/daily-pixels-3805-vind-halo-reach-faa-det-foer-alle-andre.mp4")
            #self.player.playWindowed(correctAnswer.videoFile)

        elif correctAnswer.photoFile is not None:
            print "photoFile: %s" % correctAnswer.photoFile
            self.getControl(4400).setImage(correctAnswer.photoFile)

            self.getControl(5000).setVisible(False)
            self.getControl(5001).setVisible(True)


    def _update_score(self):
        self.getControl(4101).setLabel(str(self.score['correct']))
        self.getControl(4103).setLabel(str(self.score['wrong']))

    def _update_thumb(self):
        if self.question is None:
            return # not initialized yet

        controlId = self.getFocusId()
        if controlId >= 4000 or controlId <= 4003:
            answer = self.question.getAnswer(controlId - 4000)
            if answer.coverFile is not None:
                self.getControl(4200).setVisible(True)
                self.getControl(4200).setImage(answer.coverFile)
            else:
                self.getControl(4200).setVisible(False)
                    
    def _hide_icons(self):
        self.getControl(5002).setVisible(False)
        self.getControl(5003).setVisible(False)





class SplashDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, xmlFilename, scriptPath, database):
        xbmcgui.WindowXMLDialog.__init__(self, xmlFilename, scriptPath)
        self.database = database

    def onInit(self):
        print "SplashDialog.onInit"

        movies = self.database.fetchone('SELECT COUNT(*) AS count, (SUM(c11) / 60) AS total_hours FROM movie')
        actors = self.database.fetchone('SELECT COUNT(DISTINCT idActor) AS count FROM actorlinkmovie')
        directors = self.database.fetchone('SELECT COUNT(DISTINCT idDirector) AS count FROM directorlinkmovie')

        collectionTrivia = 'Collection Trivia\n%d movies\n%d actors\n%d directors\n%d hours of\n           entertainment' \
            % (movies['count'], actors['count'], directors['count'], movies['total_hours'])



        self.getControl(4000).setLabel(collectionTrivia)

    def onAction(self, action):
        print "SplashDialog.onAction " + str(action)
        self.close()

    def onClick(self, controlId):
        print "SplashDialog.onClick " + str(controlId)  

    def onFocus(self, controlId):
        print "SplashDialog.onFocus " + str(controlId)
