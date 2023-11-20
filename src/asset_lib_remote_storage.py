import urllib.request
import urllib.parse
import urllib
import ssl
import config


def __get_content__(url):
    response = urllib.request.urlopen(url, context=config.SSL_CONTEXT)
    return response.read().decode("utf-8")


class AssetLibRemoteStorage:
    def __init__(self, library_json):
        self.base_url = config.BASE_URL
        self.library_json = library_json

    def get_library_info(self):
        # library_info_url = urllib.parse.urljoin(self.base_url, self.tag_name + 'library.json')
        # return __get_content__(library_info_url)
        return self.library_json

    def get_collections(self):
        collection_url = urllib.parse.urljoin(
            self.base_url,
            urllib.parse.quote(
                "api/bw/collections/"
                + config.USERID
                + self.library_json["metadata"]["tag"]
            ),
        )
        content = __get_content__(collection_url)
        return content

    def get_assets(self):
        assets_url = urllib.parse.urljoin(
            self.base_url,
            urllib.parse.quote(
                "api/bw/assets/" + config.USERID + self.library_json["metadata"]["tag"]
            ),
        )
        return __get_content__(assets_url)

    def get_base_assets_path(self, live=False):
        if live:
            return urllib.parse.urljoin(self.base_url, "api/bw/live-assets/")
        else:
            return urllib.parse.urljoin(
                self.base_url,
                "assets/" + self.library_json["metadata"]["company"] + "/",
            )

    def get_base_path(self):
        return self.base_url
