# Decision: Switch to a Limited Benchmark Dataset

Date: 2026-07-28

The original 10,000-customer preparation path was discontinued after repeated
native process crashes.

The customer-ID partition utility successfully routed all 10,000 customer keys,
but the Python process repeatedly terminated with exit code 139 before writing
the partitioned CSV files. Removing the explicit Oracle connection-pool close
did not change the failure.

The earlier large SQL*Loader attempt also caused an Oracle server-process crash
while loading the shard2 ledger file.

To keep the project aligned with its research objective and complete it within
the available time, the benchmark will use three controlled dataset sizes:

- 5 customers, 10 accounts, 50 ledger entries
- 10 customers, 20 accounts, 100 ledger entries
- 20 customers, 40 accounts, 200 ledger entries

Both customer-ID and account-ID designs will use equivalent logical data.
Customer and account identifiers will be selected so that both shards are
represented. Loading will use small routed DML operations instead of large
partitioned SQL*Loader files.

The reduced scale will be disclosed as an experimental limitation. The
benchmark will focus on shard-key selection, transaction locality, latency,
throughput, success rate, and balance correctness rather than production-scale
capacity.
