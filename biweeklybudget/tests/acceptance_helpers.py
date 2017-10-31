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

import logging
from time import sleep
from selenium.common.exceptions import (
    StaleElementReferenceException, TimeoutException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from biweeklybudget.utils import fmt_currency

logger = logging.getLogger(__name__)


class AcceptanceHelper(object):

    def normalize_html(self, html):
        """
        Given a HTML string, normalize some differences that may occur between
        different test environments.

        :param html: html
        :type html: str
        :return: normalized HTML
        :rtype: str
        """
        # strange inconsistency between local and TravisCI...
        html = html.replace('style="display: none; "', 'style="display: none;"')
        return html

    def relurl(self, url):
        """
        Given an absolute URL including ``self.baseurl``, return the relative
        URL portion excluding the base url.

        :param url: base url
        :type url: str
        :returns: relative URL
        :rtype: str
        """
        return url.replace(self.baseurl, '')

    def thead2list(self, elem):
        """
        Given a webdriver table element, return the inner text strings of each
        ``th`` within the ``thead``, left to right.

        :param elem: table element
        :type elem: selenium.webdriver.remote.webelement.WebElement
        :return: list of table heading strings in order left to right
        :rtype: list
        """
        thead = elem.find_element_by_tag_name('thead')
        tr = thead.find_element_by_tag_name('tr')
        cells = []
        for th in tr.find_elements_by_tag_name('th'):
            cells.append(th.text.strip())
        return cells

    def thead2elemlist(self, elem):
        """
        Given a webdriver table element, return the WebElements of each
        ``th`` within the ``thead``, left to right.

        :param elem: table element
        :type elem: selenium.webdriver.remote.webelement.WebElement
        :return: list of table heading WebElements in order left to right
        :rtype: list
        """
        thead = elem.find_element_by_tag_name('thead')
        tr = thead.find_element_by_tag_name('tr')
        cells = []
        for th in tr.find_elements_by_tag_name('th'):
            cells.append(th)
        return cells

    def tbody2textlist(self, elem):
        """
        Given a webdriver ``table`` element, return a list of table rows, top to
        bottom, each being represented by a list of strings corresponding to
        the text content of each column in the row, left to right.

        :param elem: table element
        :type elem: selenium.webdriver.remote.webelement.WebElement
        :return: list of table rows, each being a list of cell content strings
        :rtype: list
        """
        tbody = elem.find_element_by_tag_name('tbody')
        rows = []
        for tr in tbody.find_elements_by_tag_name('tr'):
            row = []
            for td in tr.find_elements_by_xpath('*'):
                if td.tag_name not in ['td', 'th']:
                    continue
                row.append(td.text.strip())
            rows.append(row)
        return rows

    def tbody2trlist(self, elem):
        """
        Given a webdriver ``table`` element, return a list of table rows, top to
        bottom.

        :param elem: table element
        :type elem: selenium.webdriver.remote.webelement.WebElement
        :return: list of ``tr`` WebElements
        :rtype: list
        """
        tbody = elem.find_element_by_tag_name('tbody')
        return [x for x in tbody.find_elements_by_tag_name('tr')]

    def tbody2elemlist(self, elem):
        """
        Given a webdriver ``table`` element, return a list of table rows, top to
        bottom, each being represented by a list of WebElements corresponding to
        the cells of each column in the row (td or th), left to right.

        :param elem: table element
        :type elem: selenium.webdriver.remote.webelement.WebElement
        :return: list of table rows, each being a list of cell WebElements
        :rtype: list
        """
        tbody = elem.find_element_by_tag_name('tbody')
        rows = []
        for tr in tbody.find_elements_by_tag_name('tr'):
            row = []
            for td in tr.find_elements_by_xpath('*'):
                if td.tag_name not in ['td', 'th']:
                    continue
                row.append(td)
            rows.append(row)
        return rows

    def retry_stale(self, func, *args, **kwargs):
        """
        Retry calling ``func`` with ``*args, **kwargs`` up to 5 times, sleeping
        1 second between each, if a StaleElementReferenceException is found.
        Return its return value.
        """
        e = None
        for i in range(5):
            try:
                res = func(*args, **kwargs)
                return res
            except StaleElementReferenceException as ex:
                e = ex
                sleep(1)
        raise e

    def wait_for_modal_shown(self, driver):
        """
        Wait for the modal to be shown.

        :param driver: Selenium driver instance
        :type driver: selenium.webdriver.remote.webdriver.WebDriver
        """
        self.wait_until_clickable(driver, 'modalLabel', timeout=10)

    def wait_until_clickable(self, driver, elem_id, by=By.ID, timeout=10):
        """
        Wait for the modal to be shown.

        :param driver: Selenium driver instance
        :type driver: selenium.webdriver.remote.webdriver.WebDriver
        :param elem_id: element ID
        :type elem_id: str
        :param by: What method to use to find the element. This must be one of
          the strings which are values of
          :py:class:`selenium.webdriver.common.by.By` attributes.
        :type by: str
        :param timeout: timeout in seconds
        :type timeout: int
        """
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, elem_id))
        )

    def wait_for_id(self, driver, id):
        """
        Wait for the element with ID ``id`` to be shown.

        :param driver: Selenium driver instance
        :type driver: selenium.webdriver.remote.webdriver.WebDriver
        :param id: ID of the element
        :type id: str
        """
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, id))
        )

    def wait_for_jquery_done(self, driver, sleep_sec=0.2, tries=20):
        """
        Wait until ``jQuery.active == 0``. Tries ``tries`` times at
        ``sleep`` second intervals; raises an exception if all tries fail.

        :param driver: Selenium driver instance
        :type driver: selenium.webdriver.remote.webdriver.WebDriver
        :param sleep_sec: how long to sleep between tries
        :type sleep_sec: float
        :param tries: how many times to try
        :type tries: bool
        """
        script = 'return jQuery.active == 0'
        count = 0
        while count < 20:
            res = driver.execute_script(script)
            if res:
                logger.debug(
                    'jQuery done after %d seconds', (sleep_sec * tries)
                )
                break
            sleep(sleep_sec)
        else:
            raise RuntimeError(
                'jQuery did not finish after %d seconds',
                (sleep_sec * tries)
            )

    def wait_for_load_complete(self, driver, sleep_sec=0.2, tries=20):
        """
        Wait until ``document.readyState == "complete"``. Tries ``tries`` times
        at ``sleep`` second intervals; raises an exception if all tries fail.

        :param driver: Selenium driver instance
        :type driver: selenium.webdriver.remote.webdriver.WebDriver
        :param sleep_sec: how long to sleep between tries
        :type sleep_sec: float
        :param tries: how many times to try
        :type tries: bool
        """
        script = 'return document.readyState == "complete"'
        count = 0
        while count < 20:
            res = driver.execute_script(script)
            if res:
                logger.debug(
                    'readyState complete after %d seconds', (sleep_sec * tries)
                )
                break
            sleep(sleep_sec)
        else:
            raise RuntimeError(
                'readyState did not reach complete after %d seconds',
                (sleep_sec * tries)
            )

    def get_modal_parts(self, selenium, wait=True):
        """
        Return a 3-tuple of the WebElements representing the modalDiv,
        modalLabel h4 and modalBody div.

        :param selenium: Selenium driver instance
        :type selenium: selenium.webdriver.remote.webdriver.WebDriver
        :param wait: whether or not to wait for presence of modalLabel
        :type wait: bool
        :return: 3-tuple of (modalDiv WebElement, modalLabel WebElement,
          modalBody WebElement)
        :rtype: tuple
        """
        if wait:
            self.wait_for_modal_shown(selenium)
        modal = selenium.find_element_by_id('modalDiv')
        title = selenium.find_element_by_id('modalLabel')
        body = selenium.find_element_by_id('modalBody')
        return modal, title, body

    def assert_modal_displayed(self, modal, title, body):
        """
        Assert that the modal is displayed.

        :param modal: the modal itself
        :type modal: selenium.webdriver.remote.webelement.WebElement
        :param title: the title element of the modal
        :type title: selenium.webdriver.remote.webelement.WebElement
        :param body: the body element of the modal
        :type body: selenium.webdriver.remote.webelement.WebElement
        """
        assert modal.is_displayed()
        assert modal.is_enabled()
        assert title.is_displayed()
        assert title.is_enabled()
        assert body.is_displayed()
        assert body.is_enabled()

    def assert_modal_hidden(self, modal, title, body):
        """
        Assert that the modal is displayed.

        :param modal: the modal itself
        :type modal: selenium.webdriver.remote.webelement.WebElement
        :param title: the title element of the modal
        :type title: selenium.webdriver.remote.webelement.WebElement
        :param body: the body element of the modal
        :type body: selenium.webdriver.remote.webelement.WebElement
        """
        assert modal.is_displayed() is False
        assert title.is_displayed() is False
        assert body.is_displayed() is False

    def get(self, _selenium, url):
        """
        Wrapper around ``selenium`` fixture's ``get()`` method to retry up to
        4 times on TimeoutException.

        :param _selenium: selenium fixture instance
        :param url: URL to get
        :type url: str
        """
        count = 0
        while True:
            count += 1
            try:
                _selenium.get(url)
                return
            except TimeoutException:
                if count > 4:
                    raise
                print('selenium.get(%s) timed out; trying again', url)
            except Exception:
                raise
        self.wait_for_load_complete(_selenium)
        self.wait_for_jquery_done(_selenium)

    def inner_htmls(self, elems):
        """
        Return a list of lists, where each outer list represents an element in
        ``elems``, and each inner list represents the ``innerHTML`` attribute
        of each item in the outer list.

        :param elems: A list of HTMLElements, such as the return value of
          :py:meth:`~.tbody2elemlist`
        :type elems: list
        :return: list of lists, rows to innerHTML of elements in each row
        :rtype: list
        """
        htmls = []
        for row in elems:
            htmls.append(
                [x.get_attribute('innerHTML') for x in row]
            )
        return htmls

    def sort_trans_rows(self, rows):
        """
        Sort a list of transaction rows by date and then amount, to match up
        with the HTML in transactions table.

        :param rows: list of inner HTMLs, such as those returned by
          :py:meth:`~.inner_htmls`.
        :type rows: list
        :return: sorted rows
        :rtype: list
        """
        tmp_rows = []
        for row in rows:
            row[1] = float(row[1].replace('$', ''))
            tmp_rows.append(row)
        ret = []
        for row in sorted(tmp_rows, key=lambda x: (x[0], x[1])):
            row[1] = fmt_currency(row[1])
            ret.append(row)
        return ret
