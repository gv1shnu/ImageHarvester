from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import threading
from urllib.parse import urljoin, urlparse
import requests
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
import pyautogui
import urllib.error


class Extractor:
    def __init__(self, param=''):
        print('Link Extractor')
        self.param = param

    def check(self, plink):
        if str(plink).find(self.param) == -1:
            return False
        else:
            return True

    def get_web_page_links(self, key):
        driver = webdriver.Chrome()
        driver.get('https://google.com/')
        print("\nOpening Chrome")
        time.sleep(2)

        searchbox = driver.find_element('q')
        key += ' {}'.format(self.param)
        searchbox.send_keys(key)
        searchbox.send_keys(Keys.ENTER)

        time.sleep(1)
        pyautogui.keyDown('esc')
        pyautogui.keyUp('esc')

        _refs = []
        page_num = 0
        while True:
            page_num += 1
            try:
                print("\nNavigating to Page " + str(page_num))
                links = driver.find_elements(By.CLASS_NAME, 'yuRUbf')
                count = 0
                for link in links:
                    plink = link.find_element(By.TAG_NAME, 'a').get_attribute("href")
                    if is_valid(plink):
                        if self.check(plink):
                            print(str(link.find_element(By.TAG_NAME, 'a').get_attribute("href")))
                            _refs.append(str(link.find_element(By.TAG_NAME, 'a').get_attribute("href")))
                            count += 1

                if count > 0:
                    print("Found " + str(count) + ' {} web pages in page '.format(self.param) + str(page_num))
                else:
                    print('No {} web pages found in page '.format(self.param) + str(page_num))
                _next = driver.find_element(By.XPATH, '//*[@id="pnnext"]')
                _next.click()
                time.sleep(1)
            except NoSuchElementException:
                print("Last page reached\n")
                break
        driver.close()
        return _refs

    def get_all_images(self, url):
        """
        Returns all image URLs on a single `url`
        """
        soup = BeautifulSoup(requests.get(url).content, "html.parser")
        urls = []
        for img in tqdm(soup.find_all("img"), "Extracting images"):
            img_url = img.attrs.get("src")
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
            # finally, if the url is valid
            if is_valid(img_url):
                urls.append(img_url)
        return urls


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


class Downloader:
    def __init__(self, pathname):
        print('Download images')
        self.pathname = pathname
        self.cnt = 0

    def download(self, url, FORMAT):
        """
        Downloads a file given an URL and puts it in the folder `pathname`
        """
        # if path doesn't exist, make that path dir
        if not os.path.isdir(self.pathname):
            os.makedirs(self.pathname)
        # download the body of response by chunk, not immediately
        try:
            response = requests.get(url, stream=True)
        except requests.exceptions.ConnectionError:
            time.sleep(10)
            response = requests.get(url, stream=True)

        # get the total file size
        file_size = int(response.headers.get("Content-Length", 0))

        # get the file name
        self.cnt += 1
        filename = os.path.join(self.pathname, 'image-{}.{}'.format(FORMAT, self.cnt))

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

    def write(self, src, dest):
        try:
            urllib.request.urlretrieve(url=src, filename=dest)
        except urllib.error.HTTPError:
            print("HTTPError at {}".format(src))


