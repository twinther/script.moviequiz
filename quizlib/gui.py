import threading

import xbmc
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

class MenuGui(xbmcgui.WindowXML):
    def __init__(self, xmlFilename, scriptPath, addon):
        xbmcgui.WindowXML.__init__(self, xmlFilename, scriptPath)
        self.addon = addon

    def onInit(self):
        print "MenuGui.onInit"

        trivia = [strings(M_TRANSLATED_BY)]

        database = db.Database()

        row = database.fetchone("SELECT COUNT(*) AS cnt FROM sqlite_master WHERE name='movieview'")
        if not int(row['cnt']):
            self.getControl(4000).setEnabled(False)
        else:
            movies = database.fetchone('SELECT COUNT(*) AS count, (SUM(c11) / 60) AS total_hours FROM movie')
            actors = database.fetchone('SELECT COUNT(DISTINCT idActor) AS count FROM actorlinkmovie')
            directors = database.fetchone('SELECT COUNT(DISTINCT idDirector) AS count FROM directorlinkmovie')
            studios = database.fetchone('SELECT COUNT(idStudio) AS count FROM studio')

            trivia += [
                    strings(M_MOVIE_COLLECTION_TRIVIA),
                    strings(M_MOVIE_COUNT) % movies['count'],
                    strings(M_ACTOR_COUNT) % actors['count'],
                    strings(M_DIRECTOR_COUNT) % directors['count'],
                    strings(M_STUDIO_COUNT) % studios['count'],
                    strings(M_HOURS_OF_ENTERTAINMENT) % movies['total_hours']
            ]


        row = database.fetchone("SELECT COUNT(*) AS cnt FROM sqlite_master WHERE name='tvshowview'")
        if not int(row['cnt']):
            self.getControl(4001).setEnabled(False)
        else:
            shows = database.fetchone('SELECT COUNT(*) AS count FROM tvshow')
            seasons = database.fetchone('SELECT SUM(season_count) AS count FROM (SELECT idShow, COUNT(DISTINCT c12) AS season_count from episodeview GROUP BY idShow)')
            episodes = databas.fetchone('SELECT COUNT(*) AS count FROM episode')

            trivia += [
                strings(M_TVSHOW_COLLECTION_TRIVIA),
                strings(M_TVSHOW_COUNT) % shows['count'],
                strings(M_SEASON_COUNT) % seasons['count'],
                strings(M_EPISODE_COUNT) % episodes['count']
            ]

        del database



        label = '  *  '.join(trivia)
        self.getControl(6000).setLabel(label)

    def onAction(self, action):
        if action.getId() == 9 or action.getId() == 10:
            self.close()

    def onClick(self, controlId):
        if controlId == 4000:
            path = self.addon.getAddonInfo('path')
            w = QuizGui('script-moviequiz-main.xml', path, addon=self.addon, type=question.TYPE_MOVIE)
            w.doModal()
            del w

        elif controlId == 4001:
            path = self.addon.getAddonInfo('path')
            w = QuizGui('script-moviequiz-main.xml', path, addon=self.addon, type=question.TYPE_TV)
            w.doModal()
            del w

        elif controlId == 4002:
            self.addon.openSettings()

        elif controlId == 4003:
            self.close()

    #noinspection PyUnusedLocal
    def onFocus(self, controlId):
        pass


