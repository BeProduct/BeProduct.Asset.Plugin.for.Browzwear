from wrappers.wnd import Wnd, IBwApiWndEvents
import BwApi
import os
import os.path
import tempfile


from urllib.request import urlopen
from urllib.parse import urlparse, urlunparse, quote
import json
import ssl
import config


context = ssl._create_unverified_context()

tmp_dir = None


def download_remote_resource(dest_path: str, source_url: str) -> None:
    def url_fix(url):
        parts = urlparse(url)
        return urlunparse(parts._replace(path=quote(parts.path)))

    # response = urlopen(url_fix(source_url), context=context)
    response = urlopen(source_url, context=context)
    text = response.read()

    if not os.path.exists(os.path.dirname(dest_path)):
        os.makedirs(os.path.dirname(dest_path))

    output = open(dest_path, "wb")
    output.write(text)
    output.close()


def add_material_from_url(material_url):
    garment_id = BwApi.GarmentId()
    if garment_id:
        with tempfile.TemporaryDirectory() as tmp_dir:
            fname = os.path.join(tmp_dir, os.path.basename(urlparse(material_url).path))
            download_remote_resource(fname, material_url)
            return BwApi.MaterialImport(
                garment_id, BwApi.ColorwayCurrentGet(garment_id), fname
            )

    return None


def upsert_color_palette(palette):
    garment_id = BwApi.GarmentId()
    BwApi.ColorLibraryCreate(garment_id, json.dumps(palette))


def get_access_token() -> str:
    url = "https://local.beproduct.org:55862/api/bw/token"

    response = urlopen(url, context=context)
    t = json.loads(response.read().decode("utf-8"))
    return (t or {}).get("accessToken", None)


def get_bw_file_info() -> str:
    ind = 0
    path_components = os.path.normpath(BwApi.GarmentPathGet(BwApi.GarmentId())).split(
        os.sep
    )

    if path_components[-1].lower().endswith(".bw"):
        ind = 1

    i = ind - 1
    filename = "%2F".join(map(quote, path_components[: i if i != 0 else None]))

    infoFromBw = None
    json_str = BwApi.GarmentInfoGetEx(BwApi.GarmentId(), "beproduct_version")
    if json_str:
        version = json.loads(json.loads(json_str)["value"])
        if version and type(version) is dict:
            header_id = version.get("inputjson", {}).get("headerId", None)
            if header_id:
                infoFromBw = f"&headerId={header_id}"

    url = (
        "https://local.beproduct.org:55862/api/bw/file-info?f=" + filename + infoFromBw
    )

    response = urlopen(url, context=context)
    return json.loads(response.read().decode("utf-8"))


class BeProductWnd(IBwApiWndEvents):
    def __init__(self) -> None:
        #        self.swatchbookApi = swatchbookAPI.SwatchbookApi()
        self.wnd = None

    # IBwApiWndEvents implementation
    def on_load(self, garment_id: str, callback_id: int, data: str) -> None:
        pass
        # BwApi.WndMessageBox(json.dumps(get_bw_file_info()), BwApi.BW_API_MB_OK)

        # self.wnd.send_message({
        #     'type': 'init',
        #     'file_info': get_bw_file_info()
        # })

    def on_close(self, garment_id: str, callback_id: int, data: str) -> None:
        self.wnd = None

    def on_msg(self, garment_id: str, callback_id: int, data: str) -> None:
        def ensure_mapping():
            if config.MATERIAL_MAPPING is not None:
                return
            json_str = BwApi.GarmentInfoGetEx(garment_id, "beproduct_mapping")
            if json_str:
                mapping = json.loads(json.loads(json_str)["value"])
                if mapping and type(mapping) is dict:
                    config.MATERIAL_MAPPING = mapping
                    return
            config.MATERIAL_MAPPING = {}

        params = json.loads(data)
        if params["action"] == "material_add":
            garment_id = BwApi.GarmentId()
            colorway_id = BwApi.ColorwayCurrentGet(garment_id)

            msg = "Material was added"
            success = True

            def inject_bp(id, mat):
                mat["custom"] = mat.get("custom", {})
                mat["custom"]["BeProduct"] = mat["custom"].get("BeProduct", {})
                mat["custom"]["BeProduct"]["materialId"] = params["materialId"]
                mat["custom"]["BeProduct"]["materialColorId"] = params[
                    "materialColorId"
                ]

            try:
                mat_id = add_material_from_url(params["url"])[0]
                ensure_mapping()
                config.MATERIAL_MAPPING[str(mat_id)] = (
                    params["materialId"],
                    params["materialColorId"],
                )

                is_group = BwApi.MaterialGroup(garment_id, colorway_id, mat_id)

                if is_group:
                    pass
                else:
                    mat = json.loads(BwApi.MaterialGet(garment_id, colorway_id, mat_id))
                    inject_bp(mat_id, mat)
                    BwApi.MaterialUpdate(
                        garment_id, colorway_id, mat_id, json.dumps(mat)
                    )

            except Exception as e:
                msg = str(e)
                success = False

            self.wnd.send_message({"material_added": msg, "success": success})

        if params["action"] == "colors_add":
            upsert_color_palette(json.loads(params["palette"]))
            self.wnd.send_message(
                {"palette_added": str(json.loads(params["palette"])["name"])}
            )

        if params["action"] == "init":
            self.wnd.send_message({"type": "init", "file_info": get_bw_file_info()})

        if params["action"] == "token":
            self.wnd.send_message({"type": "token", "accessToken": get_access_token()})

    def on_uncaught_exception(
        self, garment_id: str, callback_id: int, data: str
    ) -> None:
        print("$$$$$$$$$$$$$$$$ on_uncaught_exception $$$$$$$$$$$$$$$$")

    def show_window(self, data: object):
        if self.wnd:
            self.wnd.focus()
            return

        if "url" in data:
            url = data["url"]
        if "title" in data:
            title = data["title"]
        if "width" in data:
            width = data["width"]
        if "height" in data:
            height = data["height"]
        if "style" in data:
            style = data["style"]

        self.wnd = Wnd(url, title, width, height, style)
        self.wnd.set_delegate(self)
        self.wnd.show()
