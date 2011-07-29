import datetime

from strings import *

class GameType(object):
    def __init__(self):
        self.points = 0
        self.correctAnswers = 0
        self.wrongAnswers = 0

    def addPoints(self, points):
        self.points += points

    def addCorrectAnswer(self):
        self.correctAnswers += 1

    def addWrongAnswer(self):
        self.wrongAnswers += 1
        
    def isGameOver(self):
        raise

    def getStatsString(self):
        return ''

    def getIdentifier(self):
        raise

class UnlimitedGameType(GameType):
    def __init__(self):
        super(UnlimitedGameType, self).__init__()

    def isGameOver(self):
        return False

    def getIdentifier(self):
        return 'unlimited'

class QuestionLimitedGameType(GameType):
    def __init__(self, questionLimit):
        super(QuestionLimitedGameType, self).__init__()
        self.questionLimit = questionLimit
        self.questionCount = 0

    def isGameOver(self):
        self.questionCount += 1
        return self.correctAnswers + self.wrongAnswers >= self.questionLimit

    def getStatsString(self):
        questionsLeft = self.questionLimit - self.questionCount
        if not questionsLeft:
            return "Last question"
        else:
            return str(questionsLeft) + " questions left"
        #return strings(G_QUESTION_X_OF_Y, (self.questionCount, self.questionLimit))

    def getIdentifier(self):
        return 'question-limited-' + str(self.questionLimit)

class TimeLimitedGameType(GameType):
    def __init__(self, timeLimitMinutes):
        super(TimeLimitedGameType, self).__init__()
        self.startTime = datetime.datetime.now()
        self.timeLimitMinutes = timeLimitMinutes

    def isGameOver(self):
        return self._minutesLeft() >= self.timeLimitMinutes

    def getStatsString(self):
        return str(self.timeLimitMinutes - self._minutesLeft()) + " mins. left"

    def _minutesLeft(self):
        delta = datetime.datetime.now() - self.startTime
        print delta
        return delta.seconds / 60

    def getIdentifier(self):
        return 'time-limited-' + str(self.timeLimitMinutes)

