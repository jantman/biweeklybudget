.. _flask_app:

Flask Application
=================

Running
-------

1. ``source bin/activate``
2. ``export FLASK_APP="biweeklybudget.flaskapp.app"``
3. ``flask --help``

* Run App: ``flask run``
* Run with debug/reload: ``flask run --reload --debugger``
* Build theme: ``pushd biweeklybudget/flaskapp/static/startbootstrap-sb-admin-2 && gulp``

To run the app against the acceptance test database, use: ``DB_CONNSTRING='mysql+pymysql://budgetTester@127.0.0.1:3306/budgettest?charset=utf8mb4' flask run``

By default, Flask will only bind to localhost. If you want to bind to all interfaces, you can add `` --host=0.0.0.0`` to the ``flask run`` commands. Please be aware of the implications of this (see "Security", below).

Security
--------

This code hasn't been audited. It might have SQL injection vulnerabilities in it. It might dump your bank account details in HTML comments. Anything is possible!

To put it succinctly, this was written to be used by me, and me only. It was written with the assumption that anyone who can possibly access any of the application at all, whether in a browser or locally, is authorized to view and/or edit anything and everything related to the application (configuration, everything in the database, everything in Vault if it's being used). If you even think about making this accessible to anything other than localhost on a computer you physically own, it's entirely up to you how you secure it, but make sure you do it really well.
