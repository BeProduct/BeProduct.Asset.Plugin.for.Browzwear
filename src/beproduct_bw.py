import BwApi
import urllib.request
import urllib.parse
import urllib

from urllib.parse import urlencode
import config
import os
import json
from .beproduct_dev_app import BeProduct3DDevelopmentAssets

def __get_content__(url):
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)
    return response.read().decode('utf-8')

def __post_content__(url, body):
    try:
        headers = {'content-type': 'application/json'}
        req = urllib.request.Request(url,data=json.dumps(body).encode('utf-8'), headers=headers )
        return urllib.request.urlopen(req, context=config.SSL_CONTEXT).read().decode('utf-8')
    except Exception as e:
        return None

def get_file_info():
    try:
        garment_id = BwApi.GarmentId()
        info = {}

        # Snapshots
        snapshots = []
        snapshot_ids = BwApi.GarmentSnapshotIds(garment_id)
        for snapshot_id in snapshot_ids:
            snapshots.append({ "id":snapshot_id, "data":json.loads(BwApi.SnapshotInfoGet(garment_id, snapshot_id))})
        info["snapshots"] = snapshots

        # Colorways
        colorways = []
        colorway_ids = BwApi.GarmentColorwayIds(garment_id)
        for colorway_id in colorway_ids:
            colorways.append ({"id": colorway_id, "name": BwApi.ColorwayNameGet(garment_id, colorway_id)}) 
        info["colorways"] = colorways
        return info
    except:
        return None


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

        if callbackId == 3:
            info = get_file_info()
            if info is not None:
                BwApi.GarmentClose(garmentId, 0)
                info["title"] = "Generate Turntable"
                __post_content__(config.BASE_URL + "api/sync/wizard/turntable?f=" + filename, info)

        return 0