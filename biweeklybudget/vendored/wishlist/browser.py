from __future__ import unicode_literals
import os
import tempfile
import sys
import codecs
import pickle
import logging
import time
from contextlib import contextmanager
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from selenium import webdriver
#from selenium.webdriver.common.keys import Keys
# https://github.com/SeleniumHQ/selenium/blob/master/py/selenium/common/exceptions.py
from selenium.common.exceptions import NoSuchElementException, \
    WebDriverException, \
    NoSuchWindowException
from pyvirtualdisplay import Display
from bs4 import BeautifulSoup
from bs4 import Tag
import requests

#from selenium.webdriver.firefox.webdriver import WebDriver as BaseWebDriver
#from selenium.webdriver.chrome.options import Options
#from selenium.webdriver.firefox.webelement import FirefoxWebElement as BaseWebElement # selenium 3.0
#from selenium.webdriver.remote.webelement import WebElement as BaseWebElement # selenium <3.0

from .compat import *


logger = logging.getLogger(__name__)


class ParseError(RuntimeError):
    """This gets raised any time Browser.element() fails to parse,
    it wraps NoSuchElementException"""
    def __init__(self, msg="", body="", error=None):
        if not msg:
            if error:
                msg = error.message

        if body:
            self.body = body

        self.error = error
        super(ParseError, self).__init__(msg)


class RecoverableCrash(IOError):
    def __init__(self, e):
        self.error = e
        super(RecoverableCrash, self).__init__(e.message)


class Soup(object):
    def soupify(self, body):
        # https://www.crummy.com/software/BeautifulSoup/
        # docs: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
        # bs4 codebase: http://bazaar.launchpad.net/~leonardr/beautifulsoup/bs4/files
        if isinstance(body, Tag): return body
        soup = BeautifulSoup(body, "html.parser")
        return soup


class Cookies(object):
    """This will write and read cookies for a Browser instance, calling Browser.location()
    will use this class to load cookies for the given domain if they are available

    https://www.quora.com/Is-there-a-way-to-keep-the-session-after-login-with-Selenium-Python
    http://stackoverflow.com/a/15058521/5006
    http://stackoverflow.com/questions/30791771/persistent-selenium-cookies-in-python
    https://groups.google.com/forum/#!topic/selenium-users/iHuoa5HTzzA

    alternative to cookies, creating a profile (Firefox specific which is why I didn't
    do it, so I could switch to chrome) http://stackoverflow.com/a/5595349/5006
    """
    @property
    def jar(self):
        """Returns all the cookies as a CookieJar file"""
        # https://github.com/kennethreitz/requests/blob/master/requests/packages/urllib3/response.py
        # http://docs.python-requests.org/en/latest/api/#api-cookies
        # http://docs.python-requests.org/en/master/_modules/requests/cookies/
        # http://docs.python-requests.org/en/master/user/quickstart/#cookies
        jar = requests.cookies.RequestsCookieJar()
        for c in self:
            name = c.pop("name")
            value = c.pop("value")
            c["rest"] = {"httpOnly": c.pop("httpOnly", None)}
            c["expires"] = c.pop("expiry", None)

            jar.set(name, value, **c)
        return jar

    @property
    def directory(self):
        directory = getattr(self, "_directory", None)
        if directory is None:
            directory = os.environ.get("BROWSER_CACHE_DIR", "")
            if directory:
                directory = os.path.abspath(os.path.expanduser(directory))
            else:
                directory = tempfile.gettempdir()

            self._directory = directory
        return directory

    @property
    def path(self):
        cookies_d = self.directory
        cookies_f = os.path.join(cookies_d, "{}.txt".format(self.domain))
        return cookies_f

    def __iter__(self):
        cookies_f = self.path
        if os.path.isfile(cookies_f):
            with open(cookies_f, "rb") as f:
                cookies = pickle.load(f)

            for cookie in cookies:
                yield cookie

    def save(self, cookies):
        """save the cookies in browser"""
        cookies_f = self.path
        with open(cookies_f, "w+b") as f:
            pickle.dump(cookies, f)

    def __init__(self, domain):
        """
        browser -- selenium web driver -- usually Firefox or Chrome
        """
        self.domain = domain


