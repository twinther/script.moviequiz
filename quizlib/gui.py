import threading
import os
import re

import xbmc
import xbmcgui

import gametype
import question
import player
import db
from strings import *

# Constants from [xbmc]/xbmc/guilib/Key.h
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
REMOTE_1 = 59
REMOTE_2 = 60
REMOTE_3 = 61
REMOTE_4 = 62

ADDON = xbmcaddon.Addon()
AUDIO_CORRECT = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'audio', 'correct.wav')
AUDIO_WRONG = os.path.join(ADDON.getAddonInfo('path'), 'resources', 'audio', 'wrong.wav')

class MenuGui(xbmcgui.WindowXML):

    C_MENU_MOVIE_QUIZ = 4001
    C_MENU_TVSHOW_QUIZ = 4002
    C_MENU_SETTINGS = 4000
    C_MENU_EXIT = 4003
    C_MENU_COLLECTION_TRIVIA = 6000

    def __new__(cls):
        return super(MenuGui, cls).__new__(cls, 'script-moviequiz-menu.xml', ADDON.getAddonInfo('path'))

    def __init__(self):
        super(MenuGui, self).__init__()
    
    def onInit(self):
        print "MenuGui.onInit"

        list = self.getControl(4100)
        unlimitedGameType = xbmcgui.ListItem('Unlimited')
        list.addItem(unlimitedGameType)
        questionLimitedGameType = xbmcgui.ListItem('Question limited')
        list.addItem(questionLimitedGameType)
        timeLimitedGameType = xbmcgui.ListItem('Time limited')
        list.addItem(timeLimitedGameType)

        trivia = [strings(M_TRANSLATED_BY)]

        database = db.connect()

        if not database.hasMovies():
            self.getControl(self.C_MENU_MOVIE_QUIZ).setEnabled(False)
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
                    strings(M_HOURS_OF_ENTERTAINMENT) % int(movies['total_hours'])
            ]


        if not database.hasTVShows():
            self.getControl(self.C_MENU_TVSHOW_QUIZ).setEnabled(False)
        else:
            shows = database.fetchone('SELECT COUNT(*) AS count FROM tvshow')
            seasons = database.fetchone('SELECT SUM(season_count) AS count FROM (SELECT idShow, COUNT(DISTINCT c12) AS season_count from episodeview GROUP BY idShow) AS tbl')
            episodes = database.fetchone('SELECT COUNT(*) AS count FROM episode')

            trivia += [
                strings(M_TVSHOW_COLLECTION_TRIVIA),
                strings(M_TVSHOW_COUNT) % shows['count'],
                strings(M_SEASON_COUNT) % seasons['count'],
                strings(M_EPISODE_COUNT) % episodes['count']
            ]

        if not database.hasMovies() and not database.hasTVShows():
            line1 = 'Missing requirements!'
            line2 = 'To play the Movie Quiz you must[CR]have some movies or TV shows'
            line3 = 'in your Video library. See the[CR]XBMC wiki for information.'
            w = ClapperDialog(line1, line2, line3, autoClose = False)
            w.doModal()
            del w

            self.close()


        database.close()

        label = '  *  '.join(trivia)
        self.getControl(self.C_MENU_COLLECTION_TRIVIA).setLabel(label)

    def onAction(self, action):
        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlId):
        if ADDON.getSetting('question.limit.enabled') == 'true':
            maxQuestions = int(ADDON.getSetting('question.limit'))
            gameType = gametype.QuestionLimitedGameType(maxQuestions)
        else:
            gameType = gametype.UnlimitedGameType()

        maxRating = None

        if controlId == self.C_MENU_MOVIE_QUIZ:
            self.getControl(5000).setVisible(False)
            xbmc.sleep(250)
            self.setFocusId(4100)

        elif controlId == 4100:
            selectedPosition = self.getControl(4100).getSelectedPosition()
            print "selectedPosition = " + str(selectedPosition)
            if not selectedPosition:
                gameType = gametype.UnlimitedGameType()
            elif selectedPosition == 1:
                maxQuestions = int(ADDON.getSetting('question.limit'))
                gameType = gametype.QuestionLimitedGameType(maxQuestions)
            elif selectedPosition == 2:
                gameType = gametype.TimeLimitedGameType()

            if ADDON.getSetting('movie.rating.limit.enabled') == 'true':
                maxRating = ADDON.getSetting('movie.rating.limit')
            w = QuizGui(type=question.TYPE_MOVIE, gameType=gameType, maxRating=maxRating)
            w.doModal()
            del w

        elif controlId == self.C_MENU_TVSHOW_QUIZ:
            if ADDON.getSetting('tvshow.rating.limit.enabled') == 'true':
                maxRating = ADDON.getSetting('tvshow.rating.limit')
            w = QuizGui(type=question.TYPE_TV, gameType=gameType, maxRating=maxRating)
            w.doModal()
            del w

        elif controlId == self.C_MENU_SETTINGS:
            ADDON.openSettings()

        elif controlId == self.C_MENU_EXIT:
            self.close()

    #noinspection PyUnusedLocal
    def onFocus(self, controlId):
        pass


