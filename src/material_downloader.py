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

        #if asset.is_group():
        #    self.download_pool.submit(self.__thread_download_group_material, asset.get_remote_id(), resource)
        #else:
        self.download_pool.submit(self.__thread_download_simple_material, asset.get_remote_id(), resource)

    def __download_material(self, tmp_dir: str, remote_id: str, resource_json: object) -> object:
        try:
            # first, download material.json from the server

            resource_rel_path = urllib.parse.urljoin(remote_id, resource_json['resource_path'] if 'resource_path' in resource_json else '')

            if not resource_rel_path.endswith('/'):  # need to add \ in the resource file
                resource_rel_path = resource_rel_path + '/'

            resource_file = resource_json['resource_file']
            material_json_rel_path = urllib.parse.urljoin(resource_rel_path, resource_file)
            base_assets_path = self.asset_lib_remote_storage.get_base_assets_path()

            material_json = load_remote_json(urllib.parse.urljoin(base_assets_path, material_json_rel_path))

            sides = ['front', 'back']
            for side in sides:
                if side in material_json:
                    # loop through all channels and download the images
                    channels = ['diffuse', 'specular', 'normal']
                    for channel in channels:
                        if channel not in material_json[side]:
                            continue

                        if 'texture_map' not in material_json[side][channel]:
                            continue

                        if 'image_path' not in material_json[side][channel]['texture_map']:
                            continue

                        image_rel_path = material_json[side][channel]['texture_map']['image_path']
                        # here we need to download the remote image

                        if image_rel_path != '':

                            # update the image path with the downloaded path
                            image_rel_path = urllib.parse.urljoin(resource_rel_path, image_rel_path)

                            download_remote_resource(os.path.join(tmp_dir, image_rel_path), urllib.parse.urljoin(base_assets_path, image_rel_path))

                            material_json[side][channel]['texture_map']['image_path'] = os.path.join(tmp_dir, os.path.normpath(image_rel_path))

                        else:
                            material_json[side][channel]['texture_map']['image_path'] = ''

            channels = ['diffuse', 'specular', 'normal']
            for channel in channels:  # In case of trim3d
                if channel not in material_json:
                    continue

                if 'texture_map' not in material_json[channel]:
                    continue

                if 'image_path' not in material_json[channel]['texture_map']:
                    continue

                image_rel_path = material_json[channel]['texture_map']['image_path']
                # here we need to download the remote image

                # update the image path with the downloaded path
                image_rel_path = urllib.parse.urljoin(resource_rel_path, image_rel_path)

                download_remote_resource(os.path.join(tmp_dir, image_rel_path), urllib.parse.urljoin(base_assets_path, image_rel_path))

                material_json[channel]['texture_map']['image_path'] = os.path.join(tmp_dir, os.path.normpath(image_rel_path))

            # if material_json['type'] == 'trim3d':
            #     obj_rel_path = material_json['path']
            #     obj_rel_path = urllib.parse.urljoin(resource_rel_path, obj_rel_path)
            #     download_remote_resource(os.path.join(tmp_dir, obj_rel_path), urllib.parse.urljoin(base_assets_path, obj_rel_path))
            #     material_json['path'] = os.path.join(tmp_dir, obj_rel_path)

            return material_json

        except urllib.error.URLError as e:
            print(str(e))
            if e.reason == 'Not Found':
                resource_json['error'] = 'Error: file missing or corrupted'
            else:
                resource_json['error'] = 'Error: connection issue. Check the connection and retry.'

            BwApiWrapper.invoke_on_main_thread(self.__set_asset_in_error_mode, resource_json)
        except Exception as e:
            print(str(e))
            BwApiWrapper.invoke_on_main_thread(self.__set_asset_in_error_mode, resource_json)

    def __download_material1(self, tmp_dir: str, remote_id: str, resource_json: object) -> object:
        try:
            # first, download material.json from the server

            base_assets_path = self.asset_lib_remote_storage.get_base_assets_path()
            resource_rel_path = urllib.parse.urljoin(remote_id, resource_json[
                'resource_path'] if 'resource_path' in resource_json else '')

            if not resource_rel_path.endswith('/'):  # need to add \ in the resource file
                resource_rel_path = resource_rel_path + '/'

            resource_file = resource_json['resource_file']
            material_json_rel_path = urllib.parse.urljoin(resource_rel_path, resource_file)

            material_json = load_remote_json(urllib.parse.urljoin(base_assets_path, material_json_rel_path))

            sides = ['front', 'back']
            for side in sides:
                if side in material_json:
                    # loop through all channels and download the images
                    channels = ['diffuse', 'specular', 'normal']
                    for channel in channels:
                        if channel not in material_json[side]:
                            continue

                        if 'texture_map' not in material_json[side][channel]:
                            continue

                        if 'image_path' not in material_json[side][channel]['texture_map']:
                            continue

                        image_rel_path = material_json[side][channel]['texture_map']['image_path']
                        # here we need to download the remote image

                        if image_rel_path != '':

                            # update the image path with the downloaded path
                            image_rel_path = urllib.parse.urljoin(resource_rel_path, image_rel_path)

                            download_remote_resource(os.path.join(tmp_dir, image_rel_path),
                                                     urllib.parse.urljoin(base_assets_path, image_rel_path))

                            material_json[side][channel]['texture_map']['image_path'] = os.path.join(tmp_dir,
                                                                                                     image_rel_path)

                        else:
                            material_json[side][channel]['texture_map']['image_path'] = ''

            channels = ['diffuse', 'specular', 'normal']
            for channel in channels:  # In case of trim3d
                if channel not in material_json:
                    continue

                if 'texture_map' not in material_json[channel]:
                    continue

                if 'image_path' not in material_json[channel]['texture_map']:
                    continue

                image_rel_path = material_json[channel]['texture_map']['image_path']
                # here we need to download the remote image

                # update the image path with the downloaded path
                image_rel_path = urllib.parse.urljoin(resource_rel_path, image_rel_path)

                download_remote_resource(os.path.join(tmp_dir, image_rel_path),
                                         urllib.parse.urljoin(base_assets_path, image_rel_path))

                material_json[channel]['texture_map']['image_path'] = os.path.join(tmp_dir, image_rel_path)

            if material_json['type'] == 'trim3d':
                obj_rel_path = material_json['path']
                obj_rel_path = urllib.parse.urljoin(resource_rel_path, obj_rel_path)
                download_remote_resource(os.path.join(tmp_dir, obj_rel_path),
                                         urllib.parse.urljoin(base_assets_path, obj_rel_path))
                material_json['path'] = os.path.join(tmp_dir, obj_rel_path)

            return material_json

        except urllib.error.URLError as e:
            print(str(e))
            if e.reason == 'Not Found':
                resource_json['error'] = 'Error: file missing or corrupted'
            else:
                resource_json['error'] = 'Error: connection issue. Check the connection and retry.'

            BwApiWrapper.invoke_on_main_thread(self.__set_asset_in_error_mode, resource_json)
        except Exception as e:
            print(str(e))
            BwApiWrapper.invoke_on_main_thread(self.__set_asset_in_error_mode, resource_json)

    def __thread_download_simple_material(self, remote_id: str, resource: object):
        try:
            remote_id = remote_id + '/'

            tmp_dir = tempfile.mkdtemp()

            base_assets_path = self.asset_lib_remote_storage.get_base_assets_path(live=remote_id.startswith("__LIVE__"))

            resource_path = urllib.parse.urljoin(base_assets_path, remote_id)
            resource_json_path = urllib.parse.urljoin(resource_path, 'resource.json')



            resource_json = load_remote_json(resource_json_path)

            filename, file_extension = os.path.splitext(resource_json[0]['resource_file'])
            resource['tmp_dir'] = tmp_dir

            if file_extension == '.u3ma':
                download_remote_resource(os.path.join(tmp_dir, remote_id, resource_json[0]['resource_file']),
                                        urllib.parse.urljoin(resource_path, urllib.parse.quote(resource_json[0]['resource_file'])))
                resource['material'] = os.path.join(tmp_dir, remote_id,  resource_json[0]['resource_file'])
                BwApiWrapper.invoke_on_main_thread(self.__update_u3ma, resource)
            else:
                # once completed update the material on the main thread and update it's state
                resource['material'] = self.__download_material1(tmp_dir, remote_id, resource_json[0])
                BwApiWrapper.invoke_on_main_thread(self.__update_simple_material, resource)

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
            successful = True
        except:
            pass

        library_id = downloaded_material['library_id']
        asset_id = downloaded_material['asset_id']

        asset = Asset(library_id, asset_id)
        if not asset:
            return

        asset.set_asset_state(Asset.AssetState.ready if successful else Asset.AssetState.error)


    def __update_simple_material(self, downloaded_material: object) -> None:
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
            material.update(downloaded_material['material'])
            successful = True
        except:
            pass

        library_id = downloaded_material['library_id']
        asset_id = downloaded_material['asset_id']

        asset = Asset(library_id, asset_id)
        if not asset:
            return

        asset.set_asset_state(Asset.AssetState.ready if successful else Asset.AssetState.error)

        # os.rmdir(downloaded_material['tmp_dir']) # clean up

    def __thread_download_group_material(self, remote_id: str, resource: object):
        try:
            remote_id = remote_id + '/'

            tmp_dir = tempfile.mkdtemp()

            base_assets_path = self.asset_lib_remote_storage.get_base_assets_path()

            resource_path = urllib.parse.urljoin(base_assets_path, remote_id)
            resource_json_path = urllib.parse.urljoin(resource_path, 'resource.json')

            resource_json = load_remote_json(resource_json_path)

            resource['resources'] = []

            for group_resource in resource_json:

                group_resource['library_id'] = resource['library_id']  # Incase of error
                group_resource['asset_id'] = resource['asset_id']  # Incase of error

                resource_item = {}
                resource_item['primary_material'] = group_resource['primary_material'] if 'primary_material' in group_resource else False
                if 'type' in group_resource:
                    resource_item['type'] = group_resource['type']

                resource_item['material'] = self.__download_material(tmp_dir, remote_id, group_resource)

                resource['resources'].append(resource_item)

            resource['tmp_dir'] = tmp_dir

            BwApiWrapper.invoke_on_main_thread(self.__update_group_material, resource)

        except Exception as e:
            print(str(e))
            BwApiWrapper.invoke_on_main_thread(self.__set_asset_in_error_mode, resource)

    def __update_group_material(self, downloaded_group_material: object) -> None:
        successful = True
        try:
            required_fiedls = ['garment_id', 'colorway_id', 'material_id', 'resources']
            for field in required_fiedls:
                if field not in downloaded_group_material:
                    raise Exception('Field is missing')


            garment_id = downloaded_group_material['garment_id']
            colorway_id = downloaded_group_material['colorway_id']
            material_id = downloaded_group_material['material_id']

            library_id = downloaded_group_material['library_id']
            asset_id = downloaded_group_material['asset_id']

            asset = Asset(library_id, asset_id)
            if not asset:
                raise Exception('Asset not exist')

            group_material = Material(garment_id, colorway_id, material_id)

            colorway = Colorway(garment_id, colorway_id)
            group_material.group_clear_items()

            primary_material_id = None

            if asset.get_type() == 'button' or asset.get_type() == 'zipper':

                for material_in_group in downloaded_group_material['resources']:
                    for group_material_id in group_material.group_item_ids_get():
                        group_item = group_material.group_item_get(group_material_id)
                        if material_in_group['type'] == group_item['type']:
                            group_item_material = Material(garment_id, colorway_id, group_material_id)
                            group_item_material.update(material_in_group['material'])
                            break
                        elif material_in_group['type'] == 'draw_cord':
                            colorway = Colorway(garment_id, colorway_id)
                            drawcord_material_id = colorway.create_material(material_in_group['material'])
                            # drawcord_material = Material(garment_id, colorway_id, drawcord_material_id)
                            group_material.group_item_add(drawcord_material_id, {'type': 'draw_cord'})
                            break

            else:
                for material_in_group in downloaded_group_material['resources']:
                    material_id = colorway.create_material(material_in_group['material'])
                    group_item_json = {'type': material_in_group['material']['type']}
                    group_material.group_item_add(material_id, group_item_json)

                    if 'primary_material' in material_in_group:
                        primary_material_id = material_id

            if primary_material_id is not None:
                group_material.group_update({'group_name': asset.get_name(), 'type': asset.get_type(), 'physics_material_Id': primary_material_id})
            else:
                group_material.group_update({'group_name': asset.get_name(), 'type': asset.get_type()})

        except Exception as e:
            print(str(e))
            successful = False

        library_id = downloaded_group_material['library_id']
        asset_id = downloaded_group_material['asset_id']

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
