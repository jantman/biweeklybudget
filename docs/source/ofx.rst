.. _ofx:

OFX Transaction Downloading
===========================

biweeklybudget has the ability to download OFX transaction data from your
financial institutions, either manually or automatically (via an external
command scheduler such as ``cron``).

There are two overall methods of downloading transaction data; for banks that
support the `OFX protocol <http://ofx.net/>`_, statement data can be downloaded
using HTTP only, via the `ofxclient <https://github.com/captin411/ofxclient>`_ project (note our requirements file
specifies the upstream of `PR #37 <https://github.com/captin411/ofxclient/pull/37>`_,
which includes a fix for Discover credit cards). For banks that do not support the
OFX protocol and require you to use their website to download OFX format statements,
biweeklybudget provides a base :py:class:`~biweeklybudget.screenscraper.ScreenScraper`
class that can be used to develop a `selenium <http://selenium-python.readthedocs.io/>`_-based
tool to automate logging in to your bank's site and downloading the OFX file.

In order to use either of these methods, you must have an instance of `Hashicorp Vault <https://www.vaultproject.io/>`_
running and have your login credentials stored in it.

Important Note on Transaction Downloading
-----------------------------------------

biweeklybudget includes support for automatically downloading transaction data
from your bank. Credentials are stored in an instance of `Hashicorp Vault <https://www.vaultproject.io/>`_,
as that is a project the author has familiarity with, and was chosen as the most
secure way of storing and retrieving secrets non-interactively. Please keep in mind
that it is your decision and your decision alone how secure your banking credentials
are kept. What is considered acceptable to the author of this program may not be acceptably
secure for others; it is your sole responsibility to understand the security and privacy
implications of this program as well as Vault, and to understand the risks of storing
your banking credentials in this way.

Also note that biweeklybudget includes a base class (:py:class:`~biweeklybudget.screenscraper.ScreenScraper`)
intended to simplify developing `selenium <http://selenium-python.readthedocs.io/>`_-based
browser automation to log in to financial institution websites and download your transactions.
Many banks and other financial institutions have terms of service that
*explicitly forbid automated or programmatic use of their websites*. As such, it is up to you
as the user of this software to determine your bank's policy and abide by it. I provide a
base class to help in writing automated download tooling if your institution allows it, but
I cannot and will not distribute institution-specific download tooling.

ofxgetter entrypoint
--------------------

This package provides an ``ofxgetter`` command line entrypoint that can be used to
download OFX statements for one or all Accounts that are appropriately configured. The
script used for this provides exit codes and logging suitable for use via ``cron`` (
it exits non-zero if any accounts failed, and unless options are provided to increase
verbosity, only outputs the number of accounts successfully downloaded as well as any
errors).

Vault Setup
-----------

Configuring and running Vault is outside the scope of this document. Once you have
a Vault installation running and appropriately secured (you shouldn't be using the
dev server unless you want to lose all your data every time you reboot) and have given
biweeklybudget access to a valid token stored in a file somewhere, you'll need to ensure
that your username and password data is stored in Vault in the proper format (``username``
and ``password`` keys). If you happen to use `LastPass <https://www.lastpass.com/>`_
to store your passwords, you may find my `lastpass2vault.py <https://github.com/jantman/misc-scripts/blob/master/lastpass2vault.py>`_
helpful; run it as ``./lastpass2vault.py -vv -f PATH_TO_VAULT_TOKEN LASTPASS_USERNAME`` and
it will copy all of your credentials from LastPass to Vault, preserving the folder structure.

.. _ofx.ofxclient:

Configuring Accounts for Downloading with ofxclient
---------------------------------------------------

1. Use the ``ofxclient`` CLI to configure and test your account.
2. Put your creds in Vault.
3. Migrate ~/ofxclient.ini to JSON, add it to your :py:class:`~biweeklybudget.models.account.Account`.

A working configuration for a Bank account might look something like this:

