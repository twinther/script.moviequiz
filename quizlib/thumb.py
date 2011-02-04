import xbmc

__author__ = 'tommy'

def getCachedThumb(file):
    if file[0:8] == 'stack://':
        commaPos = file.find(' , ')
        file = xbmc.getCacheThumbName(file[8:commaPos].strip())

    crc = xbmc.getCacheThumbName(file.lower())
    return xbmc.translatePath('special://profile/Thumbnails/Video/%s/%s' % (crc[0], crc))

