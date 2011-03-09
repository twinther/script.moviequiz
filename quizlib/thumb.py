import xbmc

__author__ = 'tommy'

def getCachedThumb(file):
    if file[0:8] == 'stack://':
        commaPos = file.find(' , ')
        file = xbmc.getCacheThumbName(file[8:commaPos].strip())

    crc = xbmc.getCacheThumbName(file.lower())
    return xbmc.translatePath('special://profile/Thumbnails/Video/%s/%s' % (crc[0], crc))

def getCachedActorThumb(name):
    return getCachedThumb('actor' + name)

def getCachedSeasonThumb(path, label):
    """
    Keyword arguments:
    label - the localized string representation of the season.
            for English this can be Specials, Season 1, Season 10, etc

    """
    return getCachedThumb('season' + path + label)

def getCachedTVShowThumb(path):
    return getCachedThumb(path)