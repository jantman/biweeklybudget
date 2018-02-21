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

logger = logging.getLogger(__name__)


def set_browser_for_fullpage_screenshot(driver, extra_height_px=100):
    """
    Helper method to resize a Selenium browser to the size of the document,
    for taking a full page screenshot.

    :param extra_height_px: extra pixels to add to resize height
    :param driver: Selenium webdriver instance
    """
    height = driver.execute_script(
        "return Math.max(document.body.scrollHeight, "
        "document.body.offsetHeight, document.documentElement."
        "clientHeight, document.documentElement.scrollHeight, "
        "document.documentElement.offsetHeight);"
    )
    height += extra_height_px
    curr_size = driver.get_window_size()  # dict, "width" and "height" keys
    logger.debug(
        'Resizing browser height from %d to %d', curr_size['height'], height
    )
    driver.set_window_size(curr_size['width'], height)
