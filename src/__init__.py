import config
from wrappers import bwapi_wrapper
import urllib.request
import urllib.parse
import json
import BwApi

from .remote_asset_library import RemoteAssetLibrary
from .beproduct_bw import BeProductBW
from .beproduct_dev_app import BeProduct3DDevelopmentAssets


def __get_content__(url):
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)
    return response.read().decode('utf-8')


class Main(bwapi_wrapper.IBwApiEvents):
    def __init__(self):
        super().__init__()
        self.libraries = []

        libs = json.loads(__get_content__(
        urllib.parse.urljoin(config.BASE_URL, 'api/bw/libraries/' + config.USERID)))
        for lib in libs:
            self.libraries.append(RemoteAssetLibrary(lib))

    def on_post_initialize(self):
        for lib in self.libraries:
            lib.initialize()

def debug():
    if config.DEBUG:
        # import sys
        # sys.path.append("C:\Program Files\JetBrains\PyCharm 2018.1.3\debug-eggs\pycharm-debug.egg")
        # sys.path.append("/Applications/PyCharm.app/Contents/debug-eggs/pycharm-debug.egg")
        # sys.path.append("/Applications/LiClipse.app/Contents/Eclipse/plugins/org.python.pydev_6.2.0.201711281546/pysrc")

        try:
            # import pydevd
            # pydevd.settrace('localhost', port=9095, stdoutToServer=True, stderrToServer=True)
            # pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)
            import ptvsd
            ptvsd.enable_attach(address=('0.0.0.0', 3000), redirect_output=True)
            # Pause the program until a remote debugger is attached
            ptvsd.wait_for_attach()
            breakpoint()
        except:
            pass


def BwApiPluginInit() -> int:
    BwApi.IdentifierSet('BeProduct Sync')
    if config.SYNC_CLIENT_RUNNING:
        BwApi.MenuFunctionAdd('Sync Color Libraries', sync_callback, 1)
        BwApi.MenuFunctionAdd('Sync From Local Folder', sync_callback, 0)
        BwApi.MenuFunctionAdd('Sync To BeProduct Cloud', sync_callback, 3)
        BwApi.MenuFunctionReloadAdd()
        # register to file -> open event
        BwApi.EventRegister(fileopenthandler, 1, BwApi.BW_API_EVENT_GARMENT_OPEN)
    return bw.init()

# invoke debug if enabled
debug()

if config.SYNC_CLIENT_RUNNING:
    sync_callback = BeProductBW()
    fileopenthandler = BeProduct3DDevelopmentAssets()
    bw = bwapi_wrapper.BwApiWrapper()
    bw.set_delegate(Main())
