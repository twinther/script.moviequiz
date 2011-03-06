import xbmc
import xbmcaddon
import sys

from quizlib.gui import MenuGui, QuizGui
import quizlib.question as question

def runStandalone(addon, path):
    xbmc.log("Starting Movie Quiz in standalone mode")

    w = MenuGui('script-moviequiz-menu.xml', path, addon = addon)
    w.doModal()
    del w

def runCinemaExperience(addon, path, type, automatic, maxRating, genre, questionLimit):
    xbmc.log("Starting Movie Quiz in Cinema Experience mode")

    w = QuizGui('script-moviequiz-main.xml', path, addon=addon, type=type)
    w.doModal()
    del w


if __name__ == '__main__':
    addon = xbmcaddon.Addon(id = 'script.moviequiz')
    path = addon.getAddonInfo('path')

    sys.argv = ['movies;automatic;;comedy;5']

    if len(sys.argv) > 0 and sys.argv[0].strip() != '':
        args = sys.argv[0].split(';')

        if args[0] == 'movies':
            type = question.TYPE_MOVIE
        else:
            type = question.TYPE_TV
        if args[1] == 'automatic':
            automatic = True
        else:
            automatic = False
        maxRating = args[2]
        genre = args[3]
        questionLimit = int(args[4])

        runCinemaExperience(addon, path, type, automatic, maxRating, genre, questionLimit)
    
    else:
        runStandalone(addon, path)

