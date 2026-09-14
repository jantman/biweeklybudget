# Feature Specification: Remove OFX Downloading, Vault and Keychain

**Feature Branch**: `robot-army/issue-265-deprecate-ofx-and-remove-vault-and`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "jantman/biweeklybudget issue #265 — "deprecate OFX and remove Vault and other related stuff": As of the 1.1.0 release notes, OFX is deprecated. For 2.x, remove all OFX stuff/dependencies as well as Vault and Keychain."

## Background

Release 1.1.0 announced that OFX support is deprecated and that, going forward, only
Plaid will be supported for getting transactions from financial institutions. OFX
support today consists of:

- three command-line tools: one that downloads OFX statements from banks (either over
  the OFX protocol or by driving a web browser through a bank's website), one that loads
  previously-saved OFX statement files from disk, and a bundled copy of a third-party
  OFX client tool used to set accounts up for downloading;
- two HTTP endpoints those tools use to list accounts configured for downloading and to
  upload a statement;
- integration with Hashicorp Vault, which is where the download tool reads bank
  usernames and passwords from;
- the bundled OFX client's use of the operating system keychain ("keyring") to store
  passwords;
- a base class for writing browser automation ("screen scraping") against bank websites;
- three settings (the Vault address, the path to the Vault token, and the directory OFX
  statements are saved to) and three per-account fields that exist only to configure
  OFX downloading (the Vault credentials path, the download configuration JSON, and
  "OFX Cat Memo to Name");
- the third-party packages all of the above need, and the documentation describing it.

**Naming note**: the application also uses the word "OFX" for things that are *not*
OFX downloading and that Plaid depends on. Transactions and statements retrieved from
Plaid are stored as "OFX Transactions" and "OFX Statements", listed on the **OFX**
page, reconciled on the **Reconcile** page, and used for stale-data warnings and
interest-charge detection; the "Negate OFX Amounts" account setting is applied to Plaid
transactions. All of that is how Plaid data flows through the application, and it
**stays**. This feature removes OFX *downloading and importing*, not the storage of
downloaded transactions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install and run without OFX, Vault or keychain dependencies (Priority: P1)

An operator installs or upgrades biweeklybudget (from the package or the Docker image)
and uses it with Plaid. Nothing they install or configure relates to OFX downloading,
Vault or the operating system keychain: those third-party packages are not installed,
the OFX command-line tools no longer exist, and the application starts and works
normally.

**Why this priority**: This is the substance of the issue — dropping the dependencies
and the code of a feature deprecated since 1.1.0. Everything else follows from it.

**Independent Test**: Install the package into a clean environment and build the Docker
image; confirm that none of the OFX/Vault/keychain packages are installed, the three OFX
commands are absent, the remaining commands work, and the web application serves every
page.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** the package is installed, **Then** none of
   the packages that exist only for OFX downloading, Vault or keychain access are
   installed.
2. **Given** an installed package or the Docker image, **When** the operator looks for
   the `ofxgetter`, `ofxbackfiller` or `ofxclient` commands, **Then** they do not exist,
   and the other commands (`addtrans`, `loaddata`, `initdb`, `wishlist2project`) still
   run.
3. **Given** a running application, **When** a client requests the OFX account-list or
   statement-upload HTTP endpoints, **Then** the application responds that the page
   does not exist (HTTP 404 or 405), as for any other unknown URL.
4. **Given** a running application with Plaid-downloaded data, **When** the operator
   uses the OFX, Reconcile, Accounts, Index and Plaid pages, **Then** they behave as
   before this change.

---

### User Story 2 - Upgrade an existing installation cleanly (Priority: P1)

An operator with an existing database and settings file upgrades. The database upgrade
removes the account fields that only configured OFX downloading, and everything else in
the database — accounts, transactions, OFX/Plaid transactions and statements,
reconciliations, and the "Negate OFX Amounts" setting — is unchanged. A settings file
or environment that still sets the removed Vault/statement settings does not prevent
the application from starting.

**Why this priority**: The operator's financial data must survive the upgrade intact,
and an upgrade that refuses to start because of a leftover setting would be a
regression.

**Independent Test**: Run the database upgrade against a database containing accounts
with the OFX-only fields populated, and confirm that the fields are gone and all other
data is unchanged; run the downgrade and confirm the fields come back (empty). Start
the application with the old settings still present.

**Acceptance Scenarios**:

1. **Given** a database at the previous schema whose accounts have values in the
   Vault-credentials-path, download-configuration and "OFX Cat Memo to Name" fields,
   **When** the database is upgraded, **Then** those three fields no longer exist and
   every other account field and every other table's data is unchanged.
2. **Given** an upgraded database, **When** it is downgraded one step, **Then** the
   three fields exist again, with no value (the "OFX Cat Memo to Name" field false).
3. **Given** a settings module or environment that still defines the Vault address,
   Vault token path or statement save path, **When** the application starts, **Then**
   it starts normally and ignores them.

---

### User Story 3 - Account forms show only settings that do something (Priority: P2)

An operator adding or editing an account in the web UI no longer sees the "Vault Creds
Path", "OFXGetter Config (JSON)" and "OFX Cat Memo to Name" fields, which no longer have
any effect. "Negate OFX Amounts", "Reconcile Transactions" and the interest/payment
regular-expression fields, which apply to Plaid-downloaded transactions, remain.

**Why this priority**: Leaving dead fields in the form would mislead the operator, but
it does not affect data or behaviour.

**Independent Test**: Open the Add Account and Edit Account modals and confirm the three
fields are absent; save a new account and edit an existing one; confirm the save
succeeds and the remaining fields round-trip.

**Acceptance Scenarios**:

1. **Given** the Accounts page, **When** the operator opens Add Account or Edit Account,
   **Then** the three OFX-download fields are not shown and all other fields are.
2. **Given** the account form, **When** the operator saves an account, **Then** it is
   saved with the values entered, and the account HTTP API no longer accepts or returns
   the three removed fields.

---

### User Story 4 - Documentation describes only what exists (Priority: P2)

A reader of the README and the documentation site finds no instructions for OFX
downloading, Vault, the keychain or screen scraping, and no mention of Vault as a
prerequisite. Plaid is presented as the way to get transactions from financial
institutions. The changelog tells upgrading operators what was removed.

**Why this priority**: Documentation for removed features sends operators to set up
things (such as a Vault server) that the application no longer uses.

**Independent Test**: Build the documentation and search it and the README for
OFX-downloading, Vault, keychain and screen-scraping instructions; confirm none remain
other than in the changelog's history and the upgrade note.

**Acceptance Scenarios**:

1. **Given** the built documentation, **When** a reader looks for how to get
   transactions from a bank, **Then** they are directed to Plaid only.
2. **Given** the changelog, **When** an operator reads the Unreleased section, **Then**
   it lists the removed commands, endpoints, settings and account fields and notes the
   database migration.

### Edge Cases

- An account whose only transaction source was OFX downloading keeps all its existing
  OFX transactions and statements; they remain visible, reconcilable, and used for
  stale-data warnings and interest-charge detection. The account simply receives no new
  data until it is linked to Plaid.
- Previously-downloaded OFX statement files on disk are not read, moved or deleted.
  Their data already in the database is unaffected.
- A settings file that still defines the removed settings starts without error (see
  User Story 2).
- A client that still POSTs to the removed statement-upload endpoint gets an error
  response rather than having a statement stored.
- The "Negate OFX Amounts" account setting keeps working for Plaid transactions despite
  its name.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `ofxgetter`, `ofxbackfiller` and `ofxclient` command-line tools MUST be
  removed, along with the code only they use: the OFX download logic, the OFX statement
  import logic used by the tools and the upload endpoint, the bundled OFX client, the
  Vault client, and the screen-scraping base class.
- **FR-002**: The HTTP endpoints for listing OFX-download accounts and uploading an OFX
  statement MUST be removed.
- **FR-003**: The Vault address, Vault token path and OFX statement save path settings
  MUST be removed; if still set in a settings module or the environment they MUST be
  ignored without preventing startup.
- **FR-004**: The account fields for the Vault credentials path, the OFX download
  configuration JSON, and "OFX Cat Memo to Name" MUST be removed from the data model,
  from the account HTTP API, and from the Add/Edit Account form.
- **FR-005**: The database schema change for FR-004 MUST be delivered as a reversible
  migration that drops the three fields on upgrade and restores them (empty) on
  downgrade, leaving all other data untouched.
- **FR-006**: Third-party packages required only for OFX downloading or parsing, Vault
  access, or keychain access MUST be removed from the package's dependencies. Packages
  still used by remaining features MUST be kept.
- **FR-007**: Storage and display of downloaded transactions and statements (the OFX
  page, OFX transaction details, reconciliation, stale-data warnings, interest-charge
  detection) and the "Negate OFX Amounts" setting MUST continue to work unchanged for
  Plaid data.
- **FR-008**: The README, the documentation site (including the HTTP API reference, the
  getting-started and Docker instructions, the settings reference, the screenshots
  page and the generated API docs) and `CLAUDE.md` MUST no longer describe the removed
  features, and the dedicated OFX downloading documentation page MUST be removed.
- **FR-009**: The Docker image build and its tests MUST no longer include or check the
  removed commands.
- **FR-010**: Tests that exercise only removed functionality MUST be removed; tests and
  test data for remaining functionality MUST stop referring to the removed account
  fields; all remaining test suites MUST pass.
- **FR-011**: The changelog MUST gain an Unreleased entry listing the removed commands,
  endpoints, settings and account fields, the dropped dependencies, and the database
  migration, marked as a breaking change.
- **FR-012**: The project constitution's statement that OFX credentials live in
  Hashicorp Vault MUST be corrected, as a separate constitution amendment.

### Key Entities

- **Account**: loses the three OFX-download-only configuration fields. Keeps "Negate OFX
  Amounts", "Reconcile Transactions", the interest/payment/fee regular expressions and
  the Plaid link fields.
- **OFX Statement / OFX Transaction**: unchanged; these hold Plaid-downloaded data (and
  historical OFX data) and are not renamed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean install pulls in zero packages that exist only for OFX
  downloading, Vault or keychain access (at least five fewer direct dependencies than
  before).
- **SC-002**: Zero OFX-download, Vault or keychain command-line tools, HTTP endpoints,
  settings or account form fields remain.
- **SC-003**: After a database upgrade, 100% of accounts, transactions, OFX
  transactions, OFX statements and reconciliations present before the upgrade are still
  present with identical values (other than the three removed fields).
- **SC-004**: The unit, acceptance, migration, documentation and Docker test suites all
  pass.
- **SC-005**: Searching the README and built documentation (excluding the changelog)
  for Vault, keychain, `ofxgetter`, `ofxbackfiller`, `ofxclient` and screen-scraping
  returns no instructions.

## Assumptions

- "OFX stuff" in the issue means OFX *downloading and importing* and what supports it.
  The models, tables, page and setting that carry "OFX" in their names but hold or
  process Plaid data stay, un-renamed; renaming them would be a large, separate change
  with its own migration and URL changes.
- "Keychain" refers to the operating system keyring used by the bundled OFX client to
  store passwords, and the packages that provide it (`keyring`, `SecretStorage`).
- Dropping the "OFX Cat Memo to Name" field is included: it only affected how OFX
  files were parsed and Plaid never used it.
- Operators who still need OFX downloading can stay on a release before this change;
  no replacement or conversion tool is provided.
- This is a backwards-incompatible change intended for the next major release (2.x).
  Per the constitution, this change does not bump the version; the breaking nature is
  recorded in the changelog so the release can be versioned correctly when requested.
- Transitive packages that the remaining dependencies still need (for example the HTML
  parsers used by the wishlist and prime-rate features, and the cryptography package
  used for database authentication) are kept.
