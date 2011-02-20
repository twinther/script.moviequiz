import xbmcaddon

Q_WHAT_MOVIE_IS_THIS = 30400
Q_WHAT_MOVIE_IS_ACTOR_NOT_IN = 30401
Q_WHAT_YEAR_WAS_MOVIE_RELEASED = 30402
Q_WHAT_TAGLINE_BELONGS_TO_MOVIE = 30403
Q_WHO_DIRECTED_THIS_MOVIE = 30404
Q_WHAT_STUDIO_RELEASED_MOVIE = 30405
Q_WHAT_ACTOR_IS_THIS = 30406

G_QUESTION_X_OF_Y = 30000

M_COLLECTION_TRIVIA = 30110
M_MOVIE_COUNT = 30111
M_ACTOR_COUNT = 30112
M_DIRECTOR_COUNT = 30113
M_STUDIO_COUNT = 30114
M_HOURS_OF_ENTERTAINMENT = 30115

def strings(id, replacements = None):
    string = xbmcaddon.Addon(id = 'script.moviequiz').getLocalizedString(id)
    if replacements is not None:
        return string % replacements
    else:
        return string