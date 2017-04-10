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

import pytest
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from pytz import UTC

from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.settings import PAY_PERIOD_START_DATE
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.models import *
import biweeklybudget.models.base  # noqa
from biweeklybudget.tests.conftest import engine


@pytest.mark.acceptance
class DONOTTestPayPeriods(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url + '/payperiods')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'Pay Periods - BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element_by_id('side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_notifications(self, selenium):
        div = selenium.find_element_by_id('notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'


@pytest.mark.acceptance
class DONOTTestPayPeriodFor(AcceptanceHelper):

    def test_current_period(self, base_url, selenium):
        start_date = PAY_PERIOD_START_DATE
        print("PayPeriod start date: %s" % start_date)
        selenium.get(base_url + '/pay_period_for?date=' + start_date.strftime(
            '%Y-%m-%d'))
        self.wait_for_load_complete(selenium)
        assert selenium.current_url == \
            base_url + '/payperiod/' + start_date.strftime('%Y-%m-%d')

    def test_current_period_end(self, base_url, selenium):
        start_date = PAY_PERIOD_START_DATE
        print("PayPeriod start date: %s" % start_date)
        send_date = start_date + timedelta(days=10)
        selenium.get(base_url + '/pay_period_for?date=' + send_date.strftime(
            '%Y-%m-%d'))
        self.wait_for_load_complete(selenium)
        assert selenium.current_url == \
            base_url + '/payperiod/' + start_date.strftime('%Y-%m-%d')


@pytest.mark.acceptance
class DONOTTestFindPayPeriod(AcceptanceHelper):

    def test_input_date(self, base_url, selenium):
        selenium.get(base_url + '/payperiods')
        i = selenium.find_element_by_id('payperiod_date_input')
        i.clear()
        start_date = PAY_PERIOD_START_DATE
        print("PayPeriod start date: %s" % start_date)
        send_date = start_date + timedelta(days=4)
        i.send_keys(send_date.strftime('%Y-%m-%d'))
        selenium.find_element_by_id('payperiod-go-button').click()
        self.wait_for_load_complete(selenium)
        assert selenium.current_url == \
            base_url + '/payperiod/' + start_date.strftime('%Y-%m-%d')

    def test_input_calendar(self, base_url, selenium):
        selenium.get(base_url + '/payperiods')
        start_date = PAY_PERIOD_START_DATE
        print("PayPeriod start date: %s" % start_date)
        send_date = start_date + timedelta(days=4)
        daysdiv = selenium.find_element_by_xpath(
            '//div[@id="cal2"]//div[@class="datepicker-days"]'
        )
        tbl = daysdiv.find_elements_by_tag_name('table')[0]
        # month
        assert tbl.find_elements_by_tag_name(
            'thead')[0].find_elements_by_tag_name(
            'tr')[1].find_elements_by_tag_name('th')[1].text == \
            dtnow().strftime('%B %Y')
        tbody = tbl.find_elements_by_tag_name('tbody')[0]
        print('Looking for datepicker TD for date %s' % send_date)
        for e in tbody.find_elements_by_tag_name('td'):
            if e.get_attribute('class') != 'day':
                continue
            if e.text.strip() == str(send_date.day):
                parent = e.find_element_by_xpath('..')
                print("Found date TD: %s - parent: %s" % (
                    e.get_attribute('innerHTML'),
                    parent.get_attribute('innerHTML')
                ))
                e.click()
                break
        else:
            raise RuntimeError("Unable to find td for date %d", send_date.day)
        self.wait_for_load_complete(selenium)
        assert selenium.current_url == \
            base_url + '/payperiod/' + start_date.strftime('%Y-%m-%d')

    def test_input_calendar_future(self, base_url, selenium):
        selenium.get(base_url + '/payperiods')
        start_date = PAY_PERIOD_START_DATE
        print("PayPeriod start date: %s" % start_date)
        send_date = start_date + relativedelta(months=3)
        send_date = send_date.replace(day=3)
        send_pp = BiweeklyPayPeriod.period_for_date(send_date, None)
        daysdiv = selenium.find_element_by_xpath(
            '//div[@id="cal2"]//div[@class="datepicker-days"]'
        )
        tbl = daysdiv.find_elements_by_tag_name('table')[0]
        thead = tbl.find_elements_by_tag_name('thead')[0]
        # month
        assert thead.find_elements_by_tag_name(
            'tr')[1].find_elements_by_tag_name('th')[1].text == \
            dtnow().strftime('%B %Y')
        tbody = tbl.find_elements_by_tag_name('tbody')[0]
        print('Advancing by 3 months')
        next_link = thead.find_element_by_xpath('//th[@class="next"]')
        next_link.click()
        self.wait_for_jquery_done(selenium)
        next_link.click()
        self.wait_for_jquery_done(selenium)
        next_link.click()
        self.wait_for_jquery_done(selenium)
        print('Looking for datepicker TD for date %s' % send_date)
        for e in tbody.find_elements_by_tag_name('td'):
            if e.get_attribute('class') != 'day':
                continue
            if e.text.strip() == str(send_date.day):
                parent = e.find_element_by_xpath('..')
                print("Found date TD: %s - parent: %s" % (
                    e.get_attribute('innerHTML'),
                    parent.get_attribute('innerHTML')
                ))
                e.click()
                break
        else:
            raise RuntimeError("Unable to find td for date %d", send_date.day)
        self.wait_for_load_complete(selenium)
        assert selenium.current_url == \
            base_url + '/payperiod/' + send_pp.start_date.strftime('%Y-%m-%d')


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
class DONOTTestPayPeriodsIndex(AcceptanceHelper):

    def test_0_clean_db(self, testdb):
        # clean the database
        biweeklybudget.models.base.Base.metadata.reflect(engine)
        biweeklybudget.models.base.Base.metadata.drop_all(engine)
        biweeklybudget.models.base.Base.metadata.create_all(engine)

    def test_1_add_account(self, testdb):
        a = Account(
            description='First Bank Account',
            name='BankOne',
            ofx_cat_memo_to_name=True,
            ofxgetter_config_json='{"foo": "bar"}',
            vault_creds_path='secret/foo/bar/BankOne',
            acct_type=AcctType.Bank
        )
        testdb.add(a)
        a.set_balance(
            overall_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC),
            ledger=1.0,
            ledger_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC)
        )
        testdb.flush()
        testdb.commit()

    def test_2_add_budgets(self, testdb):
        testdb.add(Budget(
            name='1Income',
            is_periodic=True,
            description='1Income',
            starting_balance=1000.00,
            is_income=True
        ))
        testdb.add(Budget(
            name='2Periodic',
            is_periodic=True,
            description='2Periodic',
            starting_balance=500.00
        ))
        testdb.add(Budget(
            name='3Periodic',
            is_periodic=True,
            description='3Periodic',
            starting_balance=0.00
        ))
        testdb.flush()
        testdb.commit()

    def pay_periods(self, db):
        return {
            'prev': BiweeklyPayPeriod.period_for_date(
                (PAY_PERIOD_START_DATE - timedelta(days=2)), db),
            'curr': BiweeklyPayPeriod.period_for_date(
                PAY_PERIOD_START_DATE, db),
            'next': BiweeklyPayPeriod.period_for_date(
                (PAY_PERIOD_START_DATE + timedelta(days=15)), db),
            'following': BiweeklyPayPeriod.period_for_date(
                (PAY_PERIOD_START_DATE + timedelta(days=29)), db)
        }

    def test_3_add_transactions(self, testdb):
        acct = testdb.query(Account).get(1)
        ibudget = testdb.query(Budget).get(1)
        e1budget = testdb.query(Budget).get(2)
        e2budget = testdb.query(Budget).get(3)
        periods = self.pay_periods(testdb)
        # previous pay period
        ppdate = periods['prev'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=100.00,
            budgeted_amount=100.00,
            description='prev income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=250.00,
            description='prev trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='prev trans 2',
            account=acct,
            budget=e1budget
        ))
        ppdate = periods['curr'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=1400.00,
            budgeted_amount=100.00,
            description='prev income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=1850.00,
            description='prev trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='prev trans 2',
            account=acct,
            budget=e1budget
        ))
        ppdate = periods['next'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=1400.00,
            budgeted_amount=100.00,
            description='prev income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=788.00,
            description='prev trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='prev trans 2',
            account=acct,
            budget=e1budget
        ))
        ppdate = periods['following'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=1400.00,
            budgeted_amount=100.00,
            description='prev income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=2.00,
            description='prev trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='prev trans 2',
            account=acct,
            budget=e1budget
        ))
        testdb.flush()
        testdb.commit()

    def test_4_confirm_sums(self, testdb):
        periods = self.pay_periods(testdb)
        assert periods['prev'].overall_sums == {
            'allocated': 750.0,
            'spent': 850.0,
            'income': 1000.0,
            'remaining': 150.0
        }
        assert periods['curr'].overall_sums == {
            'allocated': 2350.0,
            'spent': 2450.0,
            'income': 1400.0,
            'remaining': -1050.0
        }
        assert periods['next'].overall_sums == {
            'allocated': 1288.0,
            'spent': 1388.0,
            'income': 1400.0,
            'remaining': 12.0
        }
        assert periods['following'].overall_sums == {
            'allocated': 502.0,
            'spent': 602.0,
            'income': 1400.0,
            'remaining': 798.0
        }

    def test_5_pay_periods_table(self, base_url, selenium, testdb):
        periods = self.pay_periods(testdb)
        selenium.get(base_url + '/payperiods')
        table = selenium.find_element_by_id('pay-period-table')
        texts = self.tbody2textlist(table)
        elems = self.tbody2elemlist(table)
        assert texts == [
            [
                periods['prev'].start_date.strftime('%Y-%m-%d'),
                '$750.00',
                '$850.00',
                '$150.00'
            ],
            [
                periods['curr'].start_date.strftime('%Y-%m-%d') + ' (current)',
                '$2,350.00',
                '$2,450.00',
                '-$1,050.00'
            ],
            [
                periods['next'].start_date.strftime('%Y-%m-%d'),
                '$1,288.00',
                '$1,388.00',
                '$12.00'
            ],
            [
                periods['following'].start_date.strftime('%Y-%m-%d'),
                '$502.00',
                '$602.00',
                '$798.00'
            ]
        ]
        # test links
        links = [x[0].get_attribute('innerHTML') for x in elems]
        expected = []
        for k in ['prev', 'curr', 'next', 'following']:
            dstr = periods[k].start_date.strftime('%Y-%m-%d')
            s = '<a href="/payperiod/%s">%s</a>' % (dstr, dstr)
            if k == 'curr':
                s += ' <em>(current)</em>'
            expected.append(s)
        assert links == expected
        # test red text for negative dollar amounts
        assert elems[0][3].get_attribute('innerHTML') == '$150.00'
        assert elems[1][3].get_attribute('innerHTML') == '<span ' \
            'class="text-danger">-$1,050.00</span>'
        # test highlighted row for current period
        tbody = table.find_element_by_tag_name('tbody')
        trs = tbody.find_elements_by_tag_name('tr')
        assert trs[1].get_attribute('class') == 'info'

    def test_6_notification_panels(self, base_url, selenium, testdb):
        periods = self.pay_periods(testdb)
        selenium.get(base_url + '/payperiods')
        this_panel = selenium.find_element_by_id('panel-period-current')
        assert this_panel.get_attribute('class') == 'panel panel-red'
        assert this_panel.find_element_by_class_name('panel-heading').text\
            == '-$1,050.00\nRemaining this period'
        assert this_panel.find_element_by_tag_name('a').get_attribute(
            'href') == base_url + '/payperiod/' + periods[
            'curr'].start_date.strftime('%Y-%m-%d')
        assert this_panel.find_element_by_class_name('panel-footer')\
            .text == 'View ' + periods['curr'].start_date.strftime(
            '%Y-%m-%d') + ' Pay Period'
        next_panel = selenium.find_element_by_id('panel-period-next')
        assert next_panel.get_attribute('class') == 'panel panel-yellow'
        assert next_panel.find_element_by_class_name('panel-heading').text \
            == '$12.00\nRemaining next period'
        assert next_panel.find_element_by_tag_name('a').get_attribute(
            'href') == base_url + '/payperiod/' + periods[
            'next'].start_date.strftime('%Y-%m-%d')
        assert next_panel.find_element_by_class_name('panel-footer')\
            .text == 'View ' + periods['next'].start_date.strftime(
            '%Y-%m-%d') + ' Pay Period'
        following_panel = selenium.find_element_by_id('panel-period-following')
        assert following_panel.get_attribute('class') == 'panel panel-green'
        assert following_panel.find_element_by_class_name('panel-heading')\
            .text == '$798.00\nRemaining following period'
        assert following_panel.find_element_by_tag_name('a').get_attribute(
            'href') == base_url + '/payperiod/' + periods[
            'following'].start_date.strftime('%Y-%m-%d')
        assert following_panel.find_element_by_class_name('panel-footer')\
            .text == 'View ' + periods['following'].start_date.strftime(
            '%Y-%m-%d') + ' Pay Period'


