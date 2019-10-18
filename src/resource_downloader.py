from wrappers.bwapi_wrapper import BwApiWrapper
from concurrent.futures import ThreadPoolExecutor
import tempfile
import config
import urllib.request
import urllib.parse
import json
import os
import BwApi
import sys
import typing

class ResourceDownloader(BwApi.CallbackBase):
    def __init__(self):
        super().__init__()
        self.download_pool = ThreadPoolExecutor(max_workers=4)
        self.callbacks = {}

    # BwApi.CallbackBase implementation
    def Run(self, garment_id: str, callback_id: int, data: str) -> int:
        dataJson = json.loads(data)

        print('receive extract callback with data {}'.format(dataJson))
        required_fields = ['type', 'resource_id', 'url', 'path', 'status', 'response']
        for field in required_fields:
            if field not in dataJson:
                return 0

        dataJson['path'] = dataJson['response']['destination']
        dataJson['status'] = dataJson['response']['valid']
        del dataJson['response']

        self.__notify_callback(dataJson)
        return 1

    def download(self, resource_id: str, url: str, callback: typing.Callable[[object], None]):
        if resource_id in self.callbacks:
            return  # already downloading from this url

        self.callbacks[resource_id] = callback
        self.download_pool.submit(self.__thread_download_resource, resource_id, url)

    def __thread_download_resource(self, resource_id: str, url: str):
        dataJson = {
            'type': 'download',
            'resource_id': resource_id,
            'url': url,
            'path': '',
            'status': False,
            'description': ''
        }

        try:
            with urllib.request.urlopen(url, context=config.SSL_CONTEXT) as f:
                downloaded_file_path = '{}.bwr'.format(tempfile.mktemp())
                with open(downloaded_file_path, "w+b") as fp:
                    fp.write(f.read())

                dataJson['status'] = True
                dataJson['path'] = downloaded_file_path
        except urllib.error.HTTPError as e:
            dataJson.description = str(e.reason)
            print('HTTPError exception {}'.format(dataJson['description']))
        except urllib.error.URLError as e:
            dataJson.description = str(e.reason)
            print('HTTPError exception {}'.format(dataJson['description']))
        except Exception as e:
            dataJson['description'] = str(e)
        finally:
            BwApiWrapper.invoke_on_main_thread(self.__extract_resource, dataJson)

    def __extract_resource(self, data: object):
        required_fields = ['type', 'resource_id', 'url', 'path', 'status']
        has_all_required_fields = True
        for field in required_fields:
            if field not in data:
                has_all_required_fields = False
                break;

        # extract the resource if downloaded successfuly
        if has_all_required_fields and data['status'] == True:
            temp_dir = tempfile.mkdtemp()
            BwApi.ExtractPackage(data['path'], temp_dir, self, 0, json.dumps(data))
        else:
            self.__notify_callback(data)

    def __notify_callback(self, data: object):
        if data['resource_id'] not in self.callbacks:
            return

        self.callbacks[data['resource_id']](data)
        del self.callbacks[data['resource_id']]
