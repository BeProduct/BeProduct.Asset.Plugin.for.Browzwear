import BwApi
import urllib.request
import urllib.parse
import urllib
import config


def __get_content__(url):
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)


class BeProductBW(BwApi.CallbackBase):
    def Run(self, garmentId, callbackId, dataString):
        BwApi.GarmentClose(garmentId, 1)
        __get_content__(config.BASE_URL + "api/bw/sync-back")
        return 0
