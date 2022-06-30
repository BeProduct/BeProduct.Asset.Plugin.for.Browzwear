import BwApi
import json
import config
import shutil
import copy
import math
import os
import shutil
import uuid
import re
import time
from datetime import datetime as dt
from distutils.dir_util import copy_tree
import shlex
import subprocess
import urllib.request
import urllib.parse
import urllib

render_data_normal = {
    "render": {"normal": {"outline": False, "background": "transparent"}},
    "captures": [],
}

render_data_ray_trace = {
    "render": {"ray_trace": {"cycles": 250, "background": "transparent"}},
    "captures": [],
}

LOAD_SNAPSHOT_JSON = {
    "load_snapshot_option": "saved_colorway_and_avatar",
    "sync_snapshot": False,
}


def __get_content__(url):
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)
    return response.read().decode("utf-8")


def execute_ray_trace_cmd(garment_id, render_json):
    """Run external process"""

    cmd = BwApi.RenderRayTraceCMD(garment_id, render_json)
    cmd_with_args = [arg.strip('"') for arg in shlex.split(cmd, posix=False)]
    process = subprocess.Popen(cmd_with_args)
    # (output, err) = process.communicate()
    # This makes the wait possible
    process.wait()


def render_image(
    output_path, pose, include_avatar, width, height, garment_id=None, ray_trace=False
):
    """Render single image"""

    garment_id = BwApi.GarmentId() if not garment_id else garment_id

    # copy render data
    if ray_trace:
        render = copy.deepcopy(render_data_ray_trace)
    else:
        render = copy.deepcopy(render_data_normal)

    capture = {}
    # get camera object by pos name
    capture["camera"] = json.loads(BwApi.EnvironmentCameraViewGet(garment_id, pose))
    # add output pate
    capture["path"] = output_path

    # add to the render object
    render["captures"].append(capture)

    render["include_avatar"] = include_avatar
    render["width"] = width
    render["height"] = height

    if ray_trace:
        execute_ray_trace_cmd(garment_id, json.dumps(render))
    else:
        BwApi.RenderImage(garment_id, json.dumps(render))


def render_turntable_vs(
    output_folder,
    start_pose,
    angles,
    include_avatar,
    width,
    height,
    garment_id=None,
    ray_trace=False,
):
    """Renders turntable"""

    garment_id = BwApi.GarmentId() if not garment_id else garment_id

    # copy render data
    if ray_trace:
        render = copy.deepcopy(render_data_ray_trace)
    else:
        render = copy.deepcopy(render_data_normal)

    # get turntable cameras according to starting position and number of angles
    cameras = BwApi.EnvironmentTurntableCameraPositionsGet(
        BwApi.EnvironmentCameraViewGet(garment_id, start_pose), angles
    )
    cameras = json.loads(cameras)

    current_angle = 1
    for camera in cameras:
        capture = {}
        # get camera object by pos name
        capture["camera"] = camera
        # add output pate
        capture["path"] = "{}/{}.png".format(output_folder, current_angle)

        # add capture object to the captures list
        render["captures"].append(capture)
        current_angle += 1

    render["include_avatar"] = include_avatar
    render["width"] = width
    render["height"] = height

    if ray_trace:
        execute_ray_trace_cmd(garment_id, json.dumps(render))
    else:
        BwApi.RenderImage(garment_id, json.dumps(render))


def get_snapshot_ids(garment_id=None):
    """List garment's snapshot ids"""

    garment_id = BwApi.GarmentId() if not garment_id else garment_id

    # save snapshot
    return BwApi.GarmentSnapshotIdsEx(garment_id)


def save_snapshot(name, garment_id=None):
    """Save current snapshot"""

    garment_id = BwApi.GarmentId() if not garment_id else garment_id

    # save snapshot
    return BwApi.SnapshotSave(garment_id, name)


def load_snapshot(snapshot_id, garment_id=None, mode: str = None):
    """Load snapshot by name"""

    garment_id = BwApi.GarmentId() if not garment_id else garment_id

    load_json = copy.deepcopy(LOAD_SNAPSHOT_JSON)
    if mode:
        load_json["load_snapshot_option"] = mode
    # save snapshot
    # To check against old versions
    # TODO REMOVE IN FUTURE
    all_ids = get_snapshot_ids(garment_id)
    if snapshot_id in all_ids:
        BwApi.SnapshotLoadEx(garment_id, json.dumps(load_json), snapshot_id)
        return
    else:
        for sn_id in all_ids:
            info = json.loads(BwApi.SnapshotInfoGet(garment_id, sn_id))
            if "name" in info and info["name"] == snapshot_id:
                BwApi.SnapshotLoadEx(garment_id, json.dumps(load_json), sn_id)
                return

    raise Exception("Snapshot is not found")


