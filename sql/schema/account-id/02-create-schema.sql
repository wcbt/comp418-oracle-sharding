WHENEVER SQLERROR EXIT SQL.SQLCODE
WHENEVER OSERROR EXIT FAILURE

SET ECHO ON
SET FEEDBACK ON
SET SERVEROUTPUT ON
SET SQLBLANKLINES ON
SET DEFINE OFF

ALTER SESSION ENABLE SHARD DDL;

CREATE TABLESPACE SET bank_acct_customer_ts;
CREATE TABLESPACE SET bank_account_ts;


-- Independent customer-ID table family.
CREATE SHARDED TABLE customers
(
    customer_id    NUMBER(12)      NOT NULL,
    full_name      VARCHAR2(120)   NOT NULL,
    email          VARCHAR2(180),
    customer_state VARCHAR2(20)    DEFAULT 'ACTIVE' NOT NULL,
    created_at     TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT bank_acct_customers_pk
        PRIMARY KEY (customer_id),

    CONSTRAINT bank_acct_customer_state_ck
        CHECK (customer_state IN ('ACTIVE', 'SUSPENDED', 'CLOSED'))
)
PARTITION BY CONSISTENT HASH (customer_id)
PARTITIONS AUTO
TABLESPACE SET bank_acct_customer_ts;


-- Root of the account-ID table family.
-- CUSTOMER_ID is intentionally not a foreign key because CUSTOMERS
-- and ACCOUNTS belong to different sharded table families.
CREATE SHARDED TABLE accounts
(
    account_id    NUMBER(18)     NOT NULL,
    customer_id   NUMBER(12)     NOT NULL,
    account_type  VARCHAR2(20)   NOT NULL,
    balance       NUMBER(18, 2)  DEFAULT 0 NOT NULL,
    currency      CHAR(3)        DEFAULT 'CAD' NOT NULL,
    account_state VARCHAR2(20)   DEFAULT 'ACTIVE' NOT NULL,
    created_at    TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT bank_acct_accounts_pk
        PRIMARY KEY (account_id),

    CONSTRAINT bank_acct_account_type_ck
        CHECK (account_type IN ('CHEQUING', 'SAVINGS')),

    CONSTRAINT bank_acct_account_state_ck
        CHECK (account_state IN ('ACTIVE', 'FROZEN', 'CLOSED')),

    CONSTRAINT bank_acct_balance_ck
        CHECK (balance >= 0)
)
PARTITION BY CONSISTENT HASH (account_id)
PARTITIONS AUTO
TABLESPACE SET bank_account_ts;


-- This index helps customer-to-account searches locally,
-- although the query still has to examine multiple shards.
CREATE INDEX bank_acct_accounts_customer_ix
    ON accounts (customer_id)
    LOCAL;


-- Child of ACCOUNTS and therefore co-located by ACCOUNT_ID.
CREATE SHARDED TABLE ledger_entries
(
    account_id               NUMBER(18)     NOT NULL,
    entry_id                 NUMBER(20)     NOT NULL,
    transfer_id              NUMBER(20)     NOT NULL,
    customer_id              NUMBER(12)     NOT NULL,
    entry_type               VARCHAR2(6)    NOT NULL,
    amount                   NUMBER(18, 2)  NOT NULL,
    balance_after            NUMBER(18, 2)  NOT NULL,
    counterparty_customer_id NUMBER(12),
    counterparty_account_id  NUMBER(18),
    created_at               TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT bank_acct_ledger_pk
        PRIMARY KEY (account_id, entry_id),

    CONSTRAINT bank_acct_ledger_account_fk
        FOREIGN KEY (account_id)
        REFERENCES accounts (account_id),

    CONSTRAINT bank_acct_entry_type_ck
        CHECK (entry_type IN ('DEBIT', 'CREDIT')),

    CONSTRAINT bank_acct_entry_amount_ck
        CHECK (amount > 0),

    CONSTRAINT bank_acct_balance_after_ck
        CHECK (balance_after >= 0)
)
PARTITION BY REFERENCE (bank_acct_ledger_account_fk);

PROMPT Account-ID table families created successfully.
