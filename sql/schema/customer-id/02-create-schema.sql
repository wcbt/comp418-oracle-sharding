WHENEVER SQLERROR EXIT SQL.SQLCODE
SET ECHO ON
SET FEEDBACK ON
SET SERVEROUTPUT ON
SET SQLBLANKLINES ON

ALTER SESSION ENABLE SHARD DDL;

CREATE TABLESPACE SET bank_customer_ts;

CREATE SHARDED TABLE customers
(
    customer_id    NUMBER(12)      NOT NULL,
    full_name      VARCHAR2(120)   NOT NULL,
    email          VARCHAR2(180),
    customer_state VARCHAR2(20)    DEFAULT 'ACTIVE' NOT NULL,
    created_at     TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT bank_cust_customers_pk
        PRIMARY KEY (customer_id),

    CONSTRAINT bank_cust_customer_state_ck
        CHECK (customer_state IN ('ACTIVE', 'SUSPENDED', 'CLOSED'))
)
PARTITION BY CONSISTENT HASH (customer_id)
PARTITIONS AUTO
TABLESPACE SET bank_customer_ts;


CREATE SHARDED TABLE accounts
(
    customer_id  NUMBER(12)     NOT NULL,
    account_id   NUMBER(18)     NOT NULL,
    account_type VARCHAR2(20)   NOT NULL,
    balance      NUMBER(18, 2)  DEFAULT 0 NOT NULL,
    currency     CHAR(3)        DEFAULT 'CAD' NOT NULL,
    account_state VARCHAR2(20)  DEFAULT 'ACTIVE' NOT NULL,
    created_at   TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT bank_cust_accounts_pk
        PRIMARY KEY (customer_id, account_id),

    CONSTRAINT bank_cust_accounts_customer_fk
        FOREIGN KEY (customer_id)
        REFERENCES customers (customer_id),

    CONSTRAINT bank_cust_account_type_ck
        CHECK (account_type IN ('CHEQUING', 'SAVINGS')),

    CONSTRAINT bank_cust_account_state_ck
        CHECK (account_state IN ('ACTIVE', 'FROZEN', 'CLOSED')),

    CONSTRAINT bank_cust_balance_ck
        CHECK (balance >= 0)
)
PARTITION BY REFERENCE (bank_cust_accounts_customer_fk);


CREATE SHARDED TABLE ledger_entries
(
    customer_id             NUMBER(12)     NOT NULL,
    account_id              NUMBER(18)     NOT NULL,
    entry_id                NUMBER(20)     NOT NULL,
    transfer_id             NUMBER(20)     NOT NULL,
    entry_type              VARCHAR2(6)    NOT NULL,
    amount                  NUMBER(18, 2)  NOT NULL,
    balance_after           NUMBER(18, 2)  NOT NULL,
    counterparty_customer_id NUMBER(12),
    counterparty_account_id  NUMBER(18),
    created_at              TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,

    CONSTRAINT bank_cust_ledger_pk
        PRIMARY KEY (customer_id, account_id, entry_id),

    CONSTRAINT bank_cust_ledger_account_fk
        FOREIGN KEY (customer_id, account_id)
        REFERENCES accounts (customer_id, account_id),

    CONSTRAINT bank_cust_entry_type_ck
        CHECK (entry_type IN ('DEBIT', 'CREDIT')),

    CONSTRAINT bank_cust_entry_amount_ck
        CHECK (amount > 0),

    CONSTRAINT bank_cust_balance_after_ck
        CHECK (balance_after >= 0)
)
PARTITION BY REFERENCE (bank_cust_ledger_account_fk);

PROMPT Customer-ID table family created successfully.
