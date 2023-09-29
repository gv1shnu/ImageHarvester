import time
from urllib.parse import urlparse
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
import urllib.request


class Extractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless --no-sandbox --disable-dev-shm-usage --disable-gpu")
        self.service = Service(executable_path="./cdr/chromedriver.exe")


class ImageExtractor(Extractor):
    def __init__(self):
        super().__init__()

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

    def get_images_from_pinterest_page(self, url):
        def reach_for_highest_resolution(srt):
            return srt[:21] + 'originals' + srt[21 + srt[21:].index('/'):]

        driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        driver.get(url)
        elem1 = driver.find_elements(By.CLASS_NAME, 'GrowthUnauthPinImage__Image')
        sub = []
        for i in elem1:
            x = i.get_attribute('src')
            try:
                x = reach_for_highest_resolution(str(x))
            except Exception:
                pass
            sub.append(x)
        return {url.split('/')[3]: sub}

    def get_images_from_reddit_page(self, url):
        ans = []
        try:
            weburl = urllib.request.urlopen(url)
            data = str(weburl.read()).split()

            ext = '___'
            for i in data:
                if ('.jpg' in i) and ('https://' in i) and (('redd' in i) or ('imgur' in i)):
                    ext = 'jpg'
                if ('.png' in i) and ('https://' in i) and \
                        ((('redd' in i) or ('imgur' in i)) and 'redditstatic' not in i):
                    ext = 'png'

                link = i[i.index('https://'): i.index('.' + ext) + 4]
                ans.append(link)
        except Exception as z:
            pass

        return ans


class LinkExtractor(Extractor):
    def __init__(self):
        super().__init__()

    def get_all_website_urls(self, q, param):
        return list(set(
            self.get_website_urls(q, param) +
            self.get_g_website_urls(q, param)
        ))

    def get_website_urls(self, q, param=' '):
        def check(_plink, _param):
            return str(_plink).find(_param) >= 0

        driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        key = "+".join(q.split(' '))
        driver.get(f'https://www.google.co.in/search?q={key}+{param}')
        _refs = []
        for page_num in range(1, 9):
            try:
                # Navigating to next page
                links = driver.find_elements(By.CLASS_NAME, 'yuRUbf')
                for link in links:
                    plink = link.find_element(By.TAG_NAME, 'a').get_attribute("href")
                    if check(plink, param):
                        _refs.append(str(plink))
                _next = driver.find_element(By.XPATH, '//*[@id="pnnext"]')
                _next.click()
                time.sleep(1)
            except NoSuchElementException:
                # Last page reached
                break
        driver.close()
        return _refs

    def get_g_website_urls(self, q, param):
        """
        Get URLs from google images
        """
        driver = webdriver.Chrome(options=self.chrome_options, service=self.service)
        driver.get('https://www.google.com/')
        searchBox = driver.find_element(By.NAME, 'q')
        searchBox.send_keys(f"{q} {param}")
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


def is_valid(url):
    """
    Checks whether `url` is a valid URL.
    """
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


def scroll(driver, X=3, _wait=10, _sleep=2):
    value = 0
    print('Scrolling...')
    for i in range(X):
        driver.execute_script("scrollBy(" + str(value) + ",+1000);")
        value += _wait
        time.sleep(_sleep)
    # The above code is just to scroll down the page for loading all images
