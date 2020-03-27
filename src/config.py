import os
import sys
import ssl

sys.path.append(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), '../venv/lib/python3.7/site-packages'))

DEBUG = False


# LIBRARY_INFO_URL = os.path.join(BASE_URL, "library.json")
# COLLECTIONS_URL = os.path.join(BASE_URL, "collections.json")
# ASSETS_URL = os.path.join(BASE_URL, "assets.json")

SSL_CONTEXT = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
SSL_CONTEXT.verify_mode = ssl.CERT_OPTIONAL
if sys.platform == 'win32':
    SSL_CONTEXT.load_default_certs()
elif sys.platform == 'darwin':
    import tempfile

    rootcert_path = os.path.join(tempfile.gettempdir(), 'Bw/rootcert.pem')
    if os.path.isfile(rootcert_path):
        SSL_CONTEXT.load_verify_locations(rootcert_path)
    else:
        rootcert_path = os.path.join(
            tempfile.gettempdir(), 'Browzwear/rootcert.pem')
        print("loading root cert")
        SSL_CONTEXT.load_verify_locations(rootcert_path)

import json
import urllib
import urllib.request

# sync server client
try:
    if urllib.request.urlopen("http://127.0.0.1:55862/api/settings/getsettings/").getcode() == 200:
        SYNC_CLIENT_RUNNING = True
    else:    
        SYNC_CLIENT_RUNNING = False
except Exception as exc:
    SYNC_CLIENT_RUNNING = False
    ERROR = exc

if SYNC_CLIENT_RUNNING:
    
    response = urllib.request.urlopen(
        "http://127.0.0.1:55862/api/settings/getsettings/")
    client_config = json.loads(response.read().decode('utf-8'))


    if not client_config["syncServerAddress"]:
        BASE_URL = "http://127.0.0.1:55862/"
        USERID = ""

    else:
        BASE_URL = client_config["syncServerAddress"].rstrip('/') + '/'
        if not client_config["currentUserId"]:
            USERID = ""
        else:
            USERID = client_config["currentUserId"].rstrip('/') + '/'
    
    BASE_ASSETS_PATH =  BASE_URL.rstrip('/') + '/assets/'



# standalone client
if not  SYNC_CLIENT_RUNNING:
    try:
        if urllib.request.urlopen("https://local.beproduct.org:55862/api/settings/getsettings/").getcode() == 200:
            SYNC_CLIENT_RUNNING = True
            BASE_URL = "https://local.beproduct.org:55862/"
            USERID = ""
            BASE_ASSETS_PATH =  BASE_URL.rstrip('/') + '/assets/'

        else:    
            SYNC_CLIENT_RUNNING = False
    except Exception as exc:
        SYNC_CLIENT_RUNNING = False
        ERROR = exc
