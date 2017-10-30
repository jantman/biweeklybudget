biweeklybudget
==============

.. image:: https://secure.travis-ci.org/jantman/biweeklybudget.png?branch=master
   :target: http://travis-ci.org/jantman/biweeklybudget
   :alt: travis-ci for master branch

.. image:: https://codecov.io/github/jantman/biweeklybudget/coverage.svg?branch=master
   :target: https://codecov.io/github/jantman/biweeklybudget?branch=master
   :alt: coverage report for master branch

.. image:: https://readthedocs.org/projects/biweeklybudget/badge/?version=latest
   :target: https://readthedocs.org/projects/biweeklybudget/?badge=latest
   :alt: sphinx documentation for latest release

.. image:: http://www.repostatus.org/badges/latest/wip.svg
   :alt: Project Status: WIP – Initial development is in progress, but there has not yet been a stable, usable release suitable for the public.
   :target: http://www.repostatus.org/#wip

.. image:: https://img.shields.io/waffle/label/jantman/biweeklybudget/ready.svg
   :target: https://waffle.io/jantman/biweeklybudget
   :alt: 'Stories in Ready'

Responsive Flask/SQLAlchemy personal finance app, specifically for biweekly budgeting.

**For full documentation**, see `http://biweeklybudget.readthedocs.io/en/latest/ <http://biweeklybudget.readthedocs.io/en/latest/>`_

**For screenshots**, see `<http://biweeklybudget.readthedocs.io/en/latest/screenshots.html>`_

**For development activity**, see `https://waffle.io/jantman/biweeklybudget <https://waffle.io/jantman/biweeklybudget>`_

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
you're going to use the automatic transaction download functionality, you should be familiar with `Hashicorp Vault <https://www.vaultproject.io/>`_
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

This software should be considered *alpha* quality at best. At this point, I can't even say that I'm 100% confident
it is mathematically correct, balances are right, all scheduled transactions will show up in the right places, etc. I'm going to
be testing it for my own purposes, and comparing it against my manual calculations. Until further notice, if you decide to use this,
please double-check *everything* produced by it before relying on its output.

Main Features
+++++++++++++

* Budgeting on a biweekly (fortnightly; every other week) basis, for those of us who are paid that way.
* Periodic (per-pay-period) or standing budgets.
* Optional automatic downloading of transactions/statements from your financial institutions and reconciling transactions (bank, credit, and investment accounts).
* Scheduled transactions - specific date or recurring (date-of-month, or number of times per pay period).
* Tracking of vehicle fuel fills (fuel log) and graphing of fuel economy.
* Cost tracking for multiple projects, including bills-of-materials for them. Optional synchronization from Amazon Wishlists to projects.
* Calculation of estimated credit card payoff amount and time, with configurable payment methods, payment increases on specific dates, and additional payments on specific dates.

Requirements
------------

**Note:** Alternatively, biweeklybudget is also distributed as a `Docker container <http://biweeklybudget.readthedocs.io/en/latest/flask_app.html>`_.
Using the dockerized version will eliminate all of these dependencies aside from MySQL (which you can run in another container) and
Vault (if you choose to take advantage of the OFX downloading), which you can also run in another container.

* Python 2.7 or 3.3+ (currently tested with 2.7, 3.3, 3.4, 3.5, 3.6 and developed with 3.6)
* Python `VirtualEnv <http://www.virtualenv.org/>`_ and ``pip`` (recommended installation method; your OS/distribution should have packages for these)
* MySQL, or a compatible database (e.g. `MariaDB <https://mariadb.org/>`_). biweeklybudget uses `SQLAlchemy <http://www.sqlalchemy.org/>`_ for database abstraction, but currently specifies some MySQL-specific options, and is only tested with MySQL.
* To use the automated OFX transaction downloading functionality:

  * A running, reachable instance of `Hashicorp Vault <https://www.vaultproject.io/>`_ with your financial institution web credentials stored in it.
  * `PhantomJS <http://phantomjs.org/>`_ for downloading transaction data from institutions that do not support OFX remote access ("Direct Connect").

Installation
------------

It's recommended that you install into a virtual environment (virtualenv /
venv). See the `virtualenv usage documentation <http://www.virtualenv.org/en/latest/>`_
for information on how to create a venv.

This app is developed against Python 3.6, but should work back to 2.7. It does
not support Python3 < 3.3.

.. code-block:: bash

    mkdir biweeklybudget
    virtualenv --python=python3.6 .
    source bin/activate
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
