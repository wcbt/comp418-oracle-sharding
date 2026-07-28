WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

SET ECHO ON
SET FEEDBACK ON
SET SQLBLANKLINES ON
SET DEFINE OFF
SET PAGESIZE 100
SET LINESIZE 220

PROMPT === INSERTING ACCOUNT-ID TEST DATA ===

PROMPT === CUSTOMER 518001 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    518001,
    'Account Design Customer 01',
    'account.customer01@example.test',
    'ACTIVE'
);

COMMIT;


PROMPT === CHEQUING ACCOUNT 418003 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418003,
    518001,
    'CHEQUING',
    2100,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418003,
    1,
    938001,
    518001,
    'CREDIT',
    2100,
    2100
);

COMMIT;


PROMPT === SAVINGS ACCOUNT 418001 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418001,
    518001,
    'SAVINGS',
    3100,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418001,
    1,
    938002,
    518001,
    'CREDIT',
    3100,
    3100
);

COMMIT;

PROMPT === CUSTOMER 518002 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    518002,
    'Account Design Customer 02',
    'account.customer02@example.test',
    'ACTIVE'
);

COMMIT;


PROMPT === CHEQUING ACCOUNT 418004 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418004,
    518002,
    'CHEQUING',
    2200,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418004,
    1,
    938003,
    518002,
    'CREDIT',
    2200,
    2200
);

COMMIT;


PROMPT === SAVINGS ACCOUNT 418002 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418002,
    518002,
    'SAVINGS',
    3200,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418002,
    1,
    938004,
    518002,
    'CREDIT',
    3200,
    3200
);

COMMIT;

PROMPT === CUSTOMER 518003 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    518003,
    'Account Design Customer 03',
    'account.customer03@example.test',
    'ACTIVE'
);

COMMIT;


PROMPT === CHEQUING ACCOUNT 418005 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418005,
    518003,
    'CHEQUING',
    2300,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418005,
    1,
    938005,
    518003,
    'CREDIT',
    2300,
    2300
);

COMMIT;


PROMPT === SAVINGS ACCOUNT 418006 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418006,
    518003,
    'SAVINGS',
    3300,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418006,
    1,
    938006,
    518003,
    'CREDIT',
    3300,
    3300
);

COMMIT;

PROMPT === CUSTOMER 518004 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    518004,
    'Account Design Customer 04',
    'account.customer04@example.test',
    'ACTIVE'
);

COMMIT;


PROMPT === CHEQUING ACCOUNT 418009 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418009,
    518004,
    'CHEQUING',
    2400,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418009,
    1,
    938007,
    518004,
    'CREDIT',
    2400,
    2400
);

COMMIT;


PROMPT === SAVINGS ACCOUNT 418007 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418007,
    518004,
    'SAVINGS',
    3400,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418007,
    1,
    938008,
    518004,
    'CREDIT',
    3400,
    3400
);

COMMIT;

PROMPT === CUSTOMER 518005 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    518005,
    'Account Design Customer 05',
    'account.customer05@example.test',
    'ACTIVE'
);

COMMIT;


PROMPT === CHEQUING ACCOUNT 418010 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418010,
    518005,
    'CHEQUING',
    2500,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418010,
    1,
    938009,
    518005,
    'CREDIT',
    2500,
    2500
);

COMMIT;


PROMPT === SAVINGS ACCOUNT 418008 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418008,
    518005,
    'SAVINGS',
    3500,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418008,
    1,
    938010,
    518005,
    'CREDIT',
    3500,
    3500
);

COMMIT;

PROMPT === CUSTOMER 518006 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    518006,
    'Account Design Customer 06',
    'account.customer06@example.test',
    'ACTIVE'
);

COMMIT;


PROMPT === CHEQUING ACCOUNT 418011 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418011,
    518006,
    'CHEQUING',
    2600,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418011,
    1,
    938011,
    518006,
    'CREDIT',
    2600,
    2600
);

COMMIT;


PROMPT === SAVINGS ACCOUNT 418012 ===

INSERT INTO accounts
(
    account_id,
    customer_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    418012,
    518006,
    'SAVINGS',
    3600,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    account_id,
    entry_id,
    transfer_id,
    customer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    418012,
    1,
    938012,
    518006,
    'CREDIT',
    3600,
    3600
);

COMMIT;

PROMPT === COORDINATOR ROW COUNTS ===

SELECT COUNT(*) AS customer_count
FROM customers
WHERE customer_id BETWEEN 518001 AND 518006;

SELECT COUNT(*) AS account_count
FROM accounts
WHERE customer_id BETWEEN 518001 AND 518006;

SELECT COUNT(*) AS ledger_count
FROM ledger_entries
WHERE customer_id BETWEEN 518001 AND 518006;

PROMPT === ACCOUNTS PER CUSTOMER ===

SELECT
    customer_id,
    COUNT(*) AS account_count
FROM accounts
WHERE customer_id BETWEEN 518001 AND 518006
GROUP BY customer_id
ORDER BY customer_id;

PROMPT Account-ID test data inserted successfully.
EXIT SUCCESS
