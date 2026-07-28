OPTIONS
(
    SKIP=1,
    ERRORS=0,
    ROWS=5000,
    READSIZE=2097152,
    BINDSIZE=2097152
)

LOAD DATA
APPEND
INTO TABLE ledger_entries

FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
TRAILING NULLCOLS
(
    account_id                   INTEGER EXTERNAL,
    entry_id                     INTEGER EXTERNAL,
    transfer_id                  INTEGER EXTERNAL,
    customer_id                  INTEGER EXTERNAL,
    entry_type                   CHAR,
    amount                       DECIMAL EXTERNAL,
    balance_after                DECIMAL EXTERNAL,
    counterparty_customer_id     INTEGER EXTERNAL
        NULLIF counterparty_customer_id=BLANKS,
    counterparty_account_id      INTEGER EXTERNAL
        NULLIF counterparty_account_id=BLANKS
)
