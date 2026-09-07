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

Create a Transaction via the biweeklybudget HTTP API.

This is the proof-of-concept console script called for by GitHub issue #322: a
worked example of driving ``POST /forms/transaction`` from outside the
application, taking inputs similar to the Add Transaction form and accepting
Accounts and Budgets by name as well as by ID.

It deliberately speaks HTTP rather than touching the database. Talking to the
database directly would be simpler and would prove nothing; the point is that
the published API is usable by external tooling. For the same reason this
module imports neither :py:mod:`biweeklybudget.db` nor
:py:mod:`biweeklybudget.settings`, so the script runs anywhere ``requests`` is
installed and needs no settings module of its own.

Note that ``-b``/``--budget`` splits its value on the first ``=``, so a Budget
whose *name* contains an equals sign must be given by ID instead.
"""

import argparse
import json
import logging
import os
import sys
from datetime import date

import requests

from biweeklybudget.cliutils import set_log_debug, set_log_info

logger = logging.getLogger(__name__)

#: Base URL used when neither ``--url`` nor
#: :py:const:`~biweeklybudget.addtrans.URL_ENV_VAR` is set.
DEFAULT_URL = 'http://127.0.0.1:8080'

#: Environment variable consulted for the base URL when ``--url`` is absent.
URL_ENV_VAR = 'BIWEEKLYBUDGET_URL'

#: Seconds to wait for the application to respond.
REQUEST_TIMEOUT = 30


def base_url_for(url_arg):
    """
    Determine the base URL of the application to talk to: the ``--url``
    argument if given, else the
    :py:const:`~biweeklybudget.addtrans.URL_ENV_VAR` environment variable,
    else :py:const:`~biweeklybudget.addtrans.DEFAULT_URL`.

    :param url_arg: value of the ``--url`` argument, or None
    :type url_arg: str
    :return: base URL, with any trailing slash removed
    :rtype: str
    """
    for candidate in [url_arg, os.environ.get(URL_ENV_VAR, None)]:
        if candidate is not None and candidate.strip() != '':
            return candidate.strip().rstrip('/')
    return DEFAULT_URL


def parse_budget_args(parser, budget_args, amount):
    """
    Turn the repeated ``-b``/``--budget`` arguments into the ``budgets``
    mapping the API expects.

    Each argument is either ``BUDGET`` or ``BUDGET=AMOUNT``, where ``BUDGET``
    is a Budget name or ID. Exactly one budget given without an amount means
    "all of it", which is unambiguous; more than one requires every budget to
    carry its own amount, since there is no sensible way to split an amount
    the user did not divide up.

    :param parser: the argument parser, used to report usage errors
    :type parser: argparse.ArgumentParser
    :param budget_args: the raw ``--budget`` argument values
    :type budget_args: list
    :param amount: the transaction amount, as supplied
    :type amount: str
    :return: hash of budget name or ID to amount, both as strings
    :rtype: dict
    """
    specs = []
    for arg in budget_args:
        name, sep, amt = arg.partition('=')
        specs.append((name.strip(), amt.strip() if sep else None))
    if len(specs) == 1 and specs[0][1] is None:
        specs = [(specs[0][0], amount)]
    res = {}
    for name, amt in specs:
        if name == '':
            parser.error('budget name or ID cannot be empty')
        if amt is None:
            parser.error(
                'when more than one --budget is given, each must specify its '
                'own amount as BUDGET=AMOUNT; "%s" does not' % name
            )
        if name in res:
            parser.error('--budget %s specified more than once' % name)
        res[name] = amt
    return res


def build_payload(args):
    """
    Build the JSON body to POST from parsed arguments.

    Amounts are passed through exactly as the user typed them. The application
    normalizes currency formatting server-side and accepts ``123.45``,
    ``$1,234.56`` and ``1,234.56`` alike; parsing them here would create a
    second, subtly different definition of what an amount is.

    :param args: parsed command line arguments
    :type args: argparse.Namespace
    :return: the request body
    :rtype: dict
    """
    payload = {
        'date': args.date,
        'amount': args.amount,
        'description': args.description,
        'notes': args.notes,
        'account': args.account,
        'budgets': args.budgets
    }
    if args.sales_tax is not None:
        payload['sales_tax'] = args.sales_tax
    if args.credit_payment_acct is not None:
        payload['credit_payment_acct'] = args.credit_payment_acct
    if args.no_budget_impact:
        payload['no_budget_impact'] = True
    return payload


def post_transaction(base_url, payload):
    """
    POST the transaction and report the outcome on stdout or stderr.

    Note that the application answers a *validation failure* with HTTP 200 and
    ``"success": false`` in the body, so the status code alone never says
    whether the transaction was created.

    :param base_url: base URL of the application
    :type base_url: str
    :param payload: the request body, from :py:func:`~.build_payload`
    :type payload: dict
    :return: process exit status; 0 on success
    :rtype: int
    """
    url = base_url + '/forms/transaction'
    logger.debug('POST %s: %s', url, payload)
    try:
        res = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as ex:
        sys.stderr.write(
            'ERROR: could not reach biweeklybudget at %s: %s\n' % (url, ex)
        )
        return 1
    logger.debug('HTTP %s: %s', res.status_code, res.text)
    if res.status_code != 200:
        sys.stderr.write(
            'ERROR: %s returned HTTP %s: %s\n' % (
                url, res.status_code, res.text[:500]
            )
        )
        return 1
    try:
        response = res.json()
    except ValueError:
        sys.stderr.write(
            'ERROR: %s returned a non-JSON response: %s\n' % (
                url, res.text[:500]
            )
        )
        return 1
    if response.get('success', False) is True:
        sys.stdout.write('Created Transaction %s\n' % response.get('trans_id'))
        if response.get('success_message', None):
            sys.stdout.write('%s\n' % response['success_message'])
        return 0
    errors = response.get('errors', None)
    if errors:
        sys.stderr.write('ERROR: biweeklybudget rejected the transaction:\n')
        for field in sorted(errors.keys()):
            for message in errors[field]:
                sys.stderr.write('  %s: %s\n' % (field, message))
        return 1
    sys.stderr.write(
        'ERROR: %s\n' % response.get('error_message', response)
    )
    return 1


def parse_args(argv=None):
    """
    Parse command line arguments.

    :param argv: arguments to parse; defaults to ``sys.argv[1:]``
    :type argv: list
    :return: parsed arguments, with ``budgets`` and ``base_url`` resolved
    :rtype: argparse.Namespace
    """
    p = argparse.ArgumentParser(
        description='Create a Transaction via the biweeklybudget HTTP API. '
                    'Accounts and Budgets may be given by name or by ID.'
    )
    p.add_argument('account', metavar='ACCOUNT',
                   help='Account name or ID to book the transaction against')
    p.add_argument('amount', metavar='AMOUNT',
                   help='transaction amount; "123.45", "$1,234.56" and '
                        '"1,234.56" are all accepted')
    p.add_argument('description', metavar='DESCRIPTION',
                   help='transaction description')
    p.add_argument('-b', '--budget', dest='budget', action='append',
                   required=True, metavar='BUDGET[=AMOUNT]',
                   help='Budget name or ID, optionally with the amount to '
                        'allocate to it. May be given more than once, in '
                        'which case every one must specify its amount. With '
                        'exactly one, the whole transaction amount is used.')
    p.add_argument('-d', '--date', dest='date', default=None,
                   metavar='YYYY-MM-DD',
                   help='transaction date; defaults to today')
    p.add_argument('-n', '--notes', dest='notes', default='',
                   help='free-text notes for the transaction')
    p.add_argument('-t', '--sales-tax', dest='sales_tax', default=None,
                   metavar='AMOUNT', help='sales tax portion of the amount')
    p.add_argument('-p', '--credit-payment-acct', dest='credit_payment_acct',
                   default=None, metavar='ACCOUNT',
                   help='name or ID of the credit Account that this '
                        'transaction is a payment for')
    p.add_argument('--no-budget-impact', dest='no_budget_impact',
                   action='store_true', default=False,
                   help='mark the transaction as not counting against its '
                        'budget')
    p.add_argument('-U', '--url', dest='url', default=None, metavar='URL',
                   help='base URL of the biweeklybudget application; '
                        'defaults to the %s environment variable, else '
                        '%s' % (URL_ENV_VAR, DEFAULT_URL))
    p.add_argument('--dry-run', dest='dry_run', action='store_true',
                   default=False,
                   help='print the JSON that would be posted, and exit '
                        'without posting it')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level '
                        'output.')
    args = p.parse_args(argv)
    if args.date is None:
        args.date = date.today().strftime('%Y-%m-%d')
    args.budgets = parse_budget_args(p, args.budget, args.amount)
    args.base_url = base_url_for(args.url)
    return args


def main():
    global logger
    format = "[%(asctime)s %(levelname)s] %(message)s"
    logging.basicConfig(level=logging.WARNING, format=format)
    logger = logging.getLogger()

    args = parse_args()

    # set logging level
    if args.verbose > 1:
        set_log_debug(logger)
    elif args.verbose == 1:
        set_log_info(logger)

    payload = build_payload(args)
    if args.dry_run:
        sys.stdout.write(
            '%s\n' % json.dumps(payload, indent=4, sort_keys=True)
        )
        raise SystemExit(0)
    raise SystemExit(post_transaction(args.base_url, payload))


if __name__ == "__main__":
    main()
