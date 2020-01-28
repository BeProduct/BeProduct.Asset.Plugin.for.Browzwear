import BwApi
import urllib.request
import urllib.parse
import urllib
import config
import os


def __get_content__(url):
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)


class BeProductBW(BwApi.CallbackBase):
    def Run(self, garmentId, callbackId, dataString):
        path_components = os.path.normpath(BwApi.GarmentPathGet(garmentId)).split(os.sep)
        BwApi.GarmentClose(garmentId, 1)
        if not config.USERID:
            __get_content__(config.BASE_URL + "api/bw/sync-back/" + config.USERID)
        else:
            __get_content__(config.BASE_URL + "api/bw/sync-back/" + config.USERID + path_components[-3] + "/" + urllib.parse.quote(path_components[-2]))
        return 0