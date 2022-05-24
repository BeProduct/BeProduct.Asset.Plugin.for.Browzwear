import BwApi
from wrappers.wnd import Wnd, IBwApiWndEvents

import urllib.request
import urllib.parse
import urllib

from urllib.parse import urlencode
import config
import os
import json
import uuid
import base64
from datetime import datetime as dt
from .beproduct_dev_app import BeProduct3DDevelopmentAssets


def __get_content__(url):
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)
    return response.read().decode("utf-8")


def __post_content__(url, body):
    try:
        headers = {"content-type": "application/json"}
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), headers=headers
        )
        return (
            urllib.request.urlopen(req, context=config.SSL_CONTEXT)
            .read()
            .decode("utf-8")
        )
    except Exception as e:
        return None


def get_local_settings():
    settings = {}

    def o(l):
        light = json.loads(BwApi.EnvironmentLightInfoGet(l))
        return {
            "name": l,
            "exposure": light["exposure"],
            "rotationAngle": light["rotation_angle"],
        }

    settings["lights"] = [o(l) for l in BwApi.EnvironmentLights()]

    default_camera_views = ["Front", "Left", "Back", "Right", "Top", "Bottom"]
    settings["cameraViews"] = [
        cv for cv in BwApi.EnvironmentCameraViews() if cv not in default_camera_views
    ]
    return settings


def get_file_info():
    try:
        garment_id = BwApi.GarmentId()
        info = {}

        # Snapshots
        if hasattr(BwApi, "GarmentSnapshotIdsEx"):
            snapshot_ids = BwApi.GarmentSnapshotIdsEx(garment_id)
        else:
            snapshot_ids = BwApi.GarmentSnapshotIds(garment_id)

        sorted_snapshots = []
        for snapshot_id in snapshot_ids:
            sn = json.loads(BwApi.SnapshotInfoGet(garment_id, snapshot_id))
            if "name" not in sn:
                sn["name"] = snapshot_id

            sorted_snapshots.append({"id": snapshot_id, "data": sn})
        if len(sorted_snapshots):
            sorted_snapshots.sort(key=lambda x: x["data"]["created_date"], reverse=True)
        info["snapshots"] = sorted_snapshots

        # Colorways
        colorways = []
        colorway_ids = BwApi.GarmentColorwayIds(garment_id)
        for colorway_id in colorway_ids:
            colorways.append(
                {
                    "id": colorway_id,
                    "name": BwApi.ColorwayNameGet(garment_id, colorway_id),
                }
            )
        info["colorways"] = colorways
        # info["vstitcherVersion"] = json.loads(BwApi.HostApplicationGet())["version"]

        try:
            info["style3d"] = update_embedded_json()
        except Exception as e:
            pass

        return info
    except:
        return None


def dump_info(obj):
    fname = BwApi.GarmentPathGet(BwApi.GarmentId())
    filename = os.path.basename(fname)
    dir = os.path.dirname(fname)
    jsonpath = os.path.join(dir, ".config", filename + ".json")
    try:
        with open(jsonpath, "w") as f:
            json.dump(obj, f)
    except:
        pass


def get_bp_material_ids(colorway_id, material_id):
    garment_id = BwApi.GarmentId()
    is_group = BwApi.MaterialGroup(garment_id, colorway_id, material_id)

    def ensure_mapping():
        if config.MATERIAL_MAPPING:
            return
        json_str = BwApi.GarmentInfoGetEx(garment_id, "beproduct_mapping")
        if json_str:
            mapping = json.loads(json.loads(json_str)["value"])
            if mapping and type(mapping) is dict:
                config.MATERIAL_MAPPING = mapping
                return
        config.MATERIAL_MAPPING = {}

    ensure_mapping()
    if is_group and str(material_id) in config.MATERIAL_MAPPING:
        return config.MATERIAL_MAPPING[str(material_id)]

    def to_guid(bp_string):
        guid = bp_string.replace("_", "/").replace("-", "+")
        end = len(guid) % 4
        if end == 2:
            guid += "=="
        if end == 3:
            guid += "="
        mybytes = base64.b64decode(guid)
        return str(uuid.UUID(bytes_le=mybytes))

    if not is_group:
        try:
            mat = json.loads(BwApi.MaterialGet(garment_id, colorway_id, material_id))
            keys = mat["custom"]["BeProduct"].keys()

            # case popup
            if (
                "materialId" in keys
                and mat["custom"]["BeProduct"]["materialId"]
                and "materialColorId" in keys
                and mat["custom"]["BeProduct"]["materialColorId"]
            ):
                return (
                    mat["custom"]["BeProduct"]["materialId"],
                    mat["custom"]["BeProduct"]["materialColorId"],
                )

            # case library
            plugin_ids = (
                mat["custom"]["BeProduct"]["info"]["asset_path"].rstrip("/").split("$")
            )
            bp_cw_id = to_guid(plugin_ids[-1])
            bp_mat_id = to_guid(plugin_ids[-2])
            return (bp_mat_id, bp_cw_id)

        except Exception as e:
            return None

    return None  # material is not from BP


