.. _app_usage:

Application Usage
=================

This documentation is a work in progress. I suppose if anyone other than me
ever tries to use this, I'll document it a bit more.

Pay Periods
-----------

Balancing Pay Periods
+++++++++++++++++++++

When viewing pay periods in the past (i.e. pay periods that have already ended),
a "Balance Budgets" button will appear in the header of the "Periodic Budgets"
table. This button launches a modal dialog for balancing all periodic budgets
for the period, in an attempt to zero out the remaining balance for the period.
The dialog will first ask you to select a Standing Budget to use as a source/destination
budget; any excess or insufficient funds for the pay period will be added to or
taken from this standing budget. Once that dialog is submitted, the algorithm will
attempt to transfer funds between all periodic budgets for that pay period, to get
as many periodic budgets as possible to have a zero remianing amount. After that,
any shortfall is transferred from the Standing Budget, or any excess is transferred
to the Standing Budget. All transfers and the final remaining amounts will be displayed
for confirmation before any transfers are committed.
