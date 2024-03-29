"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016-2024 Jason Antman <http://www.jasonantman.com>

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

from decimal import Decimal
import json
from datetime import timedelta

import lxml.html
from lxml.etree import tostring
import requests
import logging

from biweeklybudget.models.dbsetting import DBSetting
from biweeklybudget.utils import dtnow, decode_json_datetime
from biweeklybudget.flaskapp.jsonencoder import MagicJSONEncoder

logger = logging.getLogger(__name__)


class PrimeRateCalculator(object):

    def __init__(self, db_session):
        """
        :param db_session: Database session
        :type db_session: sqlalchemy.orm.session.Session
        """
        self._db_sess = db_session

    def _rate_from_marketwatch(self):
        url = 'https://www.wsj.com/market-data/bonds/moneyrates'
        logger.debug('Requesting %s for prime rate', url)
        r = requests.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                                   'Chrome/79.0.3945.130 Safari/537.36'}
        )
        doc = lxml.html.fromstring(r.text)
        prtitle = doc.xpath('//caption[starts-with(text(), "Prime Rates")]')
        if prtitle is None or len(prtitle) != 1:
            logger.error(
                'Could not find "Prime rates" TD; page: %s', r.text
            )
            raise RuntimeError('ERROR: format change in %s' % url)
        prtbody = prtitle[0].getparent().findall('tbody')[0]
        prthead = prtitle[0].getparent().findall('thead')[0]
        headrows = prthead.findall('tr')
        if not headrows[1].findall('th')[1].text == 'Latest':
            logger.error(
                'tr2,td1 contains unexpected text; prtbody: %s',
                tostring(prtbody)
            )
            raise RuntimeError('ERROR: format change in %s' % url)
        rows = prtbody.findall('tr')
        if not rows[0].findall('td')[0].text == 'U.S.':
            logger.error(
                'tr3,td0 contains unexpected text; prtbody: %s',
                tostring(prtbody)
            )
            raise RuntimeError('ERROR: format change in %s' % url)
        pr_amt = rows[0].findall('td')[1].text
        logger.debug(
            'Found prime rate from %s: %s', url, pr_amt
        )
        return pr_amt

    def _get_prime_rate(self):
        """
        Get the US Prime Rate from MarketWatch; update the DB and return the
        value.

        :return: current US Prime Rate
        :rtype: decimal.Decimal
        """
        rate = self._rate_from_marketwatch()
        rate = Decimal(rate) * Decimal('0.01')
        s = self._db_sess.query(DBSetting).get('prime_rate')
        if s is None:
            s = DBSetting(name='prime_rate')
        logger.info('Got Prime Rate from MarketWatch: %s', rate)
        s.value = json.dumps({
            'value': '%s' % rate,
            'date': dtnow()
        }, cls=MagicJSONEncoder)
        self._db_sess.add(s)
        self._db_sess.flush()
        self._db_sess.commit()
        return rate

    @property
    def prime_rate(self):
        """
        Return the current US Prime Rate

        :return: current US Prime Rate
        :rtype: decimal.Decimal
        """
        pr = self._db_sess.query(DBSetting).get('prime_rate')
        if pr is None:
            return self._get_prime_rate()
        j = json.loads(pr.value)
        d = decode_json_datetime(j['date'])
        if d >= (dtnow() - timedelta(hours=48)):
            return Decimal(j['value'])
        return self._get_prime_rate()

    def calculate_apr(self, margin):
        """
        Calculate an APR based on the prime rate.

        :param margin: margin added to Prime Rate to get APR
        :type margin: decimal.Decimal
        :return: effective APR
        :rtype: decimal.Decimal
        """
        return self.prime_rate + margin
