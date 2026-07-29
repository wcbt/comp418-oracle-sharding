# Oracle GDD Benchmark Evidence Summary

## Benchmark status

The proof-of-concept benchmark produced sufficient evidence for the final
report. No additional infrastructure testing is required.

The environment used Oracle Database Free in Kubernetes and Minikube.
Oracle Free is not a supported production edition for Oracle Globally
Distributed Database. Results must therefore be interpreted as laboratory
proof-of-concept measurements rather than production performance claims.

## Validated data distribution

Two sharding strategies were implemented:

1. `BANK_CUST`: customer-ID-based sharding.
2. `BANK_ACCT`: account-ID-based sharding.

The main generated dataset contained:

- 10,000 customers
- 20,000 accounts
- 100,000 ledger entries

Limited datasets of 5, 10, and 20 customers were also generated, loaded,
and verified on both shards.

## Clean correctness baseline

The post-recovery smoke benchmark used:

- 5 customers
- concurrency 1
- 3 measured operations per workload
- 1 warm-up operation
- 1 repeat

Both `BANK_CUST` and `BANK_ACCT` completed all four workloads:

- customer account lookup
- individual account lookup
- same-customer transfer
- cross-customer transfer

The smoke run reported:

- zero failed summary rows
- combined results passed
- customer, account, and ledger counts unchanged
- total account balance unchanged

This is the primary correctness and routing validation.

## Isolated transfer-concurrency experiment

The usable isolated transfer run is:

`results/limited-benchmark/20260729T002319Z-transfer-smoke`

It tested concurrency levels 1, 5, and 10.

### BANK_CUST

| Workload | Concurrency | Status | p95 latency |
|---|---:|---|---:|
| Same-customer transfer | 1 | PASS | 2.617 ms |
| Same-customer transfer | 5 | PASS | 4.842 ms |
| Same-customer transfer | 10 | PASS | 6.414 ms |
| Cross-customer transfer | 1 | PASS | 9.697 ms |
| Cross-customer transfer | 5 | PASS | 30.387 ms |
| Cross-customer transfer | 10 | PASS | 45.826 ms |

Customer-ID sharding completed every tested transfer case successfully.
Cross-customer transfer latency increased with concurrency because the
operation crossed shard boundaries.

### BANK_ACCT

| Workload | Concurrency | Status | p95 latency |
|---|---:|---|---:|
| Same-customer transfer | 1 | PASS | 19.674 ms |
| Same-customer transfer | 5 | PASS | 15.324 ms |
| Same-customer transfer | 10 | PASS | 24.243 ms |
| Cross-customer transfer | 1 | PASS | 5.586 ms |
| Cross-customer transfer | 5 | FAIL: 1 failed operation | 169.739 ms |
| Cross-customer transfer | 10 | FAIL: 1 failed operation | 3210.106 ms |

Account-ID sharding completed same-customer transfers at every tested
concurrency level. Cross-customer transfers became unstable at concurrency
5 and 10.

These failures are part of the experimental result and must not be
presented as successful measurements.

## Earlier matrix execution

The earlier limited benchmark matrix produced usable lookup measurements:

- customer-account lookup passed at concurrency 1, 5, and 10
- individual-account lookup passed at concurrency 1, 5, and 10

The same execution later experienced transfer failures and
`ORA-12537: TNS:connection closed`.

The lookup measurements may be discussed, but the execution must be
identified as a partial matrix rather than a fully successful benchmark.

## Management-plane limitation

Repeated transfer-smoke reruns were stopped before workload execution
because the Kubernetes sharding custom resource oscillated among states
such as:

- `ONLINE_SHARD`
- `SHARD_ADDITION`
- `SHARD_ONLINE_ERROR_IN_GSM`
- `SHARD_ADDITION_ERROR_IN_GSM`
- `PROVISIONING`

During these oscillations, GDSCTL repeatedly reported:

- both shards registered
- both shards in `State: Ok`
- both shards available online
- both global services started
- four ready service-instance entries
- all five Kubernetes pods ready and running

The benchmark health gate was changed to use pod readiness and GDSCTL as
the authoritative data-plane checks while retaining the operator state as
diagnostic information.

This management-plane instability affected repeatability but did not
demonstrate corruption or failure of the completed smoke workload.

## Evidence-selection policy

The final report should use:

1. Distribution and schema evidence from Steps 10 through 14.
2. `step-15a-benchmark-smoke.txt` as the clean functional baseline.
3. `step-15a1-post-recovery-routing-smoke.txt` as post-recovery validation.
4. The isolated `20260729T002319Z-transfer-smoke` results for transfer
   concurrency comparison.
5. `step-15b-limited-benchmark-matrix.txt` only for completed lookup
   measurements and documented failure boundaries.
6. One representative archived log to explain operator instability.

Failed runs that never reached workload execution must not be included in
throughput or latency calculations.

## Final conclusion

The project demonstrated:

- deployment of two alternative sharding designs
- direct routing through Oracle GSM
- data distribution across two shards
- routed lookup and transfer workloads
- preserved row counts and total balances after successful tests
- measurable differences between customer-ID and account-ID partitioning
- the operational limitations of running Oracle GDD components on Oracle
  Database Free in a constrained local Kubernetes environment

The evidence is sufficient to proceed to the final report.
