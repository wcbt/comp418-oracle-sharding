# Step 10 — Customer-ID Sharding Verification

## Schema

Schema owner: `BANK_CUST`

Table family:

- `CUSTOMERS`: root sharded table
- `ACCOUNTS`: reference-partitioned child of `CUSTOMERS`
- `LEDGER_ENTRIES`: reference-partitioned child of `ACCOUNTS`

Sharding key: `CUSTOMER_ID`

## Distributed schema verification

- All three tables are valid on the shard catalog.
- All three tables propagated to `SHARD1PDB`.
- All three tables propagated to `SHARD2PDB`.
- Twelve chunks are configured.
- Six chunks are assigned to each shard.
- All primary-key, foreign-key, and check constraints are enabled.

## Test data

Twelve customer families were inserted through the catalog coordinator:

- 12 customer rows
- 12 account rows
- 12 ledger-entry rows

## Physical distribution

- `SHARD1PDB`: 6 customer families
- `SHARD2PDB`: 6 customer families
- Total: 12 customer families

For every test customer:

- The customer row and account row use the same partition.
- The account row and ledger row use the same partition.
- The co-location result is `YES`.

## Result

The customer-ID design distributes customer families evenly across the two
shards while preserving locality for customer, account, and ledger operations.
