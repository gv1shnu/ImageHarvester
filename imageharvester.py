import os
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse
from urllib.parse import urljoin
import concurrent.futures
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager


class Extractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless --no-sandbox --disable-dev-shm-usage --disable-gpu")
        self.driver_service = webdriver.chrome.service.Service(ChromeDriverManager().install())

    def check(self, plink, param):
        return str(plink).find(param) >= 0

    def get_all_website_urls(self, q):
        return self.get_website_urls(q) + self.get_g_website_urls(q)

    def get_website_urls(self, q):
        param = ''
        driver = webdriver.Chrome(service=self.driver_service, options=self.chrome_options)
        key = "+".join(q.split(' '))
        driver.get(f'https://www.google.co.in/search?q={key}+{param}')
        _refs = []
        for page_num in range(1, 9):
            try:
                # Navigating to next page
                links = driver.find_elements(By.CLASS_NAME, 'yuRUbf')
                for link in links:
                    plink = link.find_element(By.TAG_NAME, 'a').get_attribute("href")
                    if self.check(plink, param):
                        _refs.append(str(plink))
                _next = driver.find_element(By.XPATH, '//*[@id="pnnext"]')
                _next.click()
                time.sleep(1)
                break  # remove this later
            except NoSuchElementException:
                # Last page reached
                break
        driver.close()
        return _refs

    def get_images_from_webpage(self, url):
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")
        urls = []
        imgs = soup.find_all('img')
        for img in imgs:
            img_url = img.attrs.get('src')
            if not img_url:
                # if img does not contain src attribute, just skip
                continue
            # make the URL absolute by joining domain with the URL that is just extracted
            img_url = urljoin(url, img_url)
            # remove URLs like '/hsts-pixel.gif?c=3.2.5'
            try:
                pos = img_url.index("?")
                img_url = img_url[:pos]
            except ValueError:
                pass
            urls.append(img_url)
        x = get_domain(url)
        return {x: urls}

    def get_g_website_urls(self, q):
        """
        Get URLs from google images
        """
        driver = webdriver.Chrome(options=self.chrome_options, service=self.driver_service)
        driver.get('https://www.google.com/')
        searchBox = driver.find_element(By.NAME, 'q')
        searchBox.send_keys(q)
        searchBox.send_keys(Keys.ENTER)
        elem = driver.find_element(By.LINK_TEXT, 'Images')
        elem.get_attribute('href')
        elem.click()

        # Scroll to load images
        value = 0
        for _i in range(4):
            wait = 400
            driver.execute_script("scrollBy(" + str(value) + "," + str(wait) + ");")
            value += wait
            time.sleep(2)

        elem1 = driver.find_element(By.ID, 'islrg')
        children_elems = elem1.find_elements(By.CSS_SELECTOR, '.islrc > div')
        sub = []
        for _elem in children_elems:
            class_name = _elem.get_attribute('class')
            if class_name == 'isv-r PNCib MSM1fd BUooTd':
                anchor_tags = _elem.find_elements(By.TAG_NAME, 'a')
                for anchor_tag in anchor_tags:
                    class_name = anchor_tag.get_attribute('class')
                    if class_name == "VFACy kGQAp sMi44c lNHeqe":
                        sub.append(anchor_tag.get_attribute('href'))
        return sub


def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


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

        # get the total file size
        file_size = int(response.headers.get("Content-Length", 0))
        self.cnt += 1
        # get the file name
        filename = os.path.join(path, f'image-{self.cnt}.png')

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


class ImageHarvester:
    def __init__(self, keywords):
        self.q = keywords
        self.folder = os.path.join('data', self.q)
        self.extractor = Extractor()
        self.downloader = Downloader()

    def get_images_from_web(self):
        base = os.path.join(self.folder, 'webpages')
        refs = self.extractor.get_all_website_urls(self.q)
        print(f"Found {len(refs)} websites")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            ans = executor.map(self.extractor.get_images_from_webpage, refs)

        results = list(ans)
        for dic in results:
            for key, lis in dic.items():
                path = os.path.join(base, key)
                os.makedirs(path, exist_ok=True)
                self.downloader.download_all(lis, path)


if __name__ == '__main__':
    print("Welcome to Image Harvester\n")
    ih = ImageHarvester("jurassic park")
    ih.get_images_from_web()