class Browser(Soup):
    """This is a wrapper around selenium and pyvirtualdisplay to make browsering
    from the command line easier

    link -- Selinium source -- https://github.com/SeleniumHQ/selenium/tree/master/py
    link -- https://pypi.python.org/pypi/selenium
    """
    @property
    def body(self):
        """return the body of the current page"""
        # http://stackoverflow.com/a/7866938/5006
        # http://stackoverflow.com/a/16114362/5006
        return self.browser.page_source

    @property
    def current_url(self):
        """return the current url"""
        # http://stackoverflow.com/questions/15985339/how-do-i-get-current-url-in-selenium-webdriver-2-python
        return self.browser.current_url

    @property
    def browser(self):
        """wrapper around the browser in case we want to switch from Firefox, you
        should use this over the .firefox property"""
        browser = getattr(self, "_browser", None)
        if browser is None:
            browser = self.chrome
            #browser._web_element_cls = WebElement
            self._browser = browser

        return browser

    @browser.deleter
    def browser(self):
        try:
            self._browser.close()
            del self._browser
        except (WebDriverException, AttributeError):
            pass

    @property
    def display(self):
        display = getattr(self, "_display", None)
        if display is None:
            # http://coreygoldberg.blogspot.com/2011/06/python-headless-selenium-webdriver.html
            display = Display(visible=0, size=(800, 600))
            display.start()
            self._display = display
        return display

    @property
    def chrome(self):
        # https://github.com/SeleniumHQ/selenium/blob/master/py/selenium/webdriver/remote/webdriver.py
        # http://www.guguncube.com/2983/python-testing-selenium-with-google-chrome
        # https://gist.github.com/addyosmani/5336747
        # http://blog.likewise.org/2015/01/setting-up-chromedriver-and-the-selenium-webdriver-python-bindings-on-ubuntu-14-dot-04/
        # https://sites.google.com/a/chromium.org/chromedriver/getting-started
        # http://stackoverflow.com/questions/8255929/running-webdriver-chrome-with-selenium
        chrome = webdriver.Chrome()
        return chrome

#     @property
#     def firefox(self):
#         profile = webdriver.FirefoxProfile()
#         #firefox = webdriver.Firefox(firefox_profile=profile)
#         firefox = WebDriver(firefox_profile=profile)
#         return firefox


    @classmethod
    @contextmanager
    def open(cls):
        """Where all the magic happens, you use this to start the virtual display
        and power up the browser

        with Browser.open() as browser:
            browser.location("http://example.com")
        """
        try:
            instance = cls()
            # start up the display (if available)
            instance.display
            yield instance

        except Exception as e:
            logger.exception(e)
            exc_info = sys.exc_info()
            if instance:
                instance.handle_error(e)
            reraise(*exc_info)

        finally:
            instance.close()

    def handle_error(self, e):
        try:
            directory = tempfile.gettempdir()
            filename = os.path.join(directory, "wishlist.png")
            instance.browser.get_screenshot_as_file(filename)
        except Exception as e:
            pass

        try:
            with codecs.open(os.path.join(directory, "wishlist.html"), encoding='utf-8', mode='w+') as f:
                f.write(instance.body)
        except Exception as e:
            pass

    def location(self, url, ignore_cookies=False):
        """calls the selenium driver's .get() method, and will load cookies if they
        are available

        url -- string -- the full url (scheme, domain, path)
        ignore_cookies -- boolean -- if True then don't try and load cookies
        """
        logger.debug("Loading location {}".format(url))
        driver = self.browser
        driver.get(url)
        url_bits = urlparse.urlparse(url)
        domain = url_bits.hostname
        self.domain = domain

        if not ignore_cookies:
            if domain and (domain not in self.domains):
                logger.debug("Loading cookies for {}".format(domain))
                self.domains[domain] = domain
                cookies = Cookies(domain)
                count = 0
                for count, cookie in enumerate(cookies, 1):
                    driver.add_cookie(cookie)
                logger.debug("Loaded {} cookies".format(count))

    def element_exists(self, css_selector):
        ret = True
        try:
            self.browser.find_element_by_css_selector(css_selector)
        except NoSuchElementException as e:
            ret = False
        return ret

    def element(self, css_selector):
        """wrapper around Selenium's css selector that raises ParseError if fails"""
        try:
            return self.browser.find_element_by_css_selector(css_selector)

        except NoSuchElementException as e:
            logger.exception(e)
            raise ParseError(body=self.body, error=e)

    def wait_for_element(self, css_selector, seconds):
        # ??? -- not sure this is needed or is better than builtin methods
        # http://stackoverflow.com/questions/26566799/selenium-python-how-to-wait-until-the-page-is-loaded
        elem = None
        driver = self.browser
        for count in range(seconds):
            elem = driver.find_element_by_css_selector(css_selector)
            if elem:
                break
            else:
                time.sleep(1)

        return elem


    def __init__(self):
        self.domains = {}

    def save(self):
        """save the browser session for the given domain"""
        logger.debug("Saving cookies for {}".format(self.domain))
        cookie = Cookies(self.domain)
        cookie.save(self.browser.get_cookies())

    def close(self):
        """quit the browser and power down the virtual display"""
        logger.debug("Closing down browser")
        try:
            self.browser.close()
            del self.browser
        except Exception as e:
            logger.warn("Browser close failed with {}".format(e.message))
            pass

        logger.debug("Shutting down display")
        self.display.stop()


