from wrappers.asset_library import Asset
from wrappers.bwapi_wrapper import BwApiWrapper
from wrappers.material import Material
from wrappers.colorway import Colorway
from .asset_lib_remote_storage import AssetLibRemoteStorage
from concurrent.futures import ThreadPoolExecutor
import tempfile
import config
import urllib.request
import urllib.parse
import json
import os
import BwApi


def load_remote_json(url: str) -> object:
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)
    return json.loads(response.read().decode('utf-8'))

def download_remote_resource(dest_folder: str, source_url: str) -> None:
    response = urllib.request.urlopen(source_url, context=config.SSL_CONTEXT)
    text = response.read()

    if not os.path.exists(os.path.dirname(dest_folder)):
        os.makedirs(os.path.dirname(dest_folder))

    output = open(dest_folder, 'wb')
    output.write(text)
    output.close()


class MaterialDownloader:
    def __init__(self, library_json):
        self.download_pool = ThreadPoolExecutor(max_workers=4)
        self.asset_lib_remote_storage = AssetLibRemoteStorage(library_json)

    def download(self, library_id: str, asset_id: int, resource: object) -> None:
        asset = Asset(library_id, asset_id)
        if not asset:
            return

        resource['library_id'] = library_id
        resource['asset_id'] = asset_id
        resource['metadata'] = asset.get_metadata()
        self.download_pool.submit(self.__thread_download_simple_material, asset.get_remote_id(), resource)

 
    def __thread_download_simple_material(self, remote_id: str, resource: object):
        try:
            remote_id = remote_id + '/'

            tmp_dir = tempfile.mkdtemp()

            res_id = resource['metadata']['asset_path'] if 'asset_path' in resource['metadata'] else remote_id
            base_assets_path = self.asset_lib_remote_storage.get_base_assets_path(live=res_id.startswith("__"))

            resource_path = urllib.parse.urljoin(base_assets_path,res_id)
            resource_json_path = urllib.parse.urljoin(resource_path, 'resource.json')



            resource_json = load_remote_json(resource_json_path)

            filename, file_extension = os.path.splitext(resource_json[0]['resource_file'])
            resource['tmp_dir'] = tmp_dir

            download_remote_resource(os.path.join(tmp_dir, remote_id, resource_json[0]['resource_file']),
                                    urllib.parse.urljoin(resource_path, urllib.parse.quote(resource_json[0]['resource_file'])))
            resource['material'] = os.path.join(tmp_dir, remote_id,  resource_json[0]['resource_file'])
            BwApiWrapper.invoke_on_main_thread(self.__update_u3ma, resource)

        except urllib.error.URLError as e:
            print(str(e))
            if e.reason == 'Not Found':
                resource['error'] = 'Error: file missing or corrupted.'
            else:
                resource['error'] = 'Error: connection issue. Check the connection and retry.'

            BwApiWrapper.invoke_on_main_thread(self.__set_asset_in_error_mode, resource)
        except Exception as e:
            print(str(e))
            BwApiWrapper.invoke_on_main_thread(self.__set_asset_in_error_mode, resource)


    def __update_u3ma(self, downloaded_material: object) -> None:
        successful = False
        try:

            required_fiedls = ['garment_id', 'colorway_id', 'material_id', 'material']
            for field in required_fiedls:
                if field not in downloaded_material:
                    return

            
            garment_id = downloaded_material['garment_id']
            colorway_id = downloaded_material['colorway_id']
            material_id = downloaded_material['material_id']


            material = Material(garment_id, colorway_id, material_id)
            material.update_from_file(downloaded_material['material'])

            def inject_bp(mat):
                mat['custom'] = mat.get('custom',{})
                mat['custom']['BeProduct'] = mat['custom'].get('BeProduct',{})
                mat['custom']['BeProduct']["info"] = downloaded_material['metadata']
                mat['custom']['BeProduct']["materialId"] = None
                mat['custom']['BeProduct']["materialColorId"] = None

            is_group = BwApi.MaterialGroup(garment_id, colorway_id, material_id)

            if is_group:    
                
                mat = json.loads(BwApi.MaterialGroupGet(garment_id, colorway_id, material_id))
                inject_bp(mat)
                res = BwApi.MaterialGroupUpdate(garment_id, colorway_id, material_id, json.dumps({"description":"not working"})) 
            else:
                mat = json.loads(BwApi.MaterialGet(garment_id, colorway_id, material_id))
                inject_bp(mat)
                BwApi.MaterialUpdate(garment_id, colorway_id, material_id, json.dumps(mat))

            #with open('/tmp/test.json','w') as f:
            #    json.dump(mat,f)
            # BwApi.WndMessageBox( json.dumps(mat), BwApi.BW_API_MB_OK)
            successful = True
        except:
            pass

        library_id = downloaded_material['library_id']
        asset_id = downloaded_material['asset_id']

        asset = Asset(library_id, asset_id)
        if not asset:
            return

        asset.set_asset_state(Asset.AssetState.ready if successful else Asset.AssetState.error)


    def __set_asset_in_error_mode(self, resource: object) -> None:
        library_id = resource['library_id']
        asset_id = resource['asset_id']

        asset = Asset(library_id, asset_id)
        if not asset:
            return

        asset.set_asset_state(Asset.AssetState.error, resource['error'] if 'error' in resource else '')
