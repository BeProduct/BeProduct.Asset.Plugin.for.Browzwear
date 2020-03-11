import os
import sys
import ssl

sys.path.append(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'lib'))
sys.path.append(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), '../venv/lib/python3.7/site-packages'))

DEBUG = False 


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

BASE_URL = "https://local.beproduct.org:55862/"
BASE_ASSETS_PATH =  BASE_URL.rstrip('/') + '/assets/'
USERID=""