def update_embedded_json():
    garment_id = BwApi.GarmentId()
    bp_obj = {}
    all_material_ids = []

    json_str = BwApi.GarmentInfoGetEx(garment_id, "beproduct")
    if json_str:
        bp_obj = json.loads(json.loads(json_str)["value"])
    if "styleColors" not in bp_obj:
        bp_obj["styleColors"] = []

    current_colorway_ids = BwApi.GarmentColorwayIds(garment_id)
    bp_obj["styleColors"] = [
        e for e in bp_obj["styleColors"] if e["bwColorId"] in current_colorway_ids
    ]

    for colorway_id in current_colorway_ids:
        color_name = BwApi.ColorwayNameGet(garment_id, colorway_id)
        colorway = next(
            (x for x in bp_obj["styleColors"] if x["bwColorId"] == colorway_id), None
        )
        if not colorway:
            colorway = {"bwColorId": colorway_id, "materials": []}
            bp_obj["styleColors"].append(colorway)

        colorway["colorName"] = color_name

        bw_mat_ids = BwApi.ColorwayUsedMaterialIds(garment_id, colorway_id)

        all_material_ids.extend(
            [str(x) for x in BwApi.ColorwayMaterialIds(garment_id, colorway_id)]
        )

        mat_ids_to_remove = list(
            set([e["bwMaterialId"] for e in colorway["materials"]]) - set(bw_mat_ids)
        )
        colorway["materials"] = [
            e
            for e in colorway["materials"]
            if e["bwMaterialId"] not in mat_ids_to_remove
        ]

        for mat_id in bw_mat_ids:
            bp_mat_ids = get_bp_material_ids(colorway_id, mat_id)
            if bp_mat_ids:
                bp_mat_id = bp_mat_ids[0]
                bp_mat_cw_id = bp_mat_ids[1]
                material = next(
                    (x for x in colorway["materials"] if x["bwMaterialId"] == mat_id),
                    None,
                )
                if not material:
                    material = {}
                    colorway["materials"].append(material)

                material["materialId"] = bp_mat_id
                material["materialColorId"] = bp_mat_cw_id
                material["bwMaterialId"] = mat_id

    BwApi.GarmentInfoSetEx(
        garment_id,
        "beproduct",
        json.dumps(
            {
                "show_in_techpack_html": True,
                "read_only": True,
                "caption": "beproduct",
                "value": json.dumps(bp_obj),
            }
        ),
    )

    # cleaning up
    keys_to_cleanup = [
        k for k in config.MATERIAL_MAPPING.keys() if str(k) not in all_material_ids
    ]
    for k in keys_to_cleanup:
        del config.MATERIAL_MAPPING[k]

    BwApi.GarmentInfoSetEx(
        garment_id,
        "beproduct_mapping",
        json.dumps(
            {
                "show_in_techpack_html": False,
                "read_only": True,
                "caption": "beproduct_mapping",
                "value": json.dumps(config.MATERIAL_MAPPING),
            }
        ),
    )

    return bp_obj


class UpdateJsonOnModified(BwApi.CallbackBase):
    def Run(self, garmentId, callbackId, dataString):
        try:
            update_embedded_json()
        except:
            pass