def render(params):
    """Entry point"""

    # defaults
    number_of_images = 8
    colorways_to_generate = ["-1"]
    snapshot_id = None
    display_avatar = False
    enable_ray_trace = False

    turntable_id = uuid.uuid4()

    render_turntable = True
    render_glb = False

    def set_light(name="Ambient.hdr", exposure=0.0, rotation_angle=0.0):
        """Setting light based on params"""

        BwApi.EnvironmentLightCurrentSet(name)
        BwApi.EnvironmentLightInfoSet(
            name, json.dumps({"exposure": exposure, "rotation_angle": rotation_angle})
        )
        return True

    class CamView:
        """Applying camera view before rendering"""

        def __init__(self, path, name=None):
            self.name = name
            self.path = path

        def __enter__(self):
            if self.path and self.name not in ["GarmentFront"]:
                # TODO: Support camera views
                pass
                # BwApi.EnvironmentCameraViewImport(self.path)
            return self

        def __exit__(self, type, value, traceback):
            # Camera view cleanup here
            # not available atm
            pass

    try:

        bpsync_settings = __get_content__(f"{config.BASE_URL}api/settings/getsettings")
        tmp_path = json.loads(bpsync_settings)["tempDirectory"]

        work_path = os.path.join(tmp_path, str(turntable_id))
        base_ttpath = os.path.join(work_path, "turntable", str(turntable_id))
        origin_ttpath = os.path.join(base_ttpath, "storage")
        os.makedirs(origin_ttpath, exist_ok=True)
        bw_file = os.path.join(
            origin_ttpath,
            re.sub(r"[^a-zA-Z0-9_ \-\.]", "-", os.path.basename(params["filePath"])),
        )
        shutil.copyfile(params["filePath"], bw_file)
        # params["filePath"] = bw_file

        render_glb = "glb" in params and params["glb"] in ("true", True)
        if not any([render_turntable, render_glb]):
            raise Exception("not png or glb")

        display_avatar = str(params["includeAvatar"]).lower() == "true"
        colorways_to_generate = (
            params["colorways"].split(",")
            if ("colorways" in params and params["colorways"])
            else ["-1"]
        )
        number_of_images = int(params["numberOfImages"])
        enable_ray_trace = (
            False
            if "enableRayTrace" not in params
            else str(params["enableRayTrace"]).lower() == "true"
        )
        snapshot_id = params["snapshot"]

        common_metadata = {
            # "Origin": input_files[params["fileBW"]],
            # "FileSource": input_files[params["fileBW"]],
            "FileLength": os.path.getsize(bw_file),
        }

        # opening garment
        BwApi.GarmentOpen(bw_file)
        garment_id = BwApi.GarmentId()

        colorways_to_generate = [int(c) for c in colorways_to_generate]
        colorways = (
            BwApi.GarmentColorwayIds(garment_id)
            if -1 in colorways_to_generate
            else colorways_to_generate
        )
        for colorway in colorways:

            if colorway == -1:
                pass

            matched_color = None
            if "colorwaysWithParameters" in params:
                all_cols = params[
                    "colorwaysWithParameters"
                ]  # json.loads(params["colorwaysWithParameters"])
                for col in all_cols:
                    if str(col["id"]) == str(colorway):
                        matched_color = col

            if matched_color:
                _ = (
                    set_light(
                        name=matched_color["name"],
                        exposure=float(matched_color["exposure"]),
                        rotation_angle=float(matched_color["rotationAngle"]),
                    )
                    or set_light()
                )
                if matched_color.get("action", "") == "SKIP":
                    continue
            else:
                set_light()

            BwApi.ColorwayCurrentSet(garment_id, colorway)
            load_snapshot(
                snapshot_id if snapshot_id else get_snapshot_ids()[0],
                mode="current_colorway_and_avatar",
            )

            unescaped_colorway_name = BwApi.ColorwayNameGet(garment_id, colorway)
            colorway_name = re.sub(r"[^a-zA-Z0-9_ \-\.]", "-", unescaped_colorway_name)

            ### turntable
            if render_turntable:
                previews_path = os.path.join(base_ttpath, "preview")
                render_path = os.path.join(previews_path, colorway_name)
                os.makedirs(render_path, exist_ok=True)

                # find light and cam view
                view_name = (
                    params["cameraViewTurntable"]["name"]
                    if "cameraViewTurntable" in params
                    else "GarmentFront"
                )

                render_turntable_vs(
                    render_path,
                    view_name,
                    number_of_images,
                    display_avatar,
                    1951,
                    1950,
                    ray_trace=enable_ray_trace,
                )

                # result check
                onlyfiles = [
                    f
                    for f in os.listdir(render_path)
                    if os.path.isfile(os.path.join(render_path, f))
                ]
                if not onlyfiles:
                    raise Exception("No files were found after render")

                for f in onlyfiles:
                    fname, ext = os.path.splitext(f)

                    dest_path = os.path.join(
                        previews_path,
                        f"{str(fname).zfill(4)}_{colorway_name.lower()}{ext}",
                    )
                    shutil.move(os.path.join(render_path, f), dest_path)

                    preview_obj = copy.deepcopy(common_metadata)
                    preview_obj["Metadata"] = {
                        "turntable": "generic",
                        "colorway": colorway_name,
                    }

                    try:
                        index = int(fname)
                        if index == 1:
                            preview_obj["Metadata"]["side"] = "Front"
                        if number_of_images > 3:
                            if index == math.ceil(number_of_images / 4) + 1:
                                preview_obj["Metadata"]["side"] = "Side"
                            if index == math.ceil(number_of_images / 2) + 1:
                                preview_obj["Metadata"]["side"] = "Back"
                    finally:
                        pass

                    with open(
                        os.path.join(previews_path, dest_path + ".bpmetadata"), "w"
                    ) as f:
                        json.dump(preview_obj, f)

                # additional views
                for key in params:
                    if key.startswith("cameraViewAdditional"):
                        # with CamView(
                        #     os.path.join(work_path, "input", params["file" + key])
                        #     if "file" + key in params and params["file" + key]
                        #     else None
                        # ):
                        render_image(
                            os.path.join(render_path, params[key].lower() + ".png"),
                            params[key],
                            display_avatar,
                            1951,
                            1950,
                            ray_trace=enable_ray_trace,
                        )

                onlyfiles = [
                    f
                    for f in os.listdir(render_path)
                    if os.path.isfile(os.path.join(render_path, f))
                ]
                if len(onlyfiles):
                    for f in onlyfiles:
                        fname, ext = os.path.splitext(f)

                        dest_path = os.path.join(
                            previews_path,
                            f"cv_{fname}_{colorway_name.lower()}{ext}",
                        )
                        shutil.move(os.path.join(render_path, f), dest_path)

                        preview_obj = copy.deepcopy(common_metadata)
                        preview_obj["Metadata"] = {
                            "turntable": "generic",
                            "colorway": colorway_name,
                        }
                        with open(
                            os.path.join(previews_path, dest_path + ".bpmetadata"), "w"
                        ) as f:
                            json.dump(preview_obj, f)

                shutil.rmtree(render_path)

            ### glb
            if render_glb:
                glb_id = uuid.uuid4()
                base_glbpath = os.path.join(work_path, "glb", str(glb_id))
                previews_path = os.path.join(base_glbpath, "preview")
                origin_path = os.path.join(base_glbpath, "storage")

                os.makedirs(previews_path, exist_ok=True)
                os.makedirs(origin_path, exist_ok=True)

                data = {
                    "3d_format": "gltf",
                    "up_axis": "y",
                    "scale": 1,
                    "use_pattern_pieces_names": True,
                    "layout": {"layout_type": "layout_uv", "piece": "per_piece"},
                    "export_inside": True,
                    "export_thickness": True,
                    "include_avatar": display_avatar,
                    "alpha_mode": "mask",
                    "pbr_model": "specular_glossiness",
                    # "pbr_model": "metallic_roughness",
                }

                data["path"] = os.path.join(
                    previews_path, f"{colorway_name.lower()}.glb"
                )
                BwApi.RenderExport3DObject(garment_id, json.dumps(data))

                preview_obj = copy.deepcopy(common_metadata)
                preview_obj["Metadata"] = {
                    "turntable": "glb",
                    "colorway": colorway_name,
                }
                with open(
                    os.path.join(previews_path, data["path"] + ".bpmetadata"), "w"
                ) as f:
                    json.dump(preview_obj, f)

                shutil.copy(
                    data["path"],
                    os.path.join(origin_path, f"{colorway_name.lower()}.glb"),
                )

        BwApi.GarmentClose(garment_id, True)
        return work_path, None

    except Exception as e:
        import traceback

        return None, traceback.format_exc()
