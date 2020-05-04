from .common import EventHandler
from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum
import BwApi
import json

LIST_COLLECTIONS = 1
DOWNLOAD_ASSET = 2
EXTERNAL_LINK = 3
REFRESH = 4


class IAssetLibraryEvents(ABC):
    @abstractmethod
    def on_list_collections(self, library_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_download_asset(self, library_id: str, asset_id: int, resource: object) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_refresh(self, library_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_external_link(self, library_id: str) -> None:
        raise NotImplementedError

class Asset:
    class AssetState(Enum):
        ready = "ready"
        error = "error"

    def __init__(self, library_id: str, asset_id: int, data: object = None):
        self.library_id = library_id
        self.asset_id = asset_id
        self.data = data

    def get_id(self) -> int:
        return self.asset_id

    def get_metadata(self) -> Optional[str]:
        data_str = BwApi.AssetLibAssetGet(self.library_id, self.asset_id)

        if len(data_str) == 0:
            return None

        data = json.loads(data_str)
        if "metadata" not in data:
            return {}

        return data["metadata"]

    def get_remote_id(self) -> Optional[str]:
        data_str = BwApi.AssetLibAssetGet(self.library_id, self.asset_id)

        if len(data_str) == 0:
            return None

        data = json.loads(data_str)
        if "remote_id" not in data:
            return None

        return data["remote_id"]

    def get_raw_data(self) -> object:
        return self.data

    def get_type(self) -> Optional[str]:
        data_str = BwApi.AssetLibAssetGet(self.library_id, self.asset_id)

        if len(data_str) == 0:
            return None

        data = json.loads(data_str)
        if "type" not in data:
            return None

        return data["type"]

    def is_group(self) -> bool:
        data_str = BwApi.AssetLibAssetGet(self.library_id, self.asset_id)

        if len(data_str) == 0:
            return False

        data = json.loads(data_str)
        if "is_group" not in data:
            return False

        return data["is_group"]

    def get_name(self) -> bool:
        data_str = BwApi.AssetLibAssetGet(self.library_id, self.asset_id)

        if len(data_str) == 0:
            return False

        data = json.loads(data_str)
        if "name" not in data:
            return False

        return data["name"]

    def set_asset_state(self, asset_state: "AssetState", error: str = '') -> None:
        asset_state_json = {}
        if asset_state.value == Asset.AssetState.ready.value:
            asset_state_json = {"schema_version": 2, "state": asset_state.value}
        elif asset_state.value == Asset.AssetState.error.value:
            asset_state_json = {"schema_version": 2, "state": asset_state.value, "description": error if error else "Unexpected error."}
        BwApi.AssetLibAssetStateSet(self.library_id, self.asset_id, json.dumps(asset_state_json))


class Collection:
    def __init__(self, library_id: str, collection_id: int, data: object) -> None:
        self.library_id = library_id
        self.collection_id = collection_id
        self.data = data

    def get_id(self) -> int:
        return self.collection_id

    def get_raw_data(self) -> object:
        return self.data

    def add_asset_to_collection(self, asset_id: int) -> None:
        if asset_id != -1:
            BwApi.AssetLibCollectionAssetAdd(self.library_id, self.collection_id, asset_id)

    def clear_assets(self) -> None:
        asset_ids = BwApi.AssetLibCollectionAssetIds(self.library_id, self.collection_id)
        for asset_id in asset_ids:
            BwApi.AssetLibCollectionAssetRemove(self.library_id, self.collection_id, asset_id)


class AssetLibrary:
    def __init__(self, library_id: str, data: object):
        self.library_id = library_id
        self.delegate = None
        self.data = data
        self.event_handler = EventHandler(self.__event_handler)

        # register to asset library events
        BwApi.AssetLibEventRegister(self.library_id,
                                    BwApi.BW_API_EVENT_ASSET_LIB_INITIALIZE,
                                    self.event_handler,
                                    LIST_COLLECTIONS)
        BwApi.AssetLibEventRegister(self.library_id,
                                    BwApi.BW_API_EVENT_ASSET_LIB_DOWNLOAD_ASSET,
                                    self.event_handler,
                                    DOWNLOAD_ASSET)
        BwApi.AssetLibEventRegister(self.library_id,
                                    BwApi.BW_API_EVENT_ASSET_LIB_OPEN_EXTERNAL_LINK,
                                    self.event_handler,
                                    EXTERNAL_LINK)
        BwApi.AssetLibEventRegister(self.library_id,
                                    BwApi.BW_API_EVENT_ASSET_LIB_REFRESH,
                                    self.event_handler,
                                    REFRESH)

    def get_id(self):
        return self.library_id

    def get_raw_data(self) -> object:
        return self.data

    def update_raw_data(self, data: object) -> None:
        self.data = data

    def __event_handler(self, garment_id: str, callback_id: int, data: str) -> int:
        if not self.delegate:
            return 0

        if callback_id == LIST_COLLECTIONS:
            self.delegate.on_list_collections(self)

        elif callback_id == DOWNLOAD_ASSET:
            data_json = json.loads(data)

            if not data_json:
                return 0

            if "asset_id" not in data_json:
                return 0

            if "resource" not in data_json:
                return 0

            self.delegate.on_download_asset(self.get_id(), data_json["asset_id"], data_json["resource"])

        elif callback_id == EXTERNAL_LINK:
            self.delegate.on_external_link(self.get_id())

        elif callback_id == REFRESH:
            self.delegate.on_refresh(self.get_id())

        return 1

    def set_delegate(self, delegate: "IAssetLibraryEvents"):
        self.delegate = delegate

    @staticmethod
    def add_asset_library(data: object) -> Optional["AssetLibrary"]:
        library_id = BwApi.AssetLibAdd(json.dumps(data))
        if library_id:
            return AssetLibrary(library_id, data)

    def update_asset_library(self, data: object) -> None:
        BwApi.AssetLibUpdate(self.library_id, json.dumps(data))

    def add_collection(self, collection: object) -> Optional[Collection]:
        required_fields = ["remote_id", "name"]

        # make sure that the collection has all the required fields
        has_all_fields = True
        for field in required_fields:
            if field not in collection:
                has_all_fields = False

        if not has_all_fields:
            return None

        # define require fields for the API
        data = {"remote_id": collection["remote_id"], "name": collection["name"]}

        collection_id = BwApi.AssetLibCollectionAdd(self.library_id, json.dumps(data))
        if collection_id != -1:
            return Collection(self.library_id, collection_id, collection)

        return None

    def add_asset(self, asset: object) -> Optional[Asset]:
        required_fields = ["remote_id", "name", "version", "type", "thumb"]

        # make sure that the asset has all the required fields
        has_all_fields = True
        for field in required_fields:
            if field not in asset:
                has_all_fields = False
                break

        if not has_all_fields:
            return None

        # define require fields for the API
        data = {"remote_id": asset["remote_id"], "name": asset["name"], "version": asset["version"],
                "type": asset["type"],
                "thumb": asset["thumb"]}
        if "placeholder_image" in asset:
            data["placeholder_image"] = asset["placeholder_image"]
        if "is_group" in asset:
            data["is_group"] = asset["is_group"]
        if "version_tag" in asset:
            data["version_tag"] = asset["version_tag"]
        if "metadata" in asset:
            data["metadata"] = asset["metadata"]

        asset_id = BwApi.AssetLibAssetAdd(self.library_id, json.dumps(data))
        if asset_id != -1:
            asset = Asset(self.library_id, asset_id, asset)
            return asset

        return None

    def remove_asset(self, asset_id: int):
        BwApi.AssetLibAssetRemove(self.library_id, asset_id)
