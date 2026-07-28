# Customer-ID vs Account-ID Sharding Comparison

## Test environment

- Oracle AI Database sharded deployment
- One shard catalog
- Two database shards
- Twelve chunks, with six chunks assigned to each shard
- Equivalent comparison dataset:
  - 6 customers
  - 12 accounts
  - 12 ledger entries
  - 2 accounts per customer

## Design A: Customer-ID sharding

Schema owner: `BANK_CUST`

Root sharding key:

```text
CUSTOMERS.CUSTOMER_ID
```

Table family:

```text
CUSTOMERS
└── ACCOUNTS
    └── LEDGER_ENTRIES
```

`ACCOUNTS` and `LEDGER_ENTRIES` use reference partitioning.

### Observed results

- Customer rows were distributed across both shards.
- Every customer had both accounts on the same shard.
- Every ledger row was stored in the same partition as its account.
- Customer, account, and ledger partition names matched.
- Every co-location check returned `YES`.
- A shard-local customer-to-account join returned both accounts.

### Strengths

- Customer profile and all accounts are available on one shard.
- Customer-wide balance and account queries are shard-local.
- Foreign keys enforce the complete customer hierarchy.
- Customer, account, and ledger updates can remain within one table family.

### Weaknesses

- Routing by account ID alone does not provide the customer sharding key.
- Applications may need a customer ID or an account-to-customer lookup before direct shard routing.
- A customer with unusually high activity may concentrate workload on one shard.

## Design B: Account-ID sharding

Schema owner: `BANK_ACCT`

Root sharding keys:

```text
CUSTOMERS.CUSTOMER_ID
ACCOUNTS.ACCOUNT_ID
```

Table families:

```text
CUSTOMERS

ACCOUNTS
└── LEDGER_ENTRIES
```

`CUSTOMERS` and `ACCOUNTS` are independent root table families.
`LEDGER_ENTRIES` uses reference partitioning under `ACCOUNTS`.

### Observed results

- Six accounts were stored on each shard.
- Each customer had one account on each shard.
- Every ledger row was stored in the same partition as its account.
- Account and ledger partition names matched.
- Every account-to-ledger co-location check returned `YES`.
- A shard-local customer-to-account join returned only one of the customer's two accounts.
- The local customer lookup index had twelve usable partitions on each shard.

### Strengths

- Account-specific operations route naturally using account ID.
- Account and ledger activity remains locally co-located.
- Account workload can be distributed independently of customer distribution.
- Large customers with many accounts can have their workload spread across multiple shards.

### Weaknesses

- Customer-wide account queries require results from multiple shards.
- Accounts cannot use an enforced foreign key to the separate customer table family.
- Customer data and account data may reside on different shards.
- Transfers between accounts may require distributed transaction handling when the accounts are on different shards.

## Direct comparison

| Requirement | Customer-ID design | Account-ID design |
|---|---|---|
| Customer profile lookup | One shard | One shard |
| Retrieve all customer accounts | One shard | Potentially multiple shards |
| Account lookup with account ID | Customer ID also useful for direct routing | Directly routed by account ID |
| Account ledger lookup | Local when customer ID is known | Local by account ID |
| Customer-account foreign key | Enforced | Not enforced across table families |
| Customer-wide transaction | Usually local | Potentially distributed |
| Account-to-ledger locality | Yes | Yes |
| Distribution of one customer's accounts | Same shard | Can span shards |
| Workload isolation by account | Limited | Stronger |

## Conclusion

For a retail banking model dominated by customer-wide operations, the customer-ID design is the stronger default because it preserves the complete customer hierarchy and referential integrity on one shard.

The account-ID design is preferable when most requests begin with an account number and account workloads must be distributed independently. Its main cost is weaker customer-level locality and the inability to enforce a foreign key between the independent customer and account table families.

For this project, the customer-ID design is recommended as the primary design. The account-ID design remains a valid alternative for account-centric transaction processing.

