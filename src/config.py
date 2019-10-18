import os
import sys
import ssl

sys.path.append(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), '../venv/lib/python3.7/site-packages'))

DEBUG = False
BASE_URL = 'http://127.0.0.1:55862/'

BASE_URL = os.environ.get('BW_ASSET_LIB_URL') or BASE_URL

# LIBRARY_INFO_URL = os.path.join(BASE_URL, "library.json")
# COLLECTIONS_URL = os.path.join(BASE_URL, "collections.json")
# ASSETS_URL = os.path.join(BASE_URL, "assets.json")
BASE_ASSETS_PATH = os.path.join(BASE_URL, "assets/")

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
