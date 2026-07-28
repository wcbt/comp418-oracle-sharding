`# Limited Oracle GDD benchmark datasets

This implementation replaces the abandoned 10,000-customer preparation path
with three nested proof-of-concept datasets:

| Customers | Accounts | Ledger entries |
|---:|---:|---:|
| 5 | 10 | 50 |
| 10 | 20 | 100 |
| 20 | 40 | 200 |

Each customer has two accounts and each account has five ledger entries.
The same logical rows are loaded into `BANK_CUST` and `BANK_ACCT`.

The preparation script uses short sharding-key routing scans to choose customer
and account IDs represented on both shards. Generated CSV files use LF line
endings and are stored under `workload/generated/limited/`.

## Prepare all three datasets

```bash
./workload/limited/prepare_limited_datasets.sh
```

## Load one schema and size

```bash
./workload/limited/load_limited_dataset.sh BANK_CUST 5
./workload/limited/load_limited_dataset.sh BANK_ACCT 5
```

Repeat with `10` and `20` after completing the benchmark run for the previous
size. Loading a scenario removes only IDs in the reserved limited-benchmark
ranges from the selected schema before inserting the new scenario.