class QuizGui(xbmcgui.WindowXML):
    C_MAIN_FIRST_ANSWER = 4000
    C_MAIN_LAST_ANSWER = 4003
    C_MAIN_REPLAY = 4010
    C_MAIN_EXIT = 4011
    C_MAIN_CORRECT_SCORE = 4101
    C_MAIN_INCORRECT_SCORE = 4103
    C_MAIN_QUESTION_COUNT = 4104
    C_MAIN_COVER_IMAGE = 4200
    C_MAIN_QUESTION_LABEL = 4300
    C_MAIN_PHOTO = 4400
    C_MAIN_MOVIE_BACKGROUND = 4500
    C_MAIN_TVSHOW_BACKGROUND = 4501
    C_MAIN_QUOTE_LABEL = 4600
    C_MAIN_PHOTO_1 = 4701
    C_MAIN_PHOTO_2 = 4702
    C_MAIN_PHOTO_3 = 4703
    C_MAIN_VIDEO_VISIBILITY = 5000
    C_MAIN_PHOTO_VISIBILITY = 5001
    C_MAIN_QUOTE_VISIBILITY = 5004
    C_MAIN_THREE_PHOTOS_VISIBILITY = 5006
    C_MAIN_CORRECT_VISIBILITY = 5002
    C_MAIN_INCORRECT_VISIBILITY = 5003
    C_MAIN_LOADING_VISIBILITY = 5005
    C_MAIN_REPLAY_BUTTON_VISIBILITY = 5007

    def __new__(cls, type, gameType, maxRating = None, interactive = True):
        return super(QuizGui, cls).__new__(cls, 'script-moviequiz-main.xml', ADDON.getAddonInfo('path'))

    def __init__(self, type, gameType, maxRating = None, interactive = True):
        super(QuizGui, self).__init__()

        self.gameType = gameType
        print "Using game type: " + str(self.gameType)

        self.type = type
        self.questionCount = 0
        self.maxRating = maxRating
        self.interactive = interactive

        self.questionPointsThread = None
        self.questionPoints = 0

        path = ADDON.getAddonInfo('path')
        if self.type == question.TYPE_TV:
            self.defaultBackground = os.path.join(path, 'resources', 'skins', 'Default', 'media', 'quiz-background-tvshows.png')
        else:
            self.defaultBackground = os.path.join(path, 'resources', 'skins', 'Default', 'media', 'quiz-background.png')

        self.database = db.connect()
        self.player = player.TenSecondPlayer(database=self.database)
        self.question = question.Question(self.database, None, None)
        self.previousQuestions = []

        self.correctAnswerCount = 0
        self.wrongAnswerCount = 0

        self.maxRating = None
        if maxRating is not None:
            self.maxRating = maxRating
        elif self.type == question.TYPE_MOVIE and ADDON.getSetting('movie.rating.limit.enabled') == 'true':
            self.maxRating = ADDON.getSetting('movie.rating.limit')
        elif self.type == question.TYPE_TV and ADDON.getSetting('tvshow.rating.limit.enabled') == 'true':
            self.maxRating = ADDON.getSetting('tvshow.rating.limit')
        self.onlyWatchedMovies = ADDON.getSetting('only.watched.movies') == 'true'

    def onInit(self):
        try :
            xbmcgui.lock()
            if self.type == question.TYPE_TV:
                self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.defaultBackground)
        finally:
            xbmcgui.unlock()

        self._setup_question()

    def close(self):
        if self.player and self.player.isPlaying():
            self.player.stop()
        # TODO self.database.close()
        xbmcgui.WindowXML.close(self)
        
    def onAction(self, action):
        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            self._game_over()

        elif action.getId() == REMOTE_1:
            self.setFocusId(self.C_MAIN_FIRST_ANSWER)
            self._handle_answer(self.question.getAnswer(0))
        elif action.getId() == REMOTE_2:
            self.setFocusId(self.C_MAIN_FIRST_ANSWER + 1)
            self._handle_answer(self.question.getAnswer(1))
        elif action.getId() == REMOTE_3:
            self.setFocusId(self.C_MAIN_FIRST_ANSWER + 2)
            self._handle_answer(self.question.getAnswer(2))
        elif action.getId() == REMOTE_4:
            self.setFocusId(self.C_MAIN_FIRST_ANSWER + 3)
            self._handle_answer(self.question.getAnswer(3))


    def onClick(self, controlId):
        if not self.interactive:
            return # ignore

        if self.question and (controlId >= self.C_MAIN_FIRST_ANSWER and controlId <= self.C_MAIN_LAST_ANSWER):
            answer = self.question.getAnswer(controlId - self.C_MAIN_FIRST_ANSWER)
            self._handle_answer(answer)
        elif controlId == self.C_MAIN_EXIT:
            self._game_over()
        elif controlId == self.C_MAIN_REPLAY:
            self.player.replay()

    def onFocus(self, controlId):
        self._update_thumb(controlId)

    def _game_over(self):
        if self.questionPointsThread is not None:
           self.questionPointsThread.cancel()

        if self.interactive:
            total = self.gameType.correctAnswers + self.gameType.wrongAnswers
            w = GameOverDialog(self, self.gameType.correctAnswers, total, self.gameType.points)
            w.doModal()
            del w

        self.close()

    def _setup_question(self):
        self.getControl(self.C_MAIN_LOADING_VISIBILITY).setVisible(True)

        if self.gameType.isGameOver():
            self._game_over()
            return

        self.question = self._getNewQuestion()
        self.getControl(self.C_MAIN_QUESTION_LABEL).setLabel(self.question.getText())

        answers = self.question.getAnswers()
        for idx in range(0, 4):
            button = self.getControl(self.C_MAIN_FIRST_ANSWER + idx)
            if idx >= len(answers):
                button.setLabel('')
                button.setVisible(False)
            else:
                button.setLabel(answers[idx].text, textColor='0xFFFFFFFF')
                button.setVisible(True)

            if not self.interactive and answers[idx].correct:
                # highlight correct answer
                self.setFocusId(self.C_MAIN_FIRST_ANSWER + idx)

        self._update_thumb()
        self._update_stats()

        if self.question.getFanartFile() is not None and os.path.exists(self.question.getFanartFile()):
            self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.question.getFanartFile())
        else:
            self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.defaultBackground)

        correctAnswer = self.question.getCorrectAnswer()
        if isinstance(self.question, question.VideoDisplayType):
            self._changeVisibility(video = True)
            xbmc.sleep(1500) # give skin animation time to execute
            self.player.playWindowed(self.question.getVideoFile(), correctAnswer.idFile)

        elif isinstance(self.question, question.PhotoDisplayType):
            self.getControl(self.C_MAIN_PHOTO).setImage(self.question.getPhotoFile())
            self._changeVisibility(photo = True)

        elif isinstance(self.question, question.ThreePhotoDisplayType):
            self.getControl(self.C_MAIN_PHOTO_1).setImage(self.question.getPhotoFile(0))
            self.getControl(self.C_MAIN_PHOTO_2).setImage(self.question.getPhotoFile(1))
            self.getControl(self.C_MAIN_PHOTO_3).setImage(self.question.getPhotoFile(2))
            self._changeVisibility(threePhotos = True)

        elif isinstance(self.question, question.QuoteDisplayType):
            quoteText = self.question.getQuoteText()
            quoteText = self._obfuscateQuote(quoteText)
            self.getControl(self.C_MAIN_QUOTE_LABEL).setText(quoteText)
            self._changeVisibility(quote = True)

        else:
            self._changeVisibility()

        if not self.interactive:
            # answers correctly in ten seconds
            threading.Timer(10.0, self._answer_correctly).start()

        self.getControl(self.C_MAIN_LOADING_VISIBILITY).setVisible(False)

        self.questionPoints = None
        self._question_points()

    def _getNewQuestion(self):
        retries = 0
        q = None
        while retries < 100:
            retries += 1

            q = question.getRandomQuestion(self.type, self.database, self.maxRating, self.onlyWatchedMovies)
            if q is None:
                continue
                
            try:
                self.previousQuestions.index(q.getUniqueIdentifier())
            except Exception:
                self.previousQuestions.append(q.getUniqueIdentifier())
                break

        return q

    def _question_points(self):
        if self.questionPointsThread is not None:
           self.questionPointsThread.cancel()

        if self.questionPoints is None:
            self.questionPoints = 100
        else:
            self.questionPoints -= 1
            
        self.getControl(4103).setLabel(str(self.questionPoints / 10.0))
        if self.questionPoints == 100:
            # three second head start
            self.questionPointsThread = threading.Timer(3, self._question_points)
            self.questionPointsThread.start()
        elif self.questionPoints > 10:
            seconds = (100 - self.questionPoints) / 100.0
            self.questionPointsThread = threading.Timer(seconds, self._question_points)
            self.questionPointsThread.start()
