import xbmcaddon

Q_WHAT_MOVIE_IS_THIS = 30400
Q_WHAT_MOVIE_IS_ACTOR_NOT_IN = 30401
Q_WHAT_YEAR_WAS_MOVIE_RELEASED = 30402
Q_WHAT_TAGLINE_BELONGS_TO_MOVIE = 30403
Q_WHO_DIRECTED_THIS_MOVIE = 30404
Q_WHAT_STUDIO_RELEASED_MOVIE = 30405

def strings(id, replacements):
    string = xbmcaddon.Addon(id = 'script.moviequiz').getLocalizedString(id)
    if replacements:
        return string % replacements
    else:
        return string