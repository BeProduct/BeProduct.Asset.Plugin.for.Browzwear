import BwApi
import urllib.request
import urllib.parse
import urllib
import config
import os
from .beproduct_dev_app import BeProduct3DDevelopmentAssets

def __get_content__(url):
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)
    return response.read().decode('utf-8')


class BeProductBW(BwApi.CallbackBase):
    def Run(self, garmentId, callbackId, dataString):

        path_components = os.path.normpath(BwApi.GarmentPathGet(garmentId)).split(os.sep)
        ind = 0
        if path_components[-1].lower().endswith('.bw'):
            ind=1

        i = ind - 1
        filename = "%2F".join(map(urllib.parse.quote,path_components[:i if i != 0 else None]))
          
        # Sync style
        if callbackId == 0:
            BwApi.GarmentClose(garmentId, 0)
            if not config.USERID and not config.SYNC_STANDALONE:
                __get_content__(config.BASE_URL + "api/bw/sync-back/" + config.USERID)
            else:
                __get_content__(config.BASE_URL + "api/sync/sync?f=" + filename)
        
        # Refresh colors  
        if callbackId == 1:
            if BeProduct3DDevelopmentAssets.colors is not None:
                BwApi.ColorLibraryRemove(garmentId, BeProduct3DDevelopmentAssets.colors)
                colors_json = __get_content__(config.BASE_URL + "api/bw/colors?f=" + filename)
                BeProduct3DDevelopmentAssets.colors = BwApi.ColorLibraryCreate(garmentId, colors_json)

        if callbackId == 2:
            BwApi.GarmentClose(garmentId, 0)
            __get_content__(config.BASE_URL + "api/sync/offload/turntable?f=" + filename)
        return 0