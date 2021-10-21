import signal
import sys
from selenium import webdriver
import psutil
import platform
import os
import re
import subprocess
import requests
import io
import zipfile

""" Chrome/ChromeDriver related setup """

def get_chrome_version():
    """
    Gets Chrome version and OS type
    @return: (Chrome version, OS type)
    @rtype: tuple of strings
    """
    regex = re.compile(r'\d+\.\d+\.\d+')
    try:
        if platform.system() == "Linux":
            this_os = "linux64"
            # https://askubuntu.com/questions/505531/what-version-of-google-chrome-do-i-have
            chrome_version = subprocess.check_output(["google-chrome", "--version"]).split()[2]
        elif platform.system() == "Darwin":
            this_os = "mac64"
            # https://superuser.com/questions/1144651/get-chrome-version-from-commandline-in-mac
            chrome_version = subprocess.check_output(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"]).split()[2]
        else:
            this_os = "win32"
            # https://stackoverflow.com/questions/50880917/how-to-get-chrome-version-using-command-prompt-in-windows
            chrome_version = subprocess.check_output(['wmic', 'datafile', 'where', 'name="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"', 'get', 'Version', '/value']).split('=')[1]
        chrome_version = regex.search(chrome_version).group()
    except OSError as e:
        return None, this_os
    return chrome_version, this_os

def get_chrome_driver_version():
    """
    Gets chromedriver version
    @return: chromedriver version
    @rtype: string or None if chromedriver not found
    """
    regex = re.compile(r'\d+\.\d+\.\d+')
    try:
        chrome_driver = subprocess.check_output([os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver"), "-v"]).split()[1]
        chrome_driver = regex.search(chrome_driver).group()
    except OSError as e:
        chrome_driver = None
    return chrome_driver

def verify_chrome(force=False):
    """
    Verifies and updates chrome and chromedriver versions as necessary
    @param force: Force update ChromeDriver
    @type force: bool
    @return: 0 or 1, version or error
    @rtype: tuple (int, string)
    """
    chrome_version, this_os = get_chrome_version()
    if not chrome_version:
        return (1, "Chrome not installed!\n")
    chrome_driver = get_chrome_driver_version()
    if not chrome_driver or force or chrome_driver != chrome_version:
        install_driver(chrome_version, this_os)
        return verify_chrome()

    return 0, chrome_driver + '\n'

def install_driver(chrome_version, this_os):
    """
    Installs new ChromeDriver
    http://chromedriver.chromium.org/downloads/version-selection

    @param chrome_version: current Chrome version
    @type chrome_version: string
    @param this_os: type of operating system
    @type this_os: string
    """
    print("installing ChromeDriver...")
    version = requests.get('https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{}'.format(chrome_version)).text
    r = requests.get('https://chromedriver.storage.googleapis.com/{}/chromedriver_{}.zip'.format(version, this_os))
    # https://stackoverflow.com/a/14260592
    zipfile.ZipFile(io.BytesIO(r.content)).extractall(os.path.dirname(os.path.abspath(__file__)))
    os.chmod(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver"), 0o0700)
    print("ChromeDriver {} installed.".format(version))

def kill_chrome_processes():
    """
    Backup method to kill any created Chrome processes just in case the selenium methods fails
    """
    parent = psutil.Process(os.getpid())
    children = parent.children(recursive=True)
    for process in children:
        if "chrome" in process.name().lower():
            process.kill()

class Chrome(object):
    """
    Base class for any class that needs to use selenium/ChromeDriver
    """
    driver = None
    windows = []

    @classmethod
    def signal_handler(cls, sig, frame):
        """
        Detects interrupt and quits Chrome
        https://stackoverflow.com/questions/1112343/how-do-i-capture-sigint-in-python

        @param sig:
        @type sig:
        @param frame:
        @type frame:
        """
        for window in cls.windows:
            window.quit()
        sys.exit("Killed. Chrome quit successful.")

    def __init__(self, url="", headless=True, incognito=True, window_size=(1920, 1080), implicitly_wait=10):
        """
        Starts ChromeDriver and starts signal handler in case of interrupt

        https://chromedriver.chromium.org/
        https://peter.sh/experiments/chromium-command-line-switches/
        """

        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('headless')
        options.add_argument('--disable-gpu')
        if incognito:
            options.add_argument('--incognito')
        options.add_argument('--kiosk-printing')
        options.add_argument('--block-new-web-contents')
        options.add_argument('--no-default-browser-check')
        options.add_argument("--window-size=" + str(window_size).replace(' ', ''))
        self.driver = webdriver.Chrome(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver"), options=options)
        self.driver.implicitly_wait(implicitly_wait)

        self.windows.append(self)

        signal.signal(signal.SIGINT, self.signal_handler)

        if url:
            self.get(url)

    def quit(self):
        """
        Quits Chrome using selenium command, and tries through psutil if that fails for some odd reason
        """
        try:
            if Browser.driver:
                Browser.driver.quit()
                Browser.driver = None
        except BaseException as e:
            kill_chrome_processes()

    def __call__(self, url):
        self.get(url)

    def get(self, url):
        self.driver.get(url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()




