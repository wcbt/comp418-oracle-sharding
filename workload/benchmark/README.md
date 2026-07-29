# Limited Oracle GDD benchmark runner

This runner compares the `BANK_CUST` and `BANK_ACCT` designs with the
5-, 10-, and 20-customer datasets.

Workloads:

1. `customer_account_lookup`
2. `individual_account_lookup`
3. `same_customer_transfer`
4. `cross_customer_transfer`

The transfer workloads update two balances through GSM and issue `ROLLBACK`
after every operation. No transfer changes are intended to persist.

Pair selection intentionally exposes the shard-key tradeoff:

| Workload | BANK_CUST | BANK_ACCT |
|---|---|---|
| Customer account lookup | Single-shard expected | Multi-shard expected |
| Individual account lookup | Multi-shard expected | Single-shard expected |
| Same-customer transfer | Single-shard pair | Cross-shard pair |
| Cross-customer transfer | Cross-shard pair | Single-shard pair |

The runner uses standalone Thick-mode connections rather than an Oracle
connection pool. It exits with `os._exit()` after flushing results to avoid the
native teardown path that previously caused exit 139.

## First gate: smoke test

```bash
chmod +x workload/benchmark/run_limited_benchmark.sh
./workload/benchmark/run_limited_benchmark.sh smoke
```

The smoke test reloads `BANK_CUST` with five customers and runs all four
workloads at concurrency 1 with one repeat.

Expected final markers:

```text
DATASET_STATE_UNCHANGED=PASS
BENCHMARK_RUNNER=PASS
COMBINED_RESULTS=PASS
LIMITED_BENCHMARK_SMOKE=PASS
```

## Full matrix

Run only after the smoke test passes:

```bash
./workload/benchmark/run_limited_benchmark.sh full
```

Full settings:

- schemas: `BANK_CUST`, `BANK_ACCT`
- sizes: `5`, `10`, `20`
- concurrency: `1`, `5`, `10`
- measured operations: `10` per client
- warm-up operations: `2` per client
- repeats: `3`

Results are written below:

```text
results/limited-benchmark/<UTC-run-id>-<mode>/
```

Important files:

- `combined_summary.csv`: all scenario summaries
- `combined_summary.json`: machine-readable combined output
- `<schema>-customers-<size>/operations.csv`: individual operation latency
- `<schema>-customers-<size>/summary.csv`: scenario summaries
- `<schema>-customers-<size>/summary.json`: metadata and state verification
- `<schema>-customers-<size>/runner.log`: console transcript

Evidence files:

- `evidence/step-15a-benchmark-smoke.txt`
- `evidence/step-15b-limited-benchmark-matrix.txt`
