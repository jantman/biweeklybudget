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
import re
import json
from decimal import Decimal
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.dbsetting import DBSetting
from biweeklybudget.models.account import Account, NoInterestChargedError
from biweeklybudget.models.ofx_statement import OFXStatement
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.utils import dtnow
from selenium.webdriver.support.ui import Select


def get_payoff_forms(selenium):
    form_ids = [
        s.get_attribute('id')
        for s in selenium.find_elements_by_tag_name('form')
    ]
    res = {}
    for f_type in ['increase', 'onetime']:
        vals = {}
        id_re = re.compile(r'^payoff_' + f_type + r'_frm_(\d+)$')
        for frmid in form_ids:
            m = id_re.match(frmid)
            if m is None:
                continue
            _id = int(m.group(1))

            vals[_id] = {
                'enabled': selenium.find_element_by_id(
                    'payoff_%s_frm_%s_enable' % (f_type, _id)
                ).is_selected(),
                'date': selenium.find_element_by_id(
                    'payoff_%s_frm_%s_date' % (f_type, _id)
                ).get_attribute('value'),
                'amount': selenium.find_element_by_id(
                    'payoff_%s_frm_%s_amt' % (f_type, _id)
                ).get_attribute('value')
            }
        res[f_type] = vals
    return res


def set_payoff_form(selenium, f_type, idx, enabled, date_s, amt):
    is_enabled = selenium.find_element_by_id(
        'payoff_%s_frm_%s_enable' % (f_type, idx)).is_selected()
    if is_enabled != enabled:
        selenium.find_element_by_id(
            'payoff_%s_frm_%s_enable' % (f_type, idx)).click()
        assert selenium.find_element_by_id(
            'payoff_%s_frm_%s_enable' % (f_type, idx)).is_selected() == enabled
    selenium.find_element_by_id(
        'payoff_%s_frm_%s_date' % (f_type, idx)).clear()
    selenium.find_element_by_id(
        'payoff_%s_frm_%s_date' % (f_type, idx)).send_keys(date_s)
    selenium.find_element_by_id(
        'payoff_%s_frm_%s_amt' % (f_type, idx)).clear()
    selenium.find_element_by_id(
        'payoff_%s_frm_%s_amt' % (f_type, idx)).send_keys(amt)


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestCreditPayoffsNoInterest(AcceptanceHelper):

    def test_01_heading(self, selenium, base_url):
        self.baseurl = base_url
        self.get(selenium, base_url + '/accounts/credit-payoff')
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'ERROR - Credit Card Payoffs - BiweeklyBudget'

    def test_02_nav_menu(self, selenium, base_url):
        self.baseurl = base_url
        self.get(selenium, base_url + '/accounts/credit-payoff')
        ul = selenium.find_element_by_id('side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_03_notifications(self, selenium, base_url):
        self.baseurl = base_url
        self.get(selenium, base_url + '/accounts/credit-payoff')
        div = selenium.find_element_by_id('notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'

    def test_04_danger_message(self, selenium, base_url):
        self.baseurl = base_url
        self.get(selenium, base_url + '/accounts/credit-payoff')
        div = selenium.find_element_by_id('account-interest-error-message')
        assert div is not None
        assert 'alert-danger' in div.get_attribute('class')
        text = div.get_attribute('innerHTML')
        assert 'Account Interest Error' in text
        assert 'in which case you must <a href="#" onclick="creditPayoffError' \
               'Modal(4)">manually input the interest charge ' \
               'from your last statement</a>' in text

    def test_05_verify_db(self, testdb):
        acct = testdb.query(Account).get(4)
        with pytest.raises(NoInterestChargedError):
            assert isinstance(acct.last_interest_charge, Decimal)

    def test_06_add_interest(self, selenium, base_url):
        self.baseurl = base_url
        self.get(selenium, base_url + '/accounts/credit-payoff')
        link = selenium.find_element_by_xpath(
            '//a[text()="manually input the interest charge from your '
            'last statement"]'
        )
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add Manual Interest Charge for Account 4'
        frm_id = selenium.find_element_by_id('payoff_acct_frm_id')
        frm_filename = selenium.find_element_by_id(
            'payoff_acct_frm_statement_filename'
        )
        frm_int_amt = selenium.find_element_by_id(
            'payoff_acct_frm_interest_amt'
        )
        assert frm_id.get_attribute('value') == '4'
        fname = Select(frm_filename)
        # find the options
        opts = []
        for o in fname.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['/stmt/CreditTwo/0', '2017-07-26 (-$5,498.65)']
        ]
        fname.select_by_value('/stmt/CreditTwo/0')
        frm_int_amt.clear()
        frm_int_amt.send_keys('123.45')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved OFXTransaction with ' \
                                 'FITID 20170728062444-MANUAL-CCPAYOFF' \
                                 ' in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'Credit Card Payoffs - BiweeklyBudget'

    def test_07_verify_db(self, testdb):
        acct = testdb.query(Account).get(4)
        assert acct.last_interest_charge == Decimal('-123.45')
        stmt = testdb.query(OFXStatement).get(7)
        ofxtxn = testdb.query(OFXTransaction).get(
            (4, '20170728062444-MANUAL-CCPAYOFF')
        )
        assert ofxtxn.account == acct
        assert ofxtxn.statement == stmt
        assert ofxtxn.fitid == '20170728062444-MANUAL-CCPAYOFF'
        assert ofxtxn.trans_type == 'debit'
        assert ofxtxn.date_posted == stmt.as_of
        assert ofxtxn.amount == Decimal('123.45')
        assert ofxtxn.name == 'Interest Charged - MANUALLY ENTERED'
        assert ofxtxn.memo is None
        assert ofxtxn.sic is None
        assert ofxtxn.mcc is None
        assert ofxtxn.checknum is None
        assert ofxtxn.description is None
        assert ofxtxn.notes is None
        assert ofxtxn.is_interest_charge is True


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'testflask')
@pytest.mark.incremental
class TestNoSettings(AcceptanceHelper):

    def test_000_setup_interest_charge_in_db(self, testdb):
        acct = testdb.query(Account).get(4)
        stmt = testdb.query(OFXStatement).get(7)
        txn = OFXTransaction(
            account=acct,
            statement=stmt,
            fitid='%s-MANUAL-CCPAYOFF' % dtnow().strftime('%Y%m%d%H%M%S'),
            trans_type='debit',
            date_posted=stmt.as_of,
            amount=Decimal('46.9061'),
            name='Interest Charged - MANUALLY ENTERED',
            is_interest_charge=True
        )
        testdb.add(txn)
        testdb.commit()

    def test_00_verify_db(self, testdb):
        b = testdb.query(DBSetting).get('credit-payoff')
        assert b is None

    def test_01_no_config(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        assert selenium.find_element_by_id(
            'payoff_frm_min_pymt').get_attribute('value') == '144.98'
        form_ids = [
            s.get_attribute('id')
            for s in selenium.find_elements_by_tag_name('form')
        ]
        assert sorted(form_ids) == [
            'min_payment_frm',
            'payoff_increase_frm_1',
            'payoff_onetime_frm_1'
        ]
        assert get_payoff_forms(selenium) == {
            'increase': {
                1: {
                    'enabled': False,
                    'date': '',
                    'amount': ''
                }
            },
            'onetime': {
                1: {
                    'enabled': False,
                    'date': '',
                    'amount': ''
                }
            }
        }

    def test_01_highest_balance_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id('table_HighestBalanceFirstMethod')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$35.00',
                '2.3 years', '$963.00', '$10.94'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$109.97',
                '4.6 years', '$6,956.35', '$1,457.70'
            ],
            ['Totals', '$144.97', '4.6 years', '$7,919.34', '$1,468.63']
        ]

    def test_02_highest_interest_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id(
            'table_HighestInterestRateFirstMethod'
        )
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$35.00',
                '2.3 years', '$963.00', '$10.94'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$109.97',
                '4.6 years', '$6,956.35', '$1,457.70'
            ],
            ['Totals', '$144.97', '4.6 years', '$7,919.34', '$1,468.63']
        ]

    def test_03_lowest_balance_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id('table_LowestBalanceFirstMethod')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$35.00',
                '1.8 years', '$960.92', '$8.86'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$109.97',
                '4.7 years', '$6,988.24', '$1,489.59'
            ],
            ['Totals', '$144.97', '4.7 years', '$7,949.15', '$1,498.44']
        ]

    def test_04_lowest_interest_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id(
            'table_LowestInterestRateFirstMethod'
        )
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$35.00',
                '1.8 years', '$960.92', '$8.86'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$109.97',
                '4.7 years', '$6,988.24', '$1,489.59'
            ],
            ['Totals', '$144.97', '4.7 years', '$7,949.15', '$1,498.44']
        ]

    def test_05_min_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id('table_MinPaymentMethod')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$35.00',
                '2.3 years', '$963.00', '$10.94'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$109.97',
                '13.5 years', '$8,664.86', '$3,166.21'
            ],
            ['Totals', '$144.97', '13.5 years', '$9,627.86', '$3,177.15']
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestSettings(AcceptanceHelper):

    def test_000_setup_interest_charge_in_db(self, testdb):
        acct = testdb.query(Account).get(4)
        stmt = testdb.query(OFXStatement).get(7)
        txn = OFXTransaction(
            account=acct,
            statement=stmt,
            fitid='%s-MANUAL-CCPAYOFF' % dtnow().strftime('%Y%m%d%H%M%S'),
            trans_type='debit',
            date_posted=stmt.as_of,
            amount=Decimal('46.9061'),
            name='Interest Charged - MANUALLY ENTERED',
            is_interest_charge=True
        )
        testdb.add(txn)
        testdb.commit()

    def test_00_verify_db(self, testdb):
        b = testdb.query(DBSetting).get('credit-payoff')
        assert b is None

    def test_01_no_config(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        form_ids = [
            s.get_attribute('id')
            for s in selenium.find_elements_by_tag_name('form')
        ]
        assert sorted(form_ids) == [
            'min_payment_frm',
            'payoff_increase_frm_1',
            'payoff_onetime_frm_1'
        ]
        assert get_payoff_forms(selenium) == {
            'increase': {
                1: {
                    'enabled': False,
                    'date': '',
                    'amount': ''
                }
            },
            'onetime': {
                1: {
                    'enabled': False,
                    'date': '',
                    'amount': ''
                }
            }
        }

    def test_02_input_and_save(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        assert 'disabled' in selenium.find_element_by_id(
            'btn_recalc_payoffs').get_attribute('class')
        set_payoff_form(selenium, 'increase', 1, True, '2017-05-14', '160.23')
        assert 'disabled' not in selenium.find_element_by_id(
            'btn_recalc_payoffs').get_attribute('class')
        selenium.find_element_by_link_text('(add another increase)').click()
        set_payoff_form(selenium, 'increase', 2, False, '2017-06-27', '-56.78')
        set_payoff_form(selenium, 'onetime', 1, False, '2017-07-21', '98.76')
        selenium.find_element_by_link_text(
            '(add another one-time additional payment)').click()
        set_payoff_form(selenium, 'onetime', 2, True, '2017-07-04', '54.32')
        selenium.find_element_by_id('btn_recalc_payoffs').click()
        assert len(selenium.find_elements_by_class_name('formfeedback')) == 0

    def test_03_verify_db(self, testdb):
        b = testdb.query(DBSetting).get('credit-payoff')
        assert b is not None
        assert b.value == json.dumps({
            'increases': [
                {
                    'enabled': True,
                    'date': '2017-05-14',
                    'amount': '160.23'
                },
                {
                    'enabled': False,
                    'date': '2017-06-27',
                    'amount': '-56.78'
                }
            ],
            'onetimes': [
                {
                    'enabled': True,
                    'date': '2017-07-04',
                    'amount': '54.32'
                },
                {
                    'enabled': False,
                    'date': '2017-07-21',
                    'amount': '98.76'
                }
            ]
        }, sort_keys=True)

    def test_04_form_fill(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        form_ids = [
            s.get_attribute('id')
            for s in selenium.find_elements_by_tag_name('form')
        ]
        assert sorted(form_ids) == [
            'min_payment_frm',
            'payoff_increase_frm_1',
            'payoff_increase_frm_2',
            'payoff_onetime_frm_1',
            'payoff_onetime_frm_2'
        ]
        assert get_payoff_forms(selenium) == {
            'increase': {
                1: {
                    'enabled': True,
                    'date': '2017-05-14',
                    'amount': '160.23'
                },
                2: {
                    'enabled': False,
                    'date': '2017-06-27',
                    'amount': '-56.78'
                }
            },
            'onetime': {
                1: {
                    'enabled': True,
                    'date': '2017-07-04',
                    'amount': '54.32'
                },
                2: {
                    'enabled': False,
                    'date': '2017-07-21',
                    'amount': '98.76'
                }
            }
        }

    def test_05_highest_balance_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id('table_HighestBalanceFirstMethod')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$35.00',
                '2.3 years', '$963.00', '$10.94'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$179.55',
                '4.0 years', '$6,734.42', '$1,235.77'
            ],
            ['Totals', '$214.55', '4.0 years', '$7,697.42', '$1,246.71']
        ]

    def test_06_highest_interest_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id(
            'table_HighestInterestRateFirstMethod'
        )
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$35.00',
                '2.3 years', '$963.00', '$10.94'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$179.55',
                '4.0 years', '$6,734.42', '$1,235.77'
            ],
            ['Totals', '$214.55', '4.0 years', '$7,697.42', '$1,246.71']
        ]

    def test_07_lowest_balance_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id('table_LowestBalanceFirstMethod')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$104.58',
                '1.3 years', '$958.10', '$6.04'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$109.97',
                '4.1 years', '$6,809.61', '$1,310.96'
            ],
            ['Totals', '$214.55', '4.1 years', '$7,767.71', '$1,317.00']
        ]

    def test_08_lowest_interest_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id(
            'table_LowestInterestRateFirstMethod'
        )
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$104.58',
                '1.3 years', '$958.10', '$6.04'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$109.97',
                '4.1 years', '$6,809.61', '$1,310.96'
            ],
            ['Totals', '$214.55', '4.1 years', '$7,767.71', '$1,317.00']
        ]

    def test_09_min_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id('table_MinPaymentMethod')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'CreditOne (3) ($952.06 @ 1.00%)', '$35.00',
                '2.3 years', '$963.00', '$10.94'
            ],
            [
                'CreditTwo (4) ($5,498.65 @ 10.00%)', '$109.97',
                '13.5 years', '$8,664.86', '$3,166.21'
            ],
            ['Totals', '$144.97', '13.5 years', '$9,627.86', '$3,177.15']
        ]

    def test_10_input_and_save_remove_lines(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        selenium.find_element_by_id('rm_increase_2_link').click()
        selenium.find_element_by_id('rm_onetime_1_link').click()
        selenium.find_element_by_id('btn_recalc_payoffs').click()
        assert len(selenium.find_elements_by_class_name('formfeedback')) == 0

    def test_11_verify_db(self, testdb):
        b = testdb.query(DBSetting).get('credit-payoff')
        assert b is not None
        assert b.value == json.dumps({
            'increases': [
                {
                    'enabled': True,
                    'date': '2017-05-14',
                    'amount': '160.23'
                }
            ],
            'onetimes': [
                {
                    'enabled': False,
                    'date': '2017-07-21',
                    'amount': '98.76'
                }
            ]
        }, sort_keys=True)
