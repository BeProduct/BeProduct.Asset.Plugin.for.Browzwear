from wrappers.bwapi_wrapper import BwApiWrapper
from wrappers.asset_library import AssetLibrary, IAssetLibraryEvents, Asset
from wrappers.wnd import Wnd, IBwApiWndEvents
from .material_downloader import MaterialDownloader
from .asset_lib_remote_storage import AssetLibRemoteStorage
from resource_downloader import ResourceDownloader
from enum import Enum
import urllib.request
import urllib.parse
import threading
import json
import BwApi
import time

lock = threading.Lock()


class RemoteAssetLibrary(IAssetLibraryEvents, IBwApiWndEvents):
    class AssetLibError(Enum):
        Success = "Success",
        ConnectionError = "Error: connection issue. Check the connection and retry.",
        FileError = "Error: data missing or corrupted.",
        UnexpectedError = "Unexpected error."

    def __init__(self, library_json) -> None:
        # data from json
        self.library_data = None
        self.collections_data = None
        self.assets_data = None

        # library and collection objects
        self.library = None
        self.collections = None
        self.wnd = None

        self.material_downloader = MaterialDownloader(library_json)
        self.asset_lib_remote_storage = AssetLibRemoteStorage(library_json)
        self.resource_downloader = ResourceDownloader()

    def initialize(self) -> None:
        if not self.library:
            t = threading.Thread(target=self.__thread_fetch_library_info)
            t.start()

    def __initialize(self, data: object) -> None:
        try:

            if not data:
                return

            if "thumb" in data:
                thumb_url = urllib.parse.urljoin(
                    self.asset_lib_remote_storage.get_base_path(), data["thumb"])
                data["thumb"] = thumb_url

            # first initialize
            if not self.library:
                self.library = AssetLibrary.add_asset_library(data)

                if self.library:
                    self.library.set_delegate(self)

            # refresh library
            else:
                self.library.update_raw_data = data
                self.library_data = data
                self.collections_data = None
                self.assets_data = None
                self.collections = None
                self.on_list_collections(self.library)

        except Exception as e:
            raise Exception('{}'.format(e))

        lock.release()

    def __thread_fetch_library_info(self) -> None:
        try:
            self.library_data = self.asset_lib_remote_storage.get_library_info()
            lock.acquire()
            BwApiWrapper.invoke_on_main_thread(
                self.__initialize, self.library_data)

        except urllib.error.URLError as e:
            print(str(e))
            if e.reason == 'Not Found':
                BwApiWrapper.invoke_on_main_thread(
                    self.__set_error, RemoteAssetLibrary.AssetLibError.FileError)
            else:
                BwApiWrapper.invoke_on_main_thread(
                    self.__set_error, RemoteAssetLibrary.AssetLibError.ConnectionError)

        except Exception as e:
            BwApiWrapper.invoke_on_main_thread(
                self.__set_error, RemoteAssetLibrary.AssetLibError.UnexpectedError)

    def on_list_collections(self, library: "AssetLibrary") -> None:
        # make sure that our library id is the same as we got
        if self.library.get_id() != library.get_id():
            print("received incorrect data from event - on_list_collections")
            self.__set_error(RemoteAssetLibrary.AssetLibError.UnexpectedError)
            return

        # fetch collections only once
        if not self.collections:
            t = threading.Thread(target=self.__thread_fetch_collection)
            t.start()

    def __add_collections(self, data: object) -> None:
        if not data:
            return

        if self.collections:
            return  # initialized already

        self.collections = []
        for collection in data:
            new_collection = self.library.add_collection(collection)
            if new_collection:
                self.collections.append(new_collection)

        # fetch assets
        t = threading.Thread(target=self.__thread_fetch_assets)
        t.start()

    def __thread_fetch_collection(self) -> None:
        try:
            self.collections_data = json.loads(
                self.asset_lib_remote_storage.get_collections())
            BwApiWrapper.invoke_on_main_thread(
                self.__add_collections, self.collections_data)

        except urllib.error.URLError as e:
            print(str(e))
            if e.reason == 'Not Found':
                BwApiWrapper.invoke_on_main_thread(
                    self.__set_error, RemoteAssetLibrary.AssetLibError.FileError)
            else:
                BwApiWrapper.invoke_on_main_thread(
                    self.__set_error, RemoteAssetLibrary.AssetLibError.ConnectionError)

        except Exception as e:
            BwApiWrapper.invoke_on_main_thread(
                self.__set_error, RemoteAssetLibrary.AssetLibError.UnexpectedError)

    def __add_assets(self, data: object) -> None:
        if not data:
            return

        # dictionary from remote asset id to local asset id
        remote_id_to_local_id = {}
        assets = []

        # loop through all collections, add assets to library and to collection
        for collection in self.collections:
            # get the collection data as retrieved from the server
            collection_data = collection.get_raw_data()

            if not "assets" in collection_data:
                continue

            # loop through all asset ids
            for remote_asset_id in collection_data["assets"]:
                # make sure asset exist in the assets received from the server
                if remote_asset_id not in data:
                    continue

                asset = data[remote_asset_id]
                # update the thumb field to contain the full thumb url
                if "thumb" in asset:
                    thumb_url = urllib.parse.urljoin(
                        self.asset_lib_remote_storage.get_base_assets_path(live=asset["thumb"].startswith("__")), asset["thumb"])
                    asset["thumb"] = thumb_url

                if "placeholder_image" in asset:
                    asset["placeholder_image"] = urllib.parse.urljoin(
                        self.asset_lib_remote_storage.get_base_assets_path(), asset["placeholder_image"])

                # create the asset if not created already
                if remote_asset_id not in remote_id_to_local_id:
                    asset_obj = self.library.add_asset(asset)
                    if not asset_obj:
                        continue

                    assets.append(asset_obj)
                    remote_id_to_local_id[asset_obj.get_remote_id(
                    )] = asset_obj.get_id()

                collection.add_asset_to_collection(
                    remote_id_to_local_id[remote_asset_id])

    def __thread_fetch_assets(self) -> None:
        try:
            self.assets_data = json.loads(
                self.asset_lib_remote_storage.get_assets())
            BwApiWrapper.invoke_on_main_thread(
                self.__add_assets, self.assets_data)

        except urllib.error.URLError as e:
            print(str(e))
            if e.reason == 'Not Found':
                BwApiWrapper.invoke_on_main_thread(
                    self.__set_error, RemoteAssetLibrary.AssetLibError.FileError)
            else:
                BwApiWrapper.invoke_on_main_thread(
                    self.__set_error, RemoteAssetLibrary.AssetLibError.ConnectionError)

        except Exception as e:
            BwApiWrapper.invoke_on_main_thread(
                self.__set_error, RemoteAssetLibrary.AssetLibError.UnexpectedError)

    def on_download_asset(self, library_id: str, asset_id: int, resource: object) -> None:
        if not resource:
            self.library.__set_error(
                RemoteAssetLibrary.AssetLibError.UnexpectedError)
            return

        asset = Asset(library_id, asset_id)
        if not asset:
            self.library.__set_error(
                RemoteAssetLibrary.AssetLibError.UnexpectedError)
            return

        # make sure that the type is supported material type
        asset_type = asset.get_type()
        material_types = ["fabric", "artwork", "seam",
                          "trim", "trim_edge", "trim3d", "button", "zipper"]
        if not asset_type or asset_type not in material_types:
            self.library.__set_error(
                RemoteAssetLibrary.AssetLibError.UnexpectedError)
            return

        # for material we expect to see all the following field within the given resource object
        required_fields = ["garment_id", "colorway_id", "material_id"]
        for field in required_fields:
            if field not in resource:
                self.library.__set_error(
                    RemoteAssetLibrary.AssetLibError.UnexpectedError)
                return

        self.material_downloader.download(library_id, asset_id, resource)

    def on_refresh(self, library_id: str) -> None:
        t = threading.Thread(target=self.__thread_fetch_library_info)
        t.start()

    def on_external_link(self, library_id: str) -> None:
        if self.wnd:
            self.wnd.focus()
            return

        if not self.library:
            return

        data = self.library.get_raw_data()
        if 'external_resource' not in data:
            return

        external_resource = data['external_resource']
        if 'url' in external_resource:
            url = external_resource['url']
        if 'title' in external_resource:
            title = external_resource['title']
        if 'width' in external_resource:
            width = external_resource['width']
        if 'height' in external_resource:
            height = external_resource['height']
        if 'style' in external_resource:
            style = external_resource['style']

        # url = "/index.html" # NO COMMIT
        self.wnd = Wnd(url, title, width, height, style)
        self.wnd.set_delegate(self)
        self.wnd.create()

    def __set_error(self, asset_lib_error: "AssetLibError") -> None:
        if self.library:
            data = {"error": asset_lib_error.value[0]}
            self.library.update_asset_library(data)

    # -------------------------------------------------------------------------
    #  IBwApiWndEvents implementation
    # -------------------------------------------------------------------------
    def on_load(self, garment_id: str, callback_id: int, data: str) -> None:
        pass

    def on_close(self, garment_id: str, callback_id: int, data: str) -> None:
        self.wnd = None

    def on_msg(self, garment_id: str, callback_id: int, data: str) -> None:
        dataJson = json.loads(data)
        print('on html message {}'.format(data))

        required_fields = ['action', 'type', 'resource_id', 'url']
        for field in required_fields:
            if field not in dataJson:
                print('missing required field {}'.format(field))
                return

        if dataJson['action'] != 'download':
            return

        if dataJson['type'] != 'resource':
            return

        if self.wnd:
            BwApi.WndHTMLMessageSend(self.wnd.get_handle(), json.dumps({
                'type': 'download',
                'resource_id': dataJson['resource_id'],
                'url': dataJson['url'],
                'message': 'Downloading...'
            }))
        self.resource_downloader.download(
            dataJson['resource_id'], dataJson['url'], self.__download_callback)

    def on_uncaught_exception(self, garment_id: str, callback_id: int, data: str) -> None:
        pass

    def __download_callback(self, data: object):
        # notify the window about download and extract status
        print('reach download callback with {}'.format(data))
        execute_data = {
            'type': 'execute',
            'resource_id': data['resource_id'],
            'status': False,
            'response': {
                'message': 'failed to download or extract resource {}'.format(data['resource_id'])
            }
        }

        # notify the window for execute failure due to path not exist
        if data['status'] == False:
            BwApi.WndHTMLMessageSend(
                self.wnd.get_handle(), json.dumps(execute_data))
        else:
            try:
                import sys
                from importlib import import_module, reload
                sys.path.append(data['path'])

                # update the response message
                execute_data['response']['message'] = 'failed to execute resource {}'.format(
                    data['resource_id'])

                # load the main.py module
                module = import_module('bw_main')
                reload(module)  # force reloading already loaded module

                # execute the main function
                if hasattr(module, 'main'):
                    execute_data['response'] = module.main({
                        'hwnd': self.wnd.get_handle() if self.wnd else 0
                    })
                    execute_data['status'] = True
            except Exception as e:
                print('__download_callback reach exception: {}'.format(str(e)))
            finally:
                BwApi.WndHTMLMessageSend(
                    self.wnd.get_handle(), json.dumps(execute_data))