#        else:
#            self.questionPointsThread = None

    def _answer_correctly(self):
        answer = self.question.getCorrectAnswer()
        self._handle_answer(answer)

    def _handle_answer(self, answer):
        print "_handle_answer(..)"
        if self.questionPointsThread is not None:
           self.questionPointsThread.cancel()

        if answer is not None and answer.correct:
            xbmc.playSFX(AUDIO_CORRECT)
            self.gameType.addCorrectAnswer()
            self.gameType.addPoints(self.questionPoints / 10.0)
            self.getControl(self.C_MAIN_CORRECT_VISIBILITY).setVisible(False)
        else:
            xbmc.playSFX(AUDIO_WRONG)
            self.gameType.addWrongAnswer()
            self.getControl(self.C_MAIN_INCORRECT_VISIBILITY).setVisible(False)

        if self.player.isPlaying():
            self.player.stop()

        threading.Timer(0.5, self._hide_icons).start()
        if ADDON.getSetting('show.correct.answer') == 'true' and not answer.correct:
            for idx, answer in enumerate(self.question.getAnswers()):
                if answer.correct:
                    self.getControl(self.C_MAIN_FIRST_ANSWER + idx).setLabel('[B]%s[/B]' % answer.text)
                    self.setFocusId(self.C_MAIN_FIRST_ANSWER + idx)
                else:
                    self.getControl(self.C_MAIN_FIRST_ANSWER + idx).setLabel(textColor='0x88888888')

            if isinstance(self.question, question.QuoteDisplayType):
                # Display non-obfuscated quote text
                self.getControl(self.C_MAIN_QUOTE_LABEL).setText(self.question.getQuoteText())

            xbmc.sleep(3000)

        self._setup_question()

    def _update_stats(self):
        self.getControl(self.C_MAIN_CORRECT_SCORE).setLabel(str(self.gameType.points))
