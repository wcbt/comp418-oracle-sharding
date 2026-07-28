WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

SET ECHO ON
SET FEEDBACK ON
SET SQLBLANKLINES ON
SET DEFINE OFF
SET PAGESIZE 100
SET LINESIZE 220

PROMPT === INSERTING CUSTOMER-ID TEST DATA ===

PROMPT === CUSTOMER 418001 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418001,
    'Test Customer 01',
    'customer01@example.test',
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
    418001,
    1,
    'CHEQUING',
    1100,
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
    418001,
    1,
    1,
    918001,
    'CREDIT',
    1100,
    1100
);

COMMIT;

PROMPT === CUSTOMER 418002 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418002,
    'Test Customer 02',
    'customer02@example.test',
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
    418002,
    1,
    'CHEQUING',
    1200,
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
    418002,
    1,
    1,
    918002,
    'CREDIT',
    1200,
    1200
);

COMMIT;

PROMPT === CUSTOMER 418003 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418003,
    'Test Customer 03',
    'customer03@example.test',
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
    418003,
    1,
    'CHEQUING',
    1300,
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
    418003,
    1,
    1,
    918003,
    'CREDIT',
    1300,
    1300
);

COMMIT;

PROMPT === CUSTOMER 418004 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418004,
    'Test Customer 04',
    'customer04@example.test',
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
    418004,
    1,
    'CHEQUING',
    1400,
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
    418004,
    1,
    1,
    918004,
    'CREDIT',
    1400,
    1400
);

COMMIT;

PROMPT === CUSTOMER 418005 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418005,
    'Test Customer 05',
    'customer05@example.test',
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
    418005,
    1,
    'CHEQUING',
    1500,
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
    418005,
    1,
    1,
    918005,
    'CREDIT',
    1500,
    1500
);

COMMIT;

PROMPT === CUSTOMER 418006 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418006,
    'Test Customer 06',
    'customer06@example.test',
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
    418006,
    1,
    'CHEQUING',
    1600,
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
    418006,
    1,
    1,
    918006,
    'CREDIT',
    1600,
    1600
);

COMMIT;

PROMPT === CUSTOMER 418007 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418007,
    'Test Customer 07',
    'customer07@example.test',
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
    418007,
    1,
    'CHEQUING',
    1700,
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
    418007,
    1,
    1,
    918007,
    'CREDIT',
    1700,
    1700
);

COMMIT;

PROMPT === CUSTOMER 418008 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418008,
    'Test Customer 08',
    'customer08@example.test',
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
    418008,
    1,
    'CHEQUING',
    1800,
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
    418008,
    1,
    1,
    918008,
    'CREDIT',
    1800,
    1800
);

COMMIT;

PROMPT === CUSTOMER 418009 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418009,
    'Test Customer 09',
    'customer09@example.test',
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
    418009,
    1,
    'CHEQUING',
    1900,
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
    418009,
    1,
    1,
    918009,
    'CREDIT',
    1900,
    1900
);

COMMIT;

PROMPT === CUSTOMER 418010 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418010,
    'Test Customer 10',
    'customer10@example.test',
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
    418010,
    1,
    'CHEQUING',
    2000,
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
    418010,
    1,
    1,
    918010,
    'CREDIT',
    2000,
    2000
);

COMMIT;

PROMPT === CUSTOMER 418011 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418011,
    'Test Customer 11',
    'customer11@example.test',
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
    418011,
    1,
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
    418011,
    1,
    1,
    918011,
    'CREDIT',
    2100,
    2100
);

COMMIT;

PROMPT === CUSTOMER 418012 ===

INSERT INTO customers
(
    customer_id,
    full_name,
    email,
    customer_state
)
VALUES
(
    418012,
    'Test Customer 12',
    'customer12@example.test',
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
    418012,
    1,
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
    418012,
    1,
    1,
    918012,
    'CREDIT',
    2200,
    2200
);

COMMIT;

PROMPT === COORDINATOR ROW COUNTS ===

SELECT COUNT(*) AS customer_count
FROM customers
WHERE customer_id BETWEEN 418001 AND 418012;

SELECT COUNT(*) AS account_count
FROM accounts
WHERE customer_id BETWEEN 418001 AND 418012;

SELECT COUNT(*) AS ledger_count
FROM ledger_entries
WHERE customer_id BETWEEN 418001 AND 418012;

PROMPT Customer-ID test data inserted successfully.
EXIT SUCCESS
