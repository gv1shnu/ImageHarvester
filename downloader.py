from tqdm import tqdm
import requests
import time
import os
import urllib.error
import urllib.request


class Downloader:
    def __init__(self):
        self.cnt = 0

    def download_all(self, lis, path):
        for img in lis:
            self.download(img, path)
        self.restart()

    def download(self, img_url, path):
        # download the body of response by chunk, not immediately
        try:
            response = requests.get(img_url, stream=True)
        except requests.exceptions.ConnectionError:
            time.sleep(10)
            response = requests.get(img_url, stream=True)

        ext = img_url[-3:]

        # get the total file size
        file_size = int(response.headers.get("Content-Length", 0))
        self.cnt += 1
        # get the file name
        filename = os.path.join(path, f'image-{self.cnt}.{ext}')

        # progress bar, changing the unit to bytes instead of iteration (default by tqdm)
        progress = tqdm(response.iter_content(1024), f"Downloading {filename}", total=file_size, unit="B",
                        unit_scale=True,
                        unit_divisor=1024)
        with open(filename, "wb") as f:
            for data in progress:
                # write data read to the file
                f.write(data)
                # update the progress bar manually
                progress.update(len(data))

    def restart(self):
        self.cnt = 0


def write(src, dest):
    try:
        urllib.request.urlretrieve(url=src, filename=dest)
    except urllib.error.HTTPError:
        print("HTTPError at {}".format(src))
