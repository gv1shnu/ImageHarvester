import os
import time
from urllib.parse import urljoin
import concurrent.futures
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class Extractor:
    def __init__(self, param=''):
        self.param = param
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless --no-sandbox --disable-dev-shm-usage --disable-gpu")
        self.driver_service = webdriver.chrome.service.Service(ChromeDriverManager().install())

    def check(self, plink):
        return str(plink).find(self.param) >= 0

    def get_website_urls(self, q):
        driver = webdriver.Chrome(service=self.driver_service, options=self.chrome_options)
        key = "+".join(q.split(' '))
        driver.get(f'https://www.google.co.in/search?q={key}+{self.param}')
        _refs = []
        for page_num in range(1, 9):
            try:
                print("\nNavigating to Page {}".format(str(page_num)))
                links = driver.find_elements(By.CLASS_NAME, 'yuRUbf')
                for link in links:
                    plink = link.find_element(By.TAG_NAME, 'a').get_attribute("href")
                    if self.check(plink):
                        _refs.append(str(plink))
                _next = driver.find_element(By.XPATH, '//*[@id="pnnext"]')
                _next.click()
                time.sleep(1)
            except NoSuchElementException:
                print("Last page reached\n")
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
        return urls


class ImageHarvester:
    def __init__(self, keywords):
        self.q = keywords
        self.folder = os.path.join('./', self.q)
        self.extractor = Extractor()

    def get_images_from_web(self):
        path = os.path.join(self.folder, 'webpages')
        os.makedirs(path, exist_ok=True)
        refs = self.extractor.get_website_urls(self.q)
        print(f"Found {len(refs)} websites")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(self.extractor.get_images_from_webpage, refs)
        return list(results)


if __name__ == '__main__':
    print("Welcome to Image Harvester\n")
    extractor = Extractor()
    x = extractor.get_images_from_webpage("https://en.wikipedia.org/wiki/Jurassic_Park_(film)")

    for i in x:
        print(i)