WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

SET ECHO ON
SET FEEDBACK ON
SET SQLBLANKLINES ON
SET DEFINE OFF
SET PAGESIZE 100
SET LINESIZE 220

PROMPT === INSERTING CUSTOMER-ID COMPARISON DATA ===

PROMPT === CUSTOMER FAMILY 518001 ===

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
    'Customer Design Customer 01',
    'customer.design01@example.test',
    'ACTIVE'
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518001,
    418003,
    'CHEQUING',
    2100,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518001,
    418003,
    1,
    948001,
    'CREDIT',
    2100,
    2100
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518001,
    418001,
    'SAVINGS',
    3100,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518001,
    418001,
    1,
    948002,
    'CREDIT',
    3100,
    3100
);

COMMIT;

PROMPT === CUSTOMER FAMILY 518002 ===

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
    'Customer Design Customer 02',
    'customer.design02@example.test',
    'ACTIVE'
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518002,
    418004,
    'CHEQUING',
    2200,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518002,
    418004,
    1,
    948003,
    'CREDIT',
    2200,
    2200
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518002,
    418002,
    'SAVINGS',
    3200,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518002,
    418002,
    1,
    948004,
    'CREDIT',
    3200,
    3200
);

COMMIT;

PROMPT === CUSTOMER FAMILY 518003 ===

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
    'Customer Design Customer 03',
    'customer.design03@example.test',
    'ACTIVE'
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518003,
    418005,
    'CHEQUING',
    2300,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518003,
    418005,
    1,
    948005,
    'CREDIT',
    2300,
    2300
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518003,
    418006,
    'SAVINGS',
    3300,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518003,
    418006,
    1,
    948006,
    'CREDIT',
    3300,
    3300
);

COMMIT;

PROMPT === CUSTOMER FAMILY 518004 ===

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
    'Customer Design Customer 04',
    'customer.design04@example.test',
    'ACTIVE'
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518004,
    418009,
    'CHEQUING',
    2400,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518004,
    418009,
    1,
    948007,
    'CREDIT',
    2400,
    2400
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518004,
    418007,
    'SAVINGS',
    3400,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518004,
    418007,
    1,
    948008,
    'CREDIT',
    3400,
    3400
);

COMMIT;

PROMPT === CUSTOMER FAMILY 518005 ===

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
    'Customer Design Customer 05',
    'customer.design05@example.test',
    'ACTIVE'
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518005,
    418010,
    'CHEQUING',
    2500,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518005,
    418010,
    1,
    948009,
    'CREDIT',
    2500,
    2500
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518005,
    418008,
    'SAVINGS',
    3500,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518005,
    418008,
    1,
    948010,
    'CREDIT',
    3500,
    3500
);

COMMIT;

PROMPT === CUSTOMER FAMILY 518006 ===

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
    'Customer Design Customer 06',
    'customer.design06@example.test',
    'ACTIVE'
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518006,
    418011,
    'CHEQUING',
    2600,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518006,
    418011,
    1,
    948011,
    'CREDIT',
    2600,
    2600
);

INSERT INTO accounts
(
    customer_id,
    account_id,
    account_type,
    balance,
    currency,
    account_state
)
VALUES
(
    518006,
    418012,
    'SAVINGS',
    3600,
    'CAD',
    'ACTIVE'
);

INSERT INTO ledger_entries
(
    customer_id,
    account_id,
    entry_id,
    transfer_id,
    entry_type,
    amount,
    balance_after
)
VALUES
(
    518006,
    418012,
    1,
    948012,
    'CREDIT',
    3600,
    3600
);

COMMIT;

PROMPT === COMPARISON DATA COUNTS ===

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

PROMPT Customer-ID comparison data inserted successfully.
EXIT SUCCESS