##############################################################################
class ImageHarvester:
    def __init__(self, keywords):
        self.q = keywords
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless --no-sandbox --disable-dev-shm-usage --disable-gpu")
        self.driver_service = webdriver.chrome.service.Service(ChromeDriverManager().install())

    def get_images_from_webpages(self):
        folder = './' + self.q
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass

        extractor = Extractor()
        downloader = Downloader(folder)

        refs = extractor.get_web_page_links(self.q)
        print("Found ", len(refs), " websites")

        start = time.time()

        def fun(_url, _path):
            _imgs = extractor.get_all_images(_url)
            print('Extracted {} images from {}'.format(len(_imgs), url))
            for _img in _imgs:
                downloader.download(_img, _path)

        threads = []
        for url in refs:
            t = threading.Thread(target=fun, args=(url, folder))
            t.start()
            threads.append(t)

        for thread in threads:
            thread.join()

        end = time.time()
        print('\nTime spent downloading: {} seconds'.format(round(end - start), 1))

    def get_images_from_pinterest(self):
        def get_pins(link):
            def reach_for_highest_resolution(srt):
                return srt[:21] + 'originals' + srt[21 + srt[21:].index('/'):]

            wait = 4000
            sleep = 2
            print('\nOpening ' + str(link))
            gldriver = webdriver.Chrome()
            time.sleep(2)
            gldriver.get(link)

            scroll(gldriver, 10, wait, sleep)

            elem1 = gldriver.find_elements(By.CLASS_NAME, 'GrowthUnauthPinImage__Image')
            sub = []
            for i in elem1:
                sub.append(i.get_attribute('src'))

            count = 0
            downloader = Downloader(self.q)

            print("Found " + str(len(sub)) + ' images\n')
            for sr in sub:
                src = str(sr)

                dest = self.q + '/image' + str(count) + '.jpg'
                try:
                    src = reach_for_highest_resolution(src)
                except Exception as e:
                    print("\nTried for original resolution..failed with Exception.: " + str(e))
                count += 1
                downloader.write(src, dest)

        extractor = Extractor('pinterest')
        refs = extractor.get_web_page_links(self.q)
        print("Found " + str(len(refs)) + ' web pages\n')

        try:
            os.mkdir(self.q)
        except FileExistsError:
            pass

        for url in refs:
            get_pins(url)
            time.sleep(3)

    def get_images_from_reddit(self):
        extractor = Extractor('reddit')
        refs = extractor.get_web_page_links(self.q)

        path = './' + self.q + '/'
        if not os.path.isdir(path):
            os.mkdir(path)

        downloader = Downloader(path)

        start = time.time()
        for URL in refs:
            try:
                weburl = urllib.request.urlopen(URL)
                print('Result code: {}'.format(weburl.getcode()))
                data = str(weburl.read()).split()

                ext = '___'
                for i in data:
                    if ('.jpg' in i) and ('https://' in i) and (('redd' in i) or ('imgur' in i)):
                        ext = 'jpg'
                    if ('.png' in i) and ('https://' in i) and \
                            ((('redd' in i) or ('imgur' in i)) and 'redditstatic' not in i):
                        ext = 'png'

                    link = i[i.index('https://'): i.index('.' + ext) + 4]
                    downloader.download(link, ext)

            except Exception as z:
                print('Exception {}'.format(str(z)))
                pass

        end = time.time()
        print('\nTime spent downloading: {} seconds'.format(round(end - start), 1))

    def get_images_from_google_images(self):
        driver = webdriver.Chrome(service=self.driver_service, options=self.chrome_options)
        name_of_folder = './' + self.q
        try:
            os.mkdir(name_of_folder)
        except FileExistsError:
            pass
        time.sleep(2)

        downloader = Downloader(name_of_folder)

        # Search and locate them
        driver.get('https://www.google.com/')
        searchBox = driver.find_element(By.NAME, 'q')
        searchBox.send_keys(self.q)
        searchBox.send_keys(Keys.ENTER)
        elem = driver.find_element(By.LINK_TEXT, 'Images')
        elem.get_attribute('href')
        elem.click()

        # Scroll to load images
        value = 0
        for i in range(20):
            wait = 400
            driver.execute_script("scrollBy(" + str(value) + "," + str(wait) + ");")
            value += wait
            time.sleep(2)

        elem1 = driver.find_element(By.ID, 'islmp')
        sub = elem1.find_elements(By.TAG_NAME, "img")
        # Google images contain in a div tag with is ‘islmp’. That’s the reason to fetch it.

        print(f'Found {len(sub)} images')
        print('Downloading..')
        # Download
        for (i, link) in enumerate(sub):
            try:
                src = str(link.get_attribute('src'))
                dest = name_of_folder + '/image' + str(i + 1) + '.png'
                downloader.write(src, dest)
            except:
                pass

        driver.close()


if __name__ == '__main__':
    keys = input("Enter key words to search for: ")
