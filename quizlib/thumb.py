import xbmc

__author__ = 'tommy'

def getCachedThumb(file):
    crc = xbmc.getCacheThumbName(file.lower())
    return xbmc.translatePath('special://profile/Thumbnails/Video/%s/%s' % (crc[0], crc))
