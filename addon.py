import os

from quizlib.gui import QuizGui

if __name__ == '__main__':
    w = QuizGui('script-moviequiz-main.xml', os.getcwd())
    w.doModal()
    del w