#        self.getControl(self.C_MAIN_INCORRECT_SCORE).setLabel(str(self.gameType.wrongAnswers))

        label = self.getControl(self.C_MAIN_QUESTION_COUNT)
        label.setLabel(self.gameType.getStatsString())
        
    def _update_thumb(self, controlId = None):
        if self.question is None:
            return # not initialized yet

        if controlId is None:
            controlId = self.getFocusId()
        if controlId >= self.C_MAIN_FIRST_ANSWER or controlId <= self.C_MAIN_LAST_ANSWER:
            answer = self.question.getAnswer(controlId - self.C_MAIN_FIRST_ANSWER)
            coverImage = self.getControl(self.C_MAIN_COVER_IMAGE)
            if answer is not None and answer.coverFile is not None and os.path.exists(answer.coverFile):
                coverImage.setVisible(True)
                coverImage.setImage(answer.coverFile)
            elif answer is not None and answer.coverFile is not None :
                path = ADDON.getAddonInfo('path')
                coverImage.setVisible(True)
                coverImage.setImage(os.path.join(path, 'resources', 'skins', 'Default', 'media', 'quiz-no-photo.png'))
            else:
                coverImage.setVisible(False)

    def _hide_icons(self):
        """Visibility is inverted in skin
        """
        self.getControl(self.C_MAIN_CORRECT_VISIBILITY).setVisible(True)
        self.getControl(self.C_MAIN_INCORRECT_VISIBILITY).setVisible(True)

    def _changeVisibility(self, video = False, photo = False, quote = False, threePhotos = False):
        """Visibility is inverted in skin
        """
        self.getControl(self.C_MAIN_VIDEO_VISIBILITY).setVisible(not video)
        self.getControl(self.C_MAIN_PHOTO_VISIBILITY).setVisible(not photo)
        self.getControl(self.C_MAIN_QUOTE_VISIBILITY).setVisible(not quote)
        self.getControl(self.C_MAIN_THREE_PHOTOS_VISIBILITY).setVisible(not threePhotos)
        
        self.getControl(self.C_MAIN_REPLAY_BUTTON_VISIBILITY).setEnabled(video)

    def _obfuscateQuote(self, quote):
        names = list()
        for m in re.finditer('(.*?:)', quote):
            name = m.group(1)
            if not name in names:
                names.append(name)

        for idx, name in enumerate(names):
            repl = '#%d:' % (idx + 1)
            quote = quote.replace(name, repl)

        return quote