class QuizGui(xbmcgui.WindowXML):
    def __init__(self, xmlFilename, scriptPath, addon, type):
        xbmcgui.WindowXML.__init__(self, xmlFilename, scriptPath)
        self.addon = addon
        self.type = type

    def onInit(self):
        print "onInit"

        try :
            xbmcgui.lock()
            if self.type == question.TYPE_TV:
                self.getControl(4500).setVisible(False)
        finally:
            xbmcgui.unlock()

        self.database = db.Database()
        self.player = player.TenSecondPlayer(database=self.database)

        self._setup_game()


    def onAction(self, action):
        if action.getId() == 9 or action.getId() == 10:
            if hasattr(self, 'player') and self.player.isPlaying():
                self.player.stop()
            self._game_over()
            self.close()


    def onClick(self, controlId):
        if hasattr(self, 'question') and (controlId >= 4000 or controlId <= 4003):
            answer = self.question.getAnswer(controlId - 4000)
            if answer is not None and answer.correct:
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
                        self.setFocusId(4000 + idx)
                    else:
                        self.getControl(4000 + idx).setLabel(textColor='0x88888888')

                xbmc.sleep(3000)

            self._setup_question()


    #noinspection PyUnusedLocal
    def onFocus(self, controlId):
        self._update_thumb()

    def _setup_game(self):
        maxQuestions = -1
        if self.addon.getSetting('question.limit.enabled') == 'true':
            maxQuestions = int(self.addon.getSetting('question.limit'))

        self.questionLimit = {'count': 0, 'max': maxQuestions}
        self.score = {'correct': 0, 'wrong': 0}

        self._setup_question()

    def _game_over(self):
        total = self.score['correct'] + self.score['wrong']

        line1 = strings(G_GAME_OVER)
        line2 = strings(G_YOU_SCORED) % (self.score['correct'], total)

        path = self.addon.getAddonInfo('path')
        w = ClapperDialog('script-moviequiz-clapper.xml', path, line1=line1, line2=line2)
        w.doModal()
        del w

        self.close()

    def _setup_question(self):
        self.questionLimit['count'] += 1
        if self.questionLimit['max'] > 0 and self.questionLimit['count'] > self.questionLimit['max']:
            self._game_over()
            return

        maxRating = None
        if self.type == question.TYPE_MOVIE and self.addon.getSetting('movie.rating.limit.enabled') == 'true':
            maxRating = self.addon.getSetting('movie.rating.limit')
        elif self.type == question.TYPE_TV and self.addon.getSetting('tvshow.rating.limit.enabled') == 'true':
            maxRating = self.addon.getSetting('tvshow.rating.limit')
        onlyWatchedMovies = self.addon.getSetting('only.watched.movies') == 'true'

        self.question = question.getRandomQuestion(self.type, self.database, maxRating, onlyWatchedMovies)

        self.getControl(C_MAIN_QUESTION_LABEL).setLabel(self.question.getText())

        answers = self.question.getAnswers()
        for idx in range(0, 4):
            if idx >= len(answers):
                self.getControl(4000 + idx).setLabel('')
                self.getControl(4000 + idx).setEnabled(False)
            else:
                self.getControl(4000 + idx).setLabel(answers[idx].text, textColor='0xFFFFFFFF')
                self.getControl(4000 + idx).setEnabled(True)

        self._update_thumb()
        self._update_stats()

        correctAnswer = self.question.getCorrectAnswer()
        print "videoFile = %s" % correctAnswer.videoFile
        print "photoFile = %s" % correctAnswer.photoFile
        if correctAnswer.videoFile is not None:
            self.show(C_MAIN_VIDEO_VISIBILITY)
            self.hide(C_MAIN_PHOTO_VISIBILITY)
            xbmc.sleep(1500) # give skin animation time to execute
            #self.player.playWindowed(correctAnswer.videoFile, correctAnswer.idFile)
            self.player.playWindowed('/home/tommy/panda_s01e02.mp4', -1)

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
            if answer is not None and answer.coverFile is not None:
                self.getControl(4200).setVisible(True)
                self.getControl(4200).setImage(answer.coverFile)
            else:
                self.getControl(4200).setVisible(False)

    def _hide_icons(self):
        self.hide(C_MAIN_CORRECT_VISIBILITY)
        self.hide(C_MAIN_INCORRECT_VISIBILITY)

    def show(self, controlId):
        self.getControl(controlId).setVisible(False) # Visibility is inverted in skin

    def hide(self, controlId):
        self.getControl(controlId).setVisible(True) # Visibility is inverted in skin


class ClapperDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, xmlFilename, scriptPath, line1=None, line2=None, line3=None):
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3

        xbmcgui.WindowXMLDialog.__init__(self, xmlFilename, scriptPath)


    def onInit(self):
        print "ClapperDialog.onInit"

        if self.line1 is None:
            self.line1 = ''
        if self.line2 is None:
            self.line2 = ''
        if self.line3 is None:
            self.line3 = ''

        self.getControl(4000).setLabel(self.line1)
        self.getControl(4001).setLabel(self.line2)
        self.getControl(4002).setLabel(self.line3)

        threading.Timer(5, self.delayedClose).start()

    def delayedClose(self):
        print "ClapperDialog.delayedClose"
        self.close()

    def onAction(self, action):
        print "ClapperDialog.onAction " + str(action)
        self.close()

    def onClick(self, controlId):
        print "ClapperDialog.onClick " + str(controlId)

    def onFocus(self, controlId):
        print "ClapperDialog.onFocus " + str(controlId)

