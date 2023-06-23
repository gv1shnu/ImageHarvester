import os
import concurrent.futures
from extractor import LinkExtractor, ImageExtractor
from downloader import Downloader


class ImageHarvester:
    def __init__(self, keywords):
        self.q = keywords
        self.folder = os.path.join('data', self.q)
        self.link_extractor = LinkExtractor()
        self.img_extractor = ImageExtractor()
        self.downloader = Downloader()
        self.curr_list = [
            # {'param': '', 'f': 'websites', 'func': self.img_extractor.get_images_from_webpage},
            {'param': 'pinterest', 'f': 'pinterest', 'func': self.img_extractor.get_images_from_pinterest_page},
            # {'param': 'reddit', 'f': 'reddit', 'func': self.img_extractor.get_images_from_reddit_page}
        ]

    def get_images(self, f, param, func):
        base = os.path.join(self.folder, f)
        refs = self.link_extractor.get_all_website_urls(self.q, param=param)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            ans = executor.map(func, refs)
        results = list(ans)
        for dic in results:
            for key, lis in dic.items():
                path = os.path.join(base, key)
                os.makedirs(path, exist_ok=True)
                self.downloader.download_all(lis, path)

    def get_all_images(self):
        for curr in self.curr_list:
            self.get_images(curr['f'], curr['param'], curr['func'])


if __name__ == '__main__':
    print("Welcome to Image Harvester\n")
    ih = ImageHarvester(input("Input your search keywords: "))
    ih.get_all_images()
