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

Configuring Accounts for Downloading with ofxclient
---------------------------------------------------

1. Use the ``ofxclient`` CLI to configure and test your account.
2. Put your creds in Vault.
3. Migrate ~/ofxclient.ini to JSON, add it to your :py:class:`~biweeklybudget.models.account.Account`.

Configuring Accounts for Downloading with Selenium
--------------------------------------------------

Write a class; how to provide config.