@pytest.mark.acceptance
class DONOTTestPayPeriod(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        selenium.get(
            base_url + '/payperiod/' +
            PAY_PERIOD_START_DATE.strftime('%Y-%m-%d')
        )

    def test_heading(self, selenium, testdb):
        heading = selenium.find_element_by_class_name('navbar-brand')
        pp = BiweeklyPayPeriod(PAY_PERIOD_START_DATE, testdb)
        assert heading.text == '%s to %s Pay Period - BiweeklyBudget' % (
            pp.start_date.strftime('%Y-%m-%d'),
            pp.end_date.strftime('%Y-%m-%d')
        )

    def test_nav_menu(self, selenium):
        ul = selenium.find_element_by_id('side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_notifications(self, selenium):
        div = selenium.find_element_by_id('notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
class TestPayPeriodOtherPeriodInfo(AcceptanceHelper):

    def test_0_clean_db(self, testdb):
        # clean the database
        biweeklybudget.models.base.Base.metadata.reflect(engine)
        biweeklybudget.models.base.Base.metadata.drop_all(engine)
        biweeklybudget.models.base.Base.metadata.create_all(engine)

    def test_1_add_account(self, testdb):
        a = Account(
            description='First Bank Account',
            name='BankOne',
            ofx_cat_memo_to_name=True,
            ofxgetter_config_json='{"foo": "bar"}',
            vault_creds_path='secret/foo/bar/BankOne',
            acct_type=AcctType.Bank
        )
        testdb.add(a)
        a.set_balance(
            overall_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC),
            ledger=1.0,
            ledger_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC)
        )
        testdb.flush()
        testdb.commit()

    def test_2_add_budgets(self, testdb):
        testdb.add(Budget(
            name='1Income',
            is_periodic=True,
            description='1Income',
            starting_balance=1000.00,
            is_income=True
        ))
        testdb.add(Budget(
            name='2Periodic',
            is_periodic=True,
            description='2Periodic',
            starting_balance=500.00
        ))
        testdb.add(Budget(
            name='3Periodic',
            is_periodic=True,
            description='3Periodic',
            starting_balance=0.00
        ))
        testdb.flush()
        testdb.commit()

    def pay_periods(self, db):
        return {
            'prev': BiweeklyPayPeriod.period_for_date(
                (PAY_PERIOD_START_DATE - timedelta(days=2)), db),
            'curr': BiweeklyPayPeriod.period_for_date(
                PAY_PERIOD_START_DATE, db),
            'next': BiweeklyPayPeriod.period_for_date(
                (PAY_PERIOD_START_DATE + timedelta(days=15)), db),
            'following': BiweeklyPayPeriod.period_for_date(
                (PAY_PERIOD_START_DATE + timedelta(days=29)), db),
            'last': BiweeklyPayPeriod.period_for_date(
                (PAY_PERIOD_START_DATE + timedelta(days=43)), db)
        }

    def test_3_add_transactions(self, testdb):
        acct = testdb.query(Account).get(1)
        ibudget = testdb.query(Budget).get(1)
        e1budget = testdb.query(Budget).get(2)
        e2budget = testdb.query(Budget).get(3)
        periods = self.pay_periods(testdb)
        # previous pay period
        ppdate = periods['prev'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=100.00,
            budgeted_amount=100.00,
            description='prev income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=250.00,
            description='prev trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='prev trans 2',
            account=acct,
            budget=e1budget
        ))
        ppdate = periods['curr'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=1400.00,
            budgeted_amount=100.00,
            description='prev income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=1850.00,
            description='prev trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='prev trans 2',
            account=acct,
            budget=e1budget
        ))
        ppdate = periods['next'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=1400.00,
            budgeted_amount=100.00,
            description='prev income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=788.00,
            description='prev trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='prev trans 2',
            account=acct,
            budget=e1budget
        ))
        ppdate = periods['following'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=1400.00,
            budgeted_amount=100.00,
            description='prev income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=2.00,
            description='prev trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='prev trans 2',
            account=acct,
            budget=e1budget
        ))
        ppdate = periods['last'].start_date
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=1)),
            actual_amount=1400.00,
            budgeted_amount=100.00,
            description='last income',
            account=acct,
            budget=ibudget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=2)),
            actual_amount=2.00,
            description='last trans 1',
            account=acct,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=(ppdate + timedelta(days=3)),
            actual_amount=550.00,
            budgeted_amount=550.00,
            description='last trans 2',
            account=acct,
            budget=e1budget
        ))
        testdb.flush()
        testdb.commit()

    def test_4_confirm_sums(self, testdb):
        periods = self.pay_periods(testdb)
        assert periods['prev'].overall_sums == {
            'allocated': 750.0,
            'spent': 850.0,
            'income': 1000.0,
            'remaining': 150.0
        }
        assert periods['curr'].overall_sums == {
            'allocated': 2350.0,
            'spent': 2450.0,
            'income': 1400.0,
            'remaining': -1050.0
        }
        assert periods['next'].overall_sums == {
            'allocated': 1288.0,
            'spent': 1388.0,
            'income': 1400.0,
            'remaining': 12.0
        }
        assert periods['following'].overall_sums == {
            'allocated': 502.0,
            'spent': 602.0,
            'income': 1400.0,
            'remaining': 798.0
        }
        assert periods['last'].overall_sums == {
            'allocated': 552.0,
            'spent': 552.0,
            'income': 1400.0,
            'remaining': 848.0
        }

    def test_5_other_periods_table(self, base_url, selenium, testdb):
        periods = self.pay_periods(testdb)
        selenium.get(
            base_url + '/payperiod/' +
            PAY_PERIOD_START_DATE.strftime('%Y-%m-%d')
        )
        pp = BiweeklyPayPeriod(PAY_PERIOD_START_DATE, testdb)
        table = selenium.find_element_by_id('pay-period-table')
        assert self.thead2list(table) == [
            '%s (prev.)' % pp.previous.start_date.strftime('%Y-%m-%d'),
            '%s (curr.)' % pp.start_date.strftime('%Y-%m-%d'),
            '%s (next)' % pp.next.start_date.strftime('%Y-%m-%d'),
            '%s' % pp.next.next.start_date.strftime('%Y-%m-%d'),
            '%s' % pp.next.next.next.start_date.strftime('%Y-%m-%d')
        ]
        assert self.tbody2textlist(table) == [[
            '$150.00',
            '-$1,050.00',
            '$12.00',
            '$798.00',
            '$848.00'
        ]]
        contents = [
            x.get_attribute('innerHTML') for x in self.thead2elemlist(table)
        ]
        assert contents == [
            '<a href="/payperiod/{d}">{d} <em>(prev.)</em></a>'.format(
                d=pp.previous.start_date.strftime('%Y-%m-%d')),
            '{d} <em>(curr.)</em>'.format(
                d=pp.start_date.strftime('%Y-%m-%d')),
            '<a href="/payperiod/{d}">{d} <em>(next)</em></a>'.format(
                d=pp.next.start_date.strftime('%Y-%m-%d')),
            '<a href="/payperiod/{d}">{d}</a>'.format(
                d=pp.next.next.start_date.strftime('%Y-%m-%d')),
            '<a href="/payperiod/{d}">{d}</a>'.format(
                d=pp.next.next.next.start_date.strftime('%Y-%m-%d'))
        ]
