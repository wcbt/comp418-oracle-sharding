# COMP 418 Oracle Sharding Research Project

## Research question

How do shard-key selection and transaction locality affect query and
transaction performance in Oracle Globally Distributed AI Database?

## Designs

1. Sharding by `customer_id`
2. Sharding by `account_id`

## Main measurements

- Query and transaction latency
- Operations completed per second
- Successful and failed transactions
- Single-shard versus cross-shard performance
- Correctness of account balances after transfers
