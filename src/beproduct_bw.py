import BwApi
import urllib.request
import urllib.parse
import urllib

from urllib.parse import urlencode
import config
import os
import json
from datetime import datetime as dt
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
        if hasattr(BwApi,'GarmentSnapshotIdsEx'):
            snapshot_ids = BwApi.GarmentSnapshotIdsEx(garment_id)
        else:
            snapshot_ids = BwApi.GarmentSnapshotIds(garment_id)

        sorted_snapshots = []
        for snapshot_id in snapshot_ids:
            sn = json.loads(BwApi.SnapshotInfoGet(garment_id, snapshot_id))
            if 'name' not in sn:
                sn['name'] = snapshot_id

            sorted_snapshots.append({"id":snapshot_id,"data":sn})
        if(len(sorted_snapshots)):
            sorted_snapshots.sort(key=lambda x: x["data"]["created_date"], reverse=True)
        info["snapshots"] = sorted_snapshots

        # Colorways
        colorways = []
        colorway_ids = BwApi.GarmentColorwayIds(garment_id)
        for colorway_id in colorway_ids:
            colorways.append ({"id": colorway_id, "name": BwApi.ColorwayNameGet(garment_id, colorway_id)}) 
        info["colorways"] = colorways
        #info["vstitcherVersion"] = json.loads(BwApi.HostApplicationGet())["version"]
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
            if BeProduct3DDevelopmentAssets.colors:
                while BeProduct3DDevelopmentAssets.colors:
                    BwApi.ColorLibraryRemove(garmentId, BeProduct3DDevelopmentAssets.colors.pop(0))

                colors_json = __get_content__(config.BASE_URL + "api/bw/colors?nocache=true&api-version=2.0&f=" + filename)
                for col in json.loads(colors_json):
                    BeProduct3DDevelopmentAssets.colors = BwApi.ColorLibraryCreate(garmentId, json.dumps(col)) 

        if callbackId == 2:
            BwApi.GarmentClose(garmentId, 0)
            __get_content__(config.BASE_URL + "api/sync/offload/turntable?f=" + filename)

        if callbackId == 3:

            if hasattr(BwApi,'GarmentSnapshotIdsEx'):
                snapshot_ids = BwApi.GarmentSnapshotIdsEx(garmentId)
            else:
                snapshot_ids = BwApi.GarmentSnapshotIds(garmentId)
            sorted_snapshots = []
            for snapshot_id in snapshot_ids:
                sn = json.loads(BwApi.SnapshotInfoGet(garmentId, snapshot_id))
                if 'name' not in sn:
                    sn['name'] = snapshot_id
                sorted_snapshots.append({"id":snapshot_id,"data":sn})

            for sn in sorted_snapshots:
                if sn["data"]["name"] == 'BeProduct Sync':
                    BwApi.SnapshotDelete(garmentId, sn['id'])
            BwApi.SnapshotSave(garmentId, 'BeProduct Sync')

            info = get_file_info()
            if info is not None:
                BwApi.GarmentClose(garmentId, 0)
                info["title"] = "Generate Turntable"
                __post_content__(config.BASE_URL + "api/sync/wizard/turntable?f=" + filename, info)

        return 0