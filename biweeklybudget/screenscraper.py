"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of biweeklybudget, also known as biweeklybudget.

    biweeklybudget is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    biweeklybudget is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with biweeklybudget.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/biweeklybudget> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""

import os
import logging
import codecs
import urllib
import json

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

logger = logging.getLogger(__name__)


class ScreenScraper(object):
    """
    Base class for screen-scraping bank/financial websites.
    """

    def __init__(self, savedir='./', screenshot=False):
        """
        Initialize ScreenScraper.

        :param savedir: directory to save OFX in
        :type savedir: str
        :param screenshot: whether or not to take screenshots throughout the
          process
        :type screenshot: bool
        """
        self._savedir = os.path.abspath(os.path.expanduser(savedir))
        if not os.path.exists(self._savedir):
            os.makedirs(self._savedir)
        self._cookie_file = os.path.join(self._savedir, 'cookies.txt')
        logger.debug('Using savedir: %s', self._savedir)
        self._screenshot_num = 1
        self._screenshot = screenshot
        if self._screenshot:
            logger.warning("screenshotting all actions")
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:56.0) ' \
                          'Gecko/20100101 Firefox/56.0'

    def load_cookies(self, cookie_file):
        """
        Load cookies from a JSON cookie file on disk. This file is not the
        format used natively by PhantomJS, but rather the JSON-serialized
        representation of the dict returned by
        :py:meth:`selenium.webdriver.remote.webdriver.WebDriver.get_cookies`.

        Cookies are loaded via
        :py:meth:`selenium.webdriver.remote.webdriver.WebDriver.add_cookie`

        :param cookie_file: path to the cookie file on disk
        :type cookie_file: str
        """
        if not os.path.exists(cookie_file):
            logger.warning('Cookie file does not exist: %s', cookie_file)
            return
        logger.info('Loading cookies from: %s', cookie_file)
        with open(cookie_file, 'r') as fh:
            cookies = json.loads(fh.read())
        count = 0
        for c in cookies:
            try:
                self.browser.add_cookie(c)
                count += 1
            except Exception as ex:
                logger.info('Error loading cookie %s: %s', c, ex)
        logger.debug('Loaded %d of %d cookies', count, len(cookies))

    def save_cookies(self, cookie_file):
        """
        Save cookies to a JSON cookie file on disk. This file is not the
        format used natively by PhantomJS, but rather the JSON-serialized
        representation of the dict returned by
        :py:meth:`selenium.webdriver.remote.webdriver.WebDriver.get_cookies`.

        :param cookie_file: path to the cookie file on disk
        :type cookie_file: str
        """
        cookies = self.browser.get_cookies()
        raw = json.dumps(cookies)
        with open(cookie_file, 'w') as fh:
            fh.write(raw)
        logger.info('Wrote %d cookies to: %s', len(cookies), cookie_file)

    def do_screenshot(self):
        """take a debug screenshot"""
        if not self._screenshot:
            return
        fname = os.path.join(
            os.getcwd(), '{n}.png'.format(n=self._screenshot_num)
        )
        self.browser.get_screenshot_as_file(fname)
        logger.debug(
            "Screenshot: {f} of: {s}".format(
                f=fname,
                s=self.browser.current_url
            )
        )
        self._screenshot_num += 1

    def error_screenshot(self, fname=None):
        if fname is None:
            fname = os.path.join(os.getcwd(), 'webdriver_fail.png')
        self.browser.get_screenshot_as_file(fname)
        logger.error("Screenshot saved to: {s}".format(s=fname))
        logger.error("Page title: %s", self.browser.title)
        html_path = os.path.join(os.getcwd(), 'webdriver_fail.html')
        source = self.browser.execute_script(
            "return document.getElementsByTagName('html')[0].innerHTML"
        )
        with codecs.open(html_path, 'w', 'utf-8') as fh:
            fh.write(source)
        logger.error('Page source saved to: %s', html_path)

    def xhr_get_url(self, url):
        """ use JS to download a given URL, return its contents """
        script = 'var xhr = new XMLHttpRequest(); '
        script += 'var jantman_dl_response = null; '
        script += 'xhr.open("GET", "{url}", false); '.format(url=url)
        script += 'xhr.send(null); '
        script += 'jantman_dl_response = xhr.response; '
        script += 'return jantman_dl_response;'
        logger.debug("executing in browser: {s}".format(s=script))
        res = self.browser.execute_script(script)
        logger.debug("got {c} characters of return value from script".format(
            c=len(res)))
        return res

    def xhr_post_urlencoded(self, url, data, headers={}):
        """ use JS to download a given URL, return its contents """
        if not isinstance(data, type('')) and not isinstance(data, type(u'')):
            data = urllib.urlencode(data)
        script = 'var xhr = new XMLHttpRequest(); '
        script += 'var jantman_dl_response = null; '
        script += 'xhr.open("POST", "{url}", false); '.format(url=url)
        if isinstance(headers, type({})):
            headers["Content-type"] = "application/x-www-form-urlencoded"
            for k, v in headers.items():
                script += 'xhr.setRequestHeader("%s", "%s"); ' % (k, v)
        else:
            for item in headers:
                script += 'xhr.setRequestHeader("%s", "%s"); ' % (
                    item[0], item[1]
                )
        script += 'xhr.send("{p}"); '.format(p=data)
        script += 'jantman_dl_response = { resp: xhr.response, ' \
                  'respText: xhr.responseText, status: xhr.status, ' \
                  'headers: xhr.getAllResponseHeaders() }; '
        script += 'return JSON.stringify(jantman_dl_response);'
        logger.debug("executing in browser: %s", script)
        res = self.browser.execute_script(script)
        j = json.loads(res)
        logger.debug("Script returned %d length result (status %s; "
                     "headers: %s)", len(j['respText']),
                     j['status'],
                     j['headers'].replace("\r", "").replace("\n", "; "))
        return j['respText']

    def get_browser(self, browser_name):
        """get a webdriver browser instance """
        if browser_name == 'firefox':
            logger.debug("getting Firefox browser (local)")
            if 'DISPLAY' not in os.environ:
                logger.debug("exporting DISPLAY=:0")
                os.environ['DISPLAY'] = ":0"
            browser = webdriver.Firefox()
        elif browser_name == 'chrome':
            logger.debug("getting Chrome browser (local)")
            browser = webdriver.Chrome()
        elif browser_name == 'phantomjs':
            logger.debug("getting PhantomJS browser (local)")
            dcap = dict(DesiredCapabilities.PHANTOMJS)
            dcap["phantomjs.page.settings.userAgent"] = self.user_agent
            args = [
                '--cookies-file={c}'.format(c=self._cookie_file),
                '--ssl-protocol=any',
                '--ignore-ssl-errors=true',
                '--web-security=false'
            ]
            browser = webdriver.PhantomJS(
                desired_capabilities=dcap, service_args=args
            )
            browser.set_window_size(1024, 768)
        else:
            raise SystemExit(
                "ERROR: browser type must be one of 'firefox', 'chrome' or "
                "'phantomjs', not '{b}'".format(b=browser_name))
        logger.debug("returning browser")
        return browser

    def doc_readystate_is_complete(self, foo):
        """ return true if document is ready/complete, false otherwise """
        result_str = self.browser.execute_script("return document.readyState")
        if result_str == "complete":
            return True
        return False

    def jquery_finished(self, foo):
        """ return true if jQuery.active == 0 else false """
        active = self.browser.execute_script("return jQuery.active")
        if active == 0:
            return True
        return False

    def wait_for_ajax_load(self, timeout=20):
        """
        Function to wait for an ajax event to finish and trigger page load,
        like the Janrain login form.

        Pieced together from
        http://stackoverflow.com/a/15791319

        timeout is in seconds
        """
        WebDriverWait(self.browser, timeout).until(
            self.doc_readystate_is_complete
        )
        return True
