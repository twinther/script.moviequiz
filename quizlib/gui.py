import os
import threading

import xbmc
import xbmcaddon
import xbmcgui

import question
import player
import db
from strings import *

__author__ = 'twinther'

C_MAIN_VIDEO_VISIBILITY = 5000
C_MAIN_PHOTO_VISIBILITY = 5001
C_MAIN_CORRECT_VISIBILITY = 5002
C_MAIN_INCORRECT_VISIBILITY = 5003

C_MAIN_CORRECT_SCORE = 4101
C_MAIN_INCORRECT_SCORE = 4103
C_MAIN_QUESTION_COUNT = 4104

C_MAIN_QUESTION_LABEL = 4300



class QuizGui(xbmcgui.WindowXML):
    def __init__(self, xmlFilename, scriptPath):
        xbmcgui.WindowXML.__init__(self, xmlFilename, scriptPath)

    def onInit(self):
        print "onInit"
        self.addon = xbmcaddon.Addon(id = 'script.moviequiz')
        self.database = db.Database()
        self.player = player.TenSecondPlayer(database = self.database)

        self.hide(C_MAIN_VIDEO_VISIBILITY)
        self.hide(C_MAIN_PHOTO_VISIBILITY)
        self.hide(C_MAIN_CORRECT_VISIBILITY)
        self.hide(C_MAIN_INCORRECT_VISIBILITY)

        splash = SplashDialog('script-moviequiz-splash.xml', os.getcwd(), database = self.database)
        splash.doModal()
        del splash

        self._setup_game()


    def onAction(self, action):
        if action.getId() == 9 or action.getId() == 10:
            if hasattr(self, 'player') and self.player.isPlaying():
                self.player.stop()
            self.close()


    def onClick(self, controlId):
        if hasattr(self, 'question') and (controlId >= 4000 or controlId <= 4003):
            answer = self.question.getAnswer(controlId - 4000)
            if answer.correct:
                self.score['correct'] += 1
                self.show(C_MAIN_CORRECT_VISIBILITY)
            else:
                self.score['wrong'] += 1
                self.show(C_MAIN_INCORRECT_VISIBILITY)

            if self.player.isPlaying():
                self.player.stop()

            threading.Timer(3.0, self._hide_icons).start()
            if self.addon.getSetting('show.correct.answer') == 'true' and not answer.correct:
                for idx, answer in enumerate(self.question.getAnswers()):
                    if answer.correct:
                        self.getControl(4000 + idx).setLabel('[B]%s[/B]' % answer.text)
                    else:
                        self.getControl(4000 + idx).setLabel(textColor = '0x88888888')

                xbmc.sleep(3000)

            self._setup_question()



    def onFocus(self, controlId):
        self._update_thumb()

    def _setup_game(self):
        maxQuestions = -1
        if self.addon.getSetting('question.limit.enabled') == 'true':
            maxQuestions = int(self.addon.getSetting('question.limit'))

        self.questionLimit = {'count' : 0, 'max' : maxQuestions}
        self.score = {'correct' : 0, 'wrong' : 0}

        self._setup_question()

    def _game_over(self):
        line1 = 'Game over'
        line2 = 'You scored %d of %d' % (self.score['correct'], self.questionLimit['max'])

        w = ClapperDialog('script-moviequiz-clapper.xml', os.getcwd(), line1 = line1, line2 = line2)
        w.doModal()
        del w
        
        self.close()

    def _setup_question(self):
        self.questionLimit['count'] += 1
        if self.questionLimit['max'] > 0 and self.questionLimit['count'] > self.questionLimit['max']:
            self._game_over()
            return

        maxRating = None
        if self.addon.getSetting('rating.limit.enabled') == 'true':
            maxRating = self.addon.getSetting('rating.limit')

        try:
            self.question = question.getRandomQuestion(self.database, maxRating)
        except question.QuestionException:
            pass

        self.getControl(C_MAIN_QUESTION_LABEL).setLabel(self.question.getText())

        for idx, answer in enumerate(self.question.getAnswers()):
            self.getControl(4000 + idx).setLabel(answer.text, textColor = '0xFFFFFFFF')

        self._update_thumb()
        self._update_stats()

        correctAnswer = self.question.getCorrectAnswer()
        if correctAnswer.videoFile is not None:
            self.show(C_MAIN_VIDEO_VISIBILITY)
            self.hide(C_MAIN_PHOTO_VISIBILITY)
            xbmc.sleep(1500) # give skin animation time to execute
            self.player.playWindowed("/home/tommy/Videos/daily-pixels-3805-vind-halo-reach-faa-det-foer-alle-andre.mp4", correctAnswer.idFile)
            #self.player.playWindowed(correctAnswer.videoFile, correctAnswer.idFile)

        elif correctAnswer.photoFile is not None:
            self.getControl(4400).setImage(correctAnswer.photoFile)

            self.hide(C_MAIN_VIDEO_VISIBILITY)
            self.show(C_MAIN_PHOTO_VISIBILITY)


    def _update_stats(self):
        self.getControl(C_MAIN_CORRECT_SCORE).setLabel(str(self.score['correct']))
        self.getControl(C_MAIN_INCORRECT_SCORE).setLabel(str(self.score['wrong']))

        if self.addon.getSetting('question.limit.enabled') == 'true':
            questionCount = strings(G_QUESTION_X_OF_Y, (self.questionLimit['count'], self.questionLimit['max']))
            self.getControl(C_MAIN_QUESTION_COUNT).setLabel(questionCount)
        else:
            self.getControl(C_MAIN_QUESTION_COUNT).setLabel('')


    def _update_thumb(self):
        if not hasattr(self, 'question'):
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

    def show(self, controlId):
        self.getControl(controlId).setVisible(True)

    def hide(self, controlId):
        self.getControl(controlId).setVisible(False)



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


class ClapperDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, xmlFilename, scriptPath, line1 = None, line2 = None, line3 = None):
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3

        xbmcgui.WindowXMLDialog.__init__(self, xmlFilename, scriptPath)


    def onInit(self):
        print "ClapperDialog.onInit"

        self.getControl(4000).setLabel(self.line1)
        self.getControl(4001).setLabel(self.line2)
        self.getControl(4002).setLabel(self.line3)

    def onAction(self, action):
        print "SplashDialog.onAction " + str(action)
        self.close()

    def onClick(self, controlId):
        print "SplashDialog.onClick " + str(controlId)

    def onFocus(self, controlId):
        print "SplashDialog.onFocus " + str(controlId)

