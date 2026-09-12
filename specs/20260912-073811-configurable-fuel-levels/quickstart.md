# Quickstart: validating Configurable Fuel Levels

## Prerequisites

The MariaDB test container and environment variables from `CLAUDE.md` ("Test Database
Setup for Development"), and tox from the main checkout's virtualenv.

## Automated

```bash
tox -e py314        # parse/validate unit tests + subprocess import tests
tox -e acceptance   # fuel page default list, custom list options/defaults/escaping, save
tox -e docs         # FUEL_LEVELS documented; build must succeed
```

Focused runs while developing:

```bash
tox -e py314 -- biweeklybudget/tests/unit/test_settings_fuel_levels.py
tox -e acceptance -- -k "fuel"
```

## Manual

1. Start the app with no `FUEL_LEVELS` (`flask rundev`), open `/fuel`, then **Add Fill**.
   Both level selects show `0/10` … `10/10`. Starting level is `0/10`, ending level is
   `10/10` (spec User Story 2).
2. Restart with `FUEL_LEVELS="E:0,1/4:25,1/2:50,3/4:75,F:100"`. The selects show those five
   labels in order, with E and F preselected. Save a fill with 1/4 → F. The new row in the
   fuel log shows 25% and 100% (spec User Story 1).
3. Restart with `FUEL_LEVELS="E:0,F:150"`. The app exits with
   `ERROR: FUEL_LEVELS setting is invalid: …` naming the problem (spec User Story 3).

Contract details: [contracts/fuel-levels-setting.md](./contracts/fuel-levels-setting.md).