class GameOverDialog(xbmcgui.WindowXMLDialog):
    C_GAMEOVER_RETRY = 4000
    C_GAMEOVER_MAINMENU = 4003

    def __new__(cls, parentWindow, correctAnswers, totalAnswers, score):
        return super(GameOverDialog, cls).__new__(cls, 'script-moviequiz-gameover.xml', ADDON.getAddonInfo('path'))

    def __init__(self, parentWindow, correctAnswers, totalAnswers, score):
        super(GameOverDialog, self).__init__()

        self.parentWindow = parentWindow
        self.correctAnswers = correctAnswers
        self.totalAnswers = totalAnswers
        self.score = score

    def onInit(self):
        self.getControl(4100).setLabel(strings(G_YOU_SCORED) % (self.correctAnswers, self.totalAnswers))
        self.getControl(4101).setLabel(str(self.score))

    def onAction(self, action):
        print "GameOverDialog.onAction " + str(action)

        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlId):
        print "GameOverDialog.onClick " + str(controlId)

        if controlId == self.C_GAMEOVER_RETRY:
            self.close()
            self.parentWindow.close()

            w = QuizGui(self.parentWindow.type, self.parentWindow.gameType, self.parentWindow.maxRating, self.parentWindow.interactive)
            w.doModal()
            del w

        elif controlId == self.C_GAMEOVER_MAINMENU:
            self.close()
            self.parentWindow.close()

    def onFocus(self, controlId):
        print "GameOverDialog.onFocus " + str(controlId)


class ClapperDialog(xbmcgui.WindowXMLDialog):
    C_CLAPPER_LINE1 = 4000
    C_CLAPPER_LINE2 = 4001
    C_CLAPPER_LINE3 = 4002

    def __new__(cls, line1 = None, line2 = None, line3 = None, autoClose = True):
        return super(ClapperDialog, cls).__new__(cls, 'script-moviequiz-clapper.xml', ADDON.getAddonInfo('path'))

    def __init__(self, line1 = None, line2 = None, line3 = None, autoClose = True):
        super(ClapperDialog, self).__init__()

        self.line1 = line1
        self.line2 = line2
        self.line3 = line3
        self.autoClose = autoClose
        self.timer = threading.Timer(5, self.delayedClose)

    def onInit(self):
        print "ClapperDialog.onInit"

        if self.line1 is None:
            self.line1 = ''
        if self.line2 is None:
            self.line2 = ''
        if self.line3 is None:
            self.line3 = ''

        self.getControl(self.C_CLAPPER_LINE1).setLabel(self.line1)
        self.getControl(self.C_CLAPPER_LINE2).setLabel(self.line2)
        self.getControl(self.C_CLAPPER_LINE3).setLabel(self.line3)

        if self.autoClose:
            self.timer.start()

    def delayedClose(self):
        print "ClapperDialog.delayedClose"
        self.close()

    def onAction(self, action):
        print "ClapperDialog.onAction " + str(action)
        self.timer.cancel()
        self.close()

    def onClick(self, controlId):
        print "ClapperDialog.onClick " + str(controlId)

    def onFocus(self, controlId):
        print "ClapperDialog.onFocus " + str(controlId)