.. code-block:: json

    {
        "routing_number": "012345678",
        "account_type": "CHECKING",
        "description": "Checking",
        "number": "111222333",
        "local_id": "f0a14074d33cdf83b4a099bc322dbe2fe19680ca1719425b33de5022",
        "institution": {
            "client_args": {
                "app_version": "2200",
                "app_id": "QWIN",
                "ofx_version": "103",
                "id": "f87217350cc341e2ba7407cf99dcdede"
            },
            "description": "MyBank",
            "url": "https://ofx.MyBank.com",
            "local_id": "e51fb78f88580a1c2e3bb65bd59495384388abda8796c9bf06dcf",
            "broker_id": "",
            "org": "ORG",
            "id": "98765"
        }
    }

.. _ofx.selenium:

Configuring Accounts for Downloading with Selenium
--------------------------------------------------

In your `customization package <_getting_started.customization>`, subclass
:py:class:`~biweeklybudget.screenscraper.ScreenScraper`. Override the constructor
to take whatever keyword arguments are required, and add those to your account's
``ofxgetter_config_json`` as shown below. :py:class:~biweeklybudget.ofxgetter.OfxGetter`
will instantiate the class passing it the specified keyword arguments in addition to
``username``, ``password`` and ``savedir`` keyword arguments. ``savedir`` is the
directory under :py:const:`~biweeklybudget.settings_example.STATEMENTS_SAVE_PATH` where the account's
OFX statements should be saved. After instantiating the class, ``ofxgetter`` will
call the class's ``run()`` method with no arguments, and expect to receive an OFX
statement string back.

If cookies are a concern, be aware that saving and loading cookies is
`broken in PhantomJS 2.x <https://github.com/ariya/phantomjs/issues/13115>`_.
If you need to persist cookies across sessions, look into the
:py:class:`~biweeklybudget.screenscraper.ScreenScraper` class'
:py:meth:`~biweeklybudget.screenscraper.ScreenScraper.load_cookies` and
:py:meth:`~biweeklybudget.screenscraper.ScreenScraper.save_cookies` methods.

.. code-block:: json

    {
        "class_name": "MyScraper",
        "module_name": "budget_customization.myscraper",
        "institution": {},
        "kwargs": {
            "acct_num": "1234"
        }
    }

Here's a simple, contrived example of such a class:

.. code-block:: python

    import logging
    import time
    import codecs
    from datetime import datetime

    from selenium.common.exceptions import NoSuchElementException

    from biweeklybudget.screenscraper import ScreenScraper

    logger = logging.getLogger(__name__)

    # suppress selenium logging
    selenium_log = logging.getLogger("selenium")
    selenium_log.setLevel(logging.WARNING)
    selenium_log.propagate = True


    class MyScraper(ScreenScraper):

        def __init__(self, username, password, savedir='./',
                     acct_num=None, screenshot=False):
            """
            :param username: username
            :type username: str
            :param password: password
            :type password: str
            :param savedir: directory to save OFX in
            :type savedir: str
            :param acct_num: last 4 of account number, as shown on homepage
            :type acct_num: str
            """
            super(MyScraper, self).__init__(
                savedir=savedir, screenshot=screenshot
            )
            self.browser = self.get_browser('phantomjs')
            self.username = username
            self.password = password
            self.acct_num = acct_num

        def run(self):
            """ download the transactions, return file path on disk """
            logger.debug("running, username={u}".format(u=self.username))
            logger.info('Logging in...')
            try:
                self.do_login(self.username, self.password)
                logger.info('Logged in; sleeping 2s to stabilize')
                time.sleep(2)
                self.do_screenshot()
                self.select_account()
                act = self.get_account_activity()
            except Exception:
                self.error_screenshot()
                raise
            return act

        def do_login(self, username, password):
            self.get_page('http://example.com')
            raise NotImplementedError("login to your bank here")

        def select_account(self):
            self.get_page('http://example.com')
            logger.debug('Finding account link...')
            link = self.browser.find_element_by_xpath(
                '//a[contains(text(), "%s")]' % self.acct_num
            )
            logger.debug('Clicking account link: %s', link)
            link.click()
            self.wait_for_ajax_load()
            self.do_screenshot()

        def get_account_activity(self):
            # some bank-specific stuff here, then we POST to get OFX
            post_list = self.xhr_post_urlencoded(
                post_url, post_data, headers=post_headers
            )
            if not post_list.startswith('OFXHEADER'):
                self.error_screenshot()
                with codecs.open('result', 'w', 'utf-8') as fh:
                    fh.write(post_list)
                raise SystemExit("Got non-OFX response")
            return post_list