class SimpleBrowser(Browser):
    @property
    def body(self):
        return self.response.content

    @property
    def current_url(self):
        """return the current url"""
        # http://stackoverflow.com/questions/15985339/how-do-i-get-current-url-in-selenium-webdriver-2-python
        return self.response.url

    @property
    def browser(self):
        browser = getattr(self, "_browser", None)
        if browser is None:
            # http://docs.python-requests.org/en/latest/user/advanced/#session-objects
            browser = requests.Session()
            browser.headers.update(
                {
                    # safari
                    #"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/602.1.50 (KHTML, like Gecko) Version/10.0 Safari/602.1.50",
                    # chrome
                    # 12-26-2016 - It looks like Amazon is checking Accept-Encoding for sdch, and/or br
                    # and deciding request is from a bot if it isn't there (ie, gzip, deflate) didn't
                    # work by itself, and I initially added more headers but testing revealed
                    # that the lack of this header with those values caused the bot check"
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36",
                    "Accept-Encoding": "gzip, deflate, sdch, br",
                    # 4-26-2017, and we're back
                    "Connection": "keep-alive",
                    "Cache-Control": "max-age=0",
                    "Upgrade-Insecure-Requests": "1",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.8",
                }
            )

            self._browser = browser
        return browser

    @browser.deleter
    def browser(self):
        try:
            del self._browser
        except AttributeError:
            pass

    @property
    def display(self):
        pass

    @property
    def chrome(self):
        raise NotImplementedError()

    def handle_error(self, e):
        try:
            directory = tempfile.gettempdir()
            with codecs.open(os.path.join(directory, "wishlist.html"), encoding='utf-8', mode='w+') as f:
                f.write(instance.body)
        except Exception as e:
            pass

    def location(self, url, ignore_cookies=False):
        """calls the selenium driver's .get() method, and will load cookies if they
        are available

        url -- string -- the full url (scheme, domain, path)
        ignore_cookies -- boolean -- if True then don't try and load cookies
        """
        logger.debug("Loading location {}".format(url))

        driver = self.browser
        url_bits = urlparse.urlparse(url)
        domain = url_bits.hostname
        self.domain = domain

        if not ignore_cookies:
            if domain and (domain not in self.domains):
                logger.debug("Loading cookies for {}".format(domain))
                self.domains.add(domain)
                cookies = Cookies(domain)
                driver.cookies = cookies.jar

        self.response = driver.get(url)

    def element_exists(self, css_selector):
        raise NotImplementedError()

    def element(self, css_selector):
        raise NotImplementedError()

    def __init__(self):
        self.domains = set()

    def save(self):
        raise NotImplementedError()

    def close(self):
        del self.browser

