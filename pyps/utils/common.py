# -*- coding: utf-8 -*- 
# @Time     : 2019-09-12 16:20
# @Author   : binger
import requests


def url_with_token(url):
    return url


def download_by_url(url, with_token=False):
    import re
    res = re.match("https?://", url)
    if res:
        file_or_url = url_with_token(url) if with_token else url
        response = requests.get(file_or_url)
        return response.content
    else:
        raise ValueError("Url is not legal: {}".format(url))


def read_image(file_or_url, with_token=False):
    from PIL import ImageFile, Image
    if isinstance(file_or_url, ImageFile.ImageFile):
        return file_or_url

    try:
        from io import BytesIO
        data = download_by_url(file_or_url, with_token)
        handler = BytesIO(data)
    except ValueError:
        handler = file_or_url
    except:
        return file_or_url

    return Image.open(handler)


def load_object(file_or_url, with_token=False, object_cb=None):
    try:
        from io import BytesIO
        data = download_by_url(file_or_url, with_token)
        handler = BytesIO(data)
    except ValueError:
        handler = file_or_url

    if object_cb:
        return object_cb(handler)
    return handler
if __name__ == "__main__":
    pass
