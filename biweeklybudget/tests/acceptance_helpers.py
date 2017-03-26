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

from time import sleep
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class AcceptanceHelper(object):

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

    def wait_for_modal_shown(self, driver, modal_id):
        """
        Wait for the modal with the given ID to be shown.

        :param driver: Selenium driver instance
        :param modal_id: the id of the modal div
        :type modal_id: str
        """
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, modal_id))
        )
