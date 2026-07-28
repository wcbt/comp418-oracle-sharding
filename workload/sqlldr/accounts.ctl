OPTIONS
(
    SKIP=1,
    ERRORS=0,
    ROWS=5000,
    READSIZE=1048576,
    BINDSIZE=1048576
)

LOAD DATA
APPEND
INTO TABLE accounts

FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
TRAILING NULLCOLS
(
    account_id    INTEGER EXTERNAL,
    customer_id   INTEGER EXTERNAL,
    account_type  CHAR,
    balance       DECIMAL EXTERNAL,
    currency      CHAR,
    account_state CHAR
)
