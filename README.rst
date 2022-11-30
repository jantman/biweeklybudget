biweeklybudget
==============

.. image:: https://github.com/jantman/biweeklybudget/actions/workflows/run-tox-suite.yml/badge.svg
   :target: https://github.com/jantman/biweeklybudget/actions/workflows/run-tox-suite.yml
   :alt: GitHub Actions build for master branch

.. image:: https://codecov.io/github/jantman/biweeklybudget/coverage.svg?branch=master
   :target: https://codecov.io/github/jantman/biweeklybudget?branch=master
   :alt: coverage report for master branch

.. image:: https://readthedocs.org/projects/biweeklybudget/badge/?version=latest
   :target: https://readthedocs.org/projects/biweeklybudget/?badge=latest
   :alt: sphinx documentation for latest release

.. image:: http://www.repostatus.org/badges/latest/active.svg
   :alt: Project Status: Active – The project has reached a stable, usable state and is being actively developed.
   :target: http://www.repostatus.org/#active

Responsive Flask/SQLAlchemy personal finance app, specifically for biweekly budgeting.

**For full documentation**, see `http://biweeklybudget.readthedocs.io/en/latest/ <http://biweeklybudget.readthedocs.io/en/latest/>`_

**For screenshots**, see `<http://biweeklybudget.readthedocs.io/en/latest/screenshots.html>`_

Overview
--------

biweeklybudget is a responsive (mobile-friendly) Flask/SQLAlchemy personal finance application, specifically
targeted at budgeting on a biweekly basis. This is a personal project of mine, and really only intended for my
personal use. If you find it helpful, great! But this is provided as-is; I'll happily accept pull requests if they
don't mess things up for me, but I don't intend on working any feature requests or bug reports at this time. Sorry.

The main motivation for writing this is that I get paid every other Friday, and have for almost all of my professional
life. I also essentially live paycheck-to-paycheck; what savings I have is earmarked for specific purposes, so I budget
in periods identical to my pay periods. No existing financial software that I know of handles this, and many of them
have thousands of Google results of people asking for it; almost everything existing budgets on calendar months. I spent
many years using Google Sheets and a handful of scripts to template out budgets and reconcile transactions, but I decided
it's time to just bite the bullet and write something that isn't a pain.

**Intended Audience:** This is decidedly not an end-user application. You should be familiar with Python/Flask/MySQL. If
you're going to use the OFX-baseed automatic transaction download functionality (as opposed to Plaid), you should be
familiar with `Hashicorp Vault <https://www.vaultproject.io/>`_
and how to run a reasonably secure installation of it. I personally don't recommend running this on anything other than
your own computer that you physically control, given the sensitivity of the information. I also don't recommend making the
application available to anything other than localhost, but if you do, you need to be aware of the security implications. This
application is **not** designed to be accessible in any way to anyone other than authorized users (i.e. if you just serve it
over the web, someone *will* get your account numbers, or worse).

*Note:* Any potential users outside of the US should see the documentation section on
`Currency Formatting and Localization <http://biweeklybudget.readthedocs.io/en/latest/app_usage.html#currency-formatting-and-localization>`_;
the short version is that I've done my best to make this configurable, but as far as I know I'm the
only person using this software. If anyone else wants to use it and it doesn't work for your currency
or locale, let me know and I'll fix it.

Important Warning
+++++++++++++++++

This software should be considered *beta* quality at best. I've been using it for about a year and it seems to be working correctly, but I'm very much a creature of habit; it's entirely possible that there are major bugs I haven't found because I always do the same action in the same way, the same order, the same steps, etc. In short, this application works for *me* and the *exact particular way I use it*, but it hasn't seen enough use from other people to say that it's stable and correct in the general case. As such, please **DO NOT RELY ON** the mathematical/financial calculations without double-checking them.

Main Features
+++++++++++++

* Budgeting on a biweekly (fortnightly; every other week) basis, for those of us who are paid that way.
* Periodic (per-pay-period) or standing budgets.
* Optional automatic downloading of transactions/statements from your financial institutions via OFX Direct Connect, screen scraping, or `Plaid <https://plaid.com/>`__ and reconciling transactions (bank, credit, and investment accounts).
* Scheduled transactions - specific date or recurring (date-of-month, or number of times per pay period).
* Tracking of vehicle fuel fills (fuel log) and graphing of fuel economy.
* Cost tracking for multiple projects, including bills-of-materials for them. Optional synchronization from Amazon Wishlists to projects.
* Calculation of estimated credit card payoff amount and time, with configurable payment methods, payment increases on specific dates, and additional payments on specific dates.
* Ability to split a Transaction across multiple Budgets.

Requirements
------------

**Note:** Alternatively, biweeklybudget is also distributed as a `Docker container <http://biweeklybudget.readthedocs.io/en/latest/flask_app.html>`_.
Using the dockerized version will eliminate all of these dependencies aside from MySQL (which you can run in another container) and
Vault (if you choose to take advantage of the OFX downloading), which you can also run in another container.

* Python 3.7+ (currently tested and developed with 3.10).
* Python `VirtualEnv <http://www.virtualenv.org/>`_ and ``pip`` (recommended installation method; your OS/distribution should have packages for these)
* MySQL, or a compatible database (e.g. `MariaDB <https://mariadb.org/>`_). biweeklybudget uses `SQLAlchemy <http://www.sqlalchemy.org/>`_ for database abstraction, but currently specifies some MySQL-specific options, and is only tested with MySQL.
* To use the automated Plaid transaction downloading functionality, a valid `Plaid <https://plaid.com/>`__ account.
* To use the automated OFX Direct Connect transaction downloading functionality:

  * A running, reachable instance of `Hashicorp Vault <https://www.vaultproject.io/>`_ with your financial institution web credentials stored in it.
  * If your bank does not support OFX remote access ("Direct Connect"), you will need to write a custom screen-scraper class using Selenium and a browser.

Installation
------------

It's recommended that you run from the Docker image, as that's what I do. If you
don't want to do that, you can also install in a virtualenv using Python 3.10:

.. code-block:: bash

    mkdir biweeklybudget
    python3.10 -mvenv venv
    source venv/bin/activate
    pip install biweeklybudget

License
-------

biweeklybudget itself is licensed under the
`GNU Affero General Public License, version 3 <https://www.gnu.org/licenses/agpl-3.0.en.html>`_.
This is specifically intended to extend to anyone who uses the software remotely
over a network, the same rights as those who download and install it locally.
biweeklybudget makes use of various third party software, especially in the UI and
frontend, that is distributed under other licenses. Please see
``biweeklybudget/flaskapp/static`` in the source tree for further information.

biweeklybudget includes a number of dependencies distributed alongside it, which
are licensed and distributed under their respective licenses. See the
``biweeklybudget/vendored`` directory in the source distribution for further
information.

Attributions
------------

The logo used for biweeklybudget makes use of the wonderful, free Ledger icon by Eucalyp on FlatIcons: `Ledger icons created by Eucalyp - Flaticon <https://www.flaticon.com/free-icons/ledger>`_.