class BeProductWnd(IBwApiWndEvents):
    def __init__(self, key, path=None, width=620, height=390, title="BeProduct"):
        url = (
            ""
            if path and path.startswith("http")
            else config.BASE_URL.rstrip("/") + "/index.html"
        )
        self.wnd = Wnd(
            url + (path if path else f"#/wizard/turntable/{key}"),
            title,
            width,
            height,
            {},
        )
        self.wnd.set_delegate(self)
        self.wnd.show()

    def on_msg(self, garment_id: str, callback_id: int, data: str) -> None:
        params = json.loads(data)
        if "exit" in params and params["exit"]:
            self.wnd.close()

        if "syncCameraViews" in params:
            for cv in params["syncCameraViews"]:
                import tempfile

                tf = tempfile.NamedTemporaryFile(delete=False)
                fname = tf.name
                tf.close()
                BwApi.EnvironmentCameraViewExport(cv["name"], fname)
                cv["fileSource"] = fname
            __post_content__(
                config.BASE_URL + "api/bw/synccameraviews", params["syncCameraViews"]
            )

    def on_load(self, garment_id: str, callback_id: int, data: str) -> None:
        pass

    def on_close(self, garment_id: str, callback_id: int, data: str) -> None:
        pass

    def on_uncaught_exception(
        self, garment_id: str, callback_id: int, data: str
    ) -> None:
        print("$$$$$$$$$$$$$$$$ on_uncaught_exception $$$$$$$$$$$$$$$$")


class BeProductBW(BwApi.CallbackBase):
    def Run(self, garmentId, callbackId, dataString):

        path_components = os.path.normpath(BwApi.GarmentPathGet(garmentId)).split(
            os.sep
        )
        ind = 0
        if path_components[-1].lower().endswith(".bw"):
            ind = 1

        i = ind - 1
        filename = "%2F".join(
            map(urllib.parse.quote, path_components[: i if i != 0 else None])
        )

        # Sync style
        if callbackId == 0:
            info = get_file_info()
            dump_info(info)
            BwApi.GarmentClose(garmentId, 0)
            if not config.USERID and not config.SYNC_STANDALONE:
                __get_content__(config.BASE_URL + "api/bw/sync-back/" + config.USERID)
            else:
                __post_content__(config.BASE_URL + "api/sync/sync?f=" + filename, info)

        # Refresh colors
        if callbackId == 1:
            if BeProduct3DDevelopmentAssets.colors:
                while BeProduct3DDevelopmentAssets.colors:
                    BwApi.ColorLibraryRemove(
                        garmentId, BeProduct3DDevelopmentAssets.colors.pop(0)
                    )

                colors_json = __get_content__(
                    config.BASE_URL
                    + "api/bw/colors?nocache=true&api-version=2.0&f="
                    + filename
                )
                for col in json.loads(colors_json):
                    BeProduct3DDevelopmentAssets.colors = BwApi.ColorLibraryCreate(
                        garmentId, json.dumps(col)
                    )

        if callbackId == 2:
            BwApi.GarmentClose(garmentId, 0)
            __get_content__(
                config.BASE_URL + "api/sync/offload/turntable?f=" + filename
            )

        if callbackId == 4:
            update_embedded_json()

        if callbackId == 3:
            info = get_file_info()
            dump_info(info)
            if info is not None:

                infoFromBw = None
                json_str = BwApi.GarmentInfoGetEx(garmentId, "beproduct_version")
                if json_str:
                    version = json.loads(json.loads(json_str)["value"])
                    if version and type(version) is dict:
                        header_id = version.get("headerId", None)
                        if header_id:
                            infoFromBw = f"&headerId={header_id}"

                BwApi.GarmentClose(garmentId, 0)
                url = (
                    (
                        "api/sync/wizardanyfilelocation/turntable?f="
                        + filename
                        + infoFromBw
                    )
                    if infoFromBw
                    else ("api/sync/wizard/turntable?f=" + filename)
                )

                key = json.loads(
                    __post_content__(
                        config.BASE_URL + url,
                        info,
                    )
                )["key"]

                self.wnd = BeProductWnd(
                    key, width=1020, height=610, title="BEPRODUCT SYNC"
                )

        if callbackId == 5:
            settings = get_local_settings()
            __post_content__(config.BASE_URL + "api/sync/wizard/envsettings", settings)
            # self.wnd = BeProductWnd(None, "http://localhost:3000/#/settings")
            self.wnd = BeProductWnd(None, "#/settings", title="BEPRODUCT SETTINGS")

        return 0
