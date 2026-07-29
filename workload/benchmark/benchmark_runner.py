#!/usr/bin/env python3
"""Limited Oracle GDD benchmark runner.

Runs routed operations through GSM and discovers physical placement through
direct shard connections. Transfer operations update two account balances and
always roll back, so the loaded dataset should remain unchanged.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterable

import oracledb


GSM_DSN = "//gsm1-0.gsm1.comp418-gdd.svc.cluster.local:1522/oltp_rw_svc.catalog.oradbcloud"
COORDINATOR_DSN = "//localhost:1521/GDS$CATALOG.oradbcloud"
SHARD_DSNS = {
    "shard1": "//shard1-0.shard1:1521/shard1pdb",
    "shard2": "//shard2-0.shard2:1521/shard2pdb",
}

CUSTOMER_MIN = 700_000_000
CUSTOMER_MAX = 700_999_999
ACCOUNT_MIN = 710_000_000
ACCOUNT_MAX = 710_999_999
LEDGER_MIN = 720_000_000
LEDGER_MAX = 720_999_999

SUPPORTED_SCHEMAS = {"BANK_CUST", "BANK_ACCT"}
SUPPORTED_SIZES = {5, 10, 20}
SUPPORTED_WORKLOADS = (
    "customer_account_lookup",
    "individual_account_lookup",
    "same_customer_transfer",
    "cross_customer_transfer",
)

# Keep Thick-mode connections alive until os._exit() bypasses native teardown.
OPEN_CONNECTIONS: list[Any] = []
OPEN_CONNECTIONS_LOCK = threading.Lock()


@dataclass(frozen=True)
class Account:
    account_id: int
    customer_id: int
    shard: str
    balance: Decimal


@dataclass(frozen=True)
class TransferPair:
    source: Account
    target: Account

    @property
    def expected_scope(self) -> str:
        return "single_shard" if self.source.shard == self.target.shard else "cross_shard"


@dataclass
class OperationResult:
    schema: str
    dataset_size: int
    workload: str
    concurrency: int
    repeat: int
    worker_id: int
    iteration: int
    latency_ms: float
    success: bool
    expected_scope: str
    customer_id: int | None = None
    source_customer_id: int | None = None
    target_customer_id: int | None = None
    account_id: int | None = None
    source_account_id: int | None = None
    target_account_id: int | None = None
    row_count: int | None = None
    error_type: str = ""
    error_message: str = ""


@dataclass
class Snapshot:
    customers: int
    accounts: int
    ledger_entries: int
    total_balance: str


@dataclass
class Topology:
    customer_shard: dict[int, str]
    accounts: list[Account]
    accounts_by_customer: dict[int, list[Account]]
    snapshot: Snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True, choices=sorted(SUPPORTED_SCHEMAS))
    parser.add_argument("--size", required=True, type=int, choices=sorted(SUPPORTED_SIZES))
    parser.add_argument(
        "--workloads",
        default=",".join(SUPPORTED_WORKLOADS),
        help="Comma-separated workload names.",
    )
    parser.add_argument(
        "--concurrencies",
        default="1,5,10",
        help="Comma-separated positive client counts.",
    )
    parser.add_argument("--iterations-per-client", type=int, default=10)
    parser.add_argument("--warmup-per-client", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--transfer-amount", type=Decimal, default=Decimal("1.00"))
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def parse_csv_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def configure_oracle_client() -> None:
    oracle_home = os.environ.get("ORACLE_HOME", "/opt/oracle/product/26ai/dbhomeFree")
    lib_dir = str(Path(oracle_home) / "lib")
    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
    except oracledb.ProgrammingError:
        # Already initialized in this interpreter.
        pass


def retain_connection(connection: Any) -> Any:
    with OPEN_CONNECTIONS_LOCK:
        OPEN_CONNECTIONS.append(connection)
    return connection


def connect(
    dsn: str,
    user: str,
    password: str,
    *,
    sharding_key: int | None = None,
) -> Any:
    arguments: dict[str, Any] = {
        "user": user,
        "password": password,
        "dsn": dsn,
    }
    if sharding_key is not None:
        arguments["shardingkey"] = [sharding_key]

    connection = oracledb.connect(**arguments)
    connection.call_timeout = 120_000
    return retain_connection(connection)


def safe_close(connection: Any | None) -> None:
    """Release the database session while retaining the Python object reference."""
    if connection is None:
        return
    try:
        connection.rollback()
    except Exception:
        pass
    try:
        connection.close()
    except Exception:
        pass


def decimal_text(value: Any) -> str:
    if value is None:
        return "0"
    return format(Decimal(value), "f")


def discover_topology(user: str, password: str, expected_size: int) -> Topology:
    customer_shard: dict[int, str] = {}
    accounts: list[Account] = []
    customer_count = 0
    account_count = 0
    ledger_count = 0
    total_balance = Decimal("0")

    for shard, dsn in SHARD_DSNS.items():
        connection = connect(dsn, user, password)
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT customer_id
            FROM customers
            WHERE customer_id BETWEEN :minimum AND :maximum
            ORDER BY customer_id
            """,
            {"minimum": CUSTOMER_MIN, "maximum": CUSTOMER_MAX},
        )
        shard_customers = [int(row[0]) for row in cursor]
        for customer_id in shard_customers:
            if customer_id in customer_shard:
                raise RuntimeError(f"Customer {customer_id} appeared on multiple shards.")
            customer_shard[customer_id] = shard
        customer_count += len(shard_customers)

        cursor.execute(
            """
            SELECT account_id, customer_id, balance
            FROM accounts
            WHERE account_id BETWEEN :minimum AND :maximum
            ORDER BY account_id
            """,
            {"minimum": ACCOUNT_MIN, "maximum": ACCOUNT_MAX},
        )
        shard_accounts = [
            Account(
                account_id=int(row[0]),
                customer_id=int(row[1]),
                shard=shard,
                balance=Decimal(row[2]),
            )
            for row in cursor
        ]
        accounts.extend(shard_accounts)
        account_count += len(shard_accounts)
        total_balance += sum((account.balance for account in shard_accounts), Decimal("0"))

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM ledger_entries
            WHERE entry_id BETWEEN :minimum AND :maximum
            """,
            {"minimum": LEDGER_MIN, "maximum": LEDGER_MAX},
        )
        ledger_count += int(cursor.fetchone()[0])
        safe_close(connection)

    expected_accounts = expected_size * 2
    expected_ledger = expected_accounts * 5

    actual = (customer_count, account_count, ledger_count)
    expected = (expected_size, expected_accounts, expected_ledger)
    if actual != expected:
        raise RuntimeError(
            "Loaded dataset does not match requested scenario: "
            f"actual={actual}, expected={expected}"
        )

    accounts_by_customer: dict[int, list[Account]] = defaultdict(list)
    for account in sorted(accounts, key=lambda item: item.account_id):
        accounts_by_customer[account.customer_id].append(account)

    missing_customers = sorted(set(customer_shard) - set(accounts_by_customer))
    if missing_customers:
        raise RuntimeError(f"Customers without accounts: {missing_customers}")

    invalid_groups = {
        customer_id: rows
        for customer_id, rows in accounts_by_customer.items()
        if len(rows) != 2
    }
    if invalid_groups:
        raise RuntimeError(
            "Every customer must have exactly two accounts; invalid customer IDs: "
            + ",".join(str(value) for value in sorted(invalid_groups))
        )

    return Topology(
        customer_shard=customer_shard,
        accounts=sorted(accounts, key=lambda item: item.account_id),
        accounts_by_customer={
            key: sorted(value, key=lambda item: item.account_id)
            for key, value in sorted(accounts_by_customer.items())
        },
        snapshot=Snapshot(
            customers=customer_count,
            accounts=account_count,
            ledger_entries=ledger_count,
            total_balance=decimal_text(total_balance),
        ),
    )


def build_direct_routing_keys(schema: str, topology: Topology) -> dict[str, int]:
    representatives: dict[str, int] = {}

    if schema == "BANK_CUST":
        for customer_id, shard in sorted(topology.customer_shard.items()):
            representatives.setdefault(shard, customer_id)
    elif schema == "BANK_ACCT":
        for account in topology.accounts:
            representatives.setdefault(account.shard, account.account_id)
    else:
        raise ValueError(schema)

    missing = sorted(set(SHARD_DSNS) - set(representatives))
    if missing:
        raise RuntimeError(
            f"No direct-routing key is available for shards: {','.join(missing)}"
        )

    return representatives


def uses_direct_routing(schema: str, workload: str) -> bool:
    return (
        (schema == "BANK_CUST" and workload == "customer_account_lookup")
        or (schema == "BANK_ACCT" and workload == "individual_account_lookup")
        or (schema == "BANK_CUST" and workload == "same_customer_transfer")
        or (schema == "BANK_ACCT" and workload == "cross_customer_transfer")
    )


def build_same_customer_pairs(topology: Topology) -> list[TransferPair]:
    pairs: list[TransferPair] = []
    for customer_id in sorted(topology.accounts_by_customer):
        first, second = topology.accounts_by_customer[customer_id]
        pairs.append(TransferPair(first, second))
    return pairs


def build_cross_customer_pairs(schema: str, topology: Topology) -> list[TransferPair]:
    pairs: list[TransferPair] = []

    if schema == "BANK_CUST":
        # Force different customer shards, which also forces different account shards.
        by_customer_shard: dict[str, list[Account]] = defaultdict(list)
        for customer_id, rows in topology.accounts_by_customer.items():
            by_customer_shard[topology.customer_shard[customer_id]].append(rows[0])

        left = sorted(by_customer_shard.get("shard1", []), key=lambda item: item.account_id)
        right = sorted(by_customer_shard.get("shard2", []), key=lambda item: item.account_id)
        for index in range(max(len(left), len(right))):
            if not left or not right:
                break
            pairs.append(TransferPair(left[index % len(left)], right[index % len(right)]))
    else:
        # Force different customers but the same account shard.
        by_account_shard: dict[str, list[Account]] = defaultdict(list)
        for account in topology.accounts:
            by_account_shard[account.shard].append(account)

        for shard in sorted(by_account_shard):
            rows = sorted(by_account_shard[shard], key=lambda item: (item.customer_id, item.account_id))
            for index, source in enumerate(rows):
                target = next(
                    (
                        candidate
                        for candidate in rows[index + 1 :] + rows[:index]
                        if candidate.customer_id != source.customer_id
                    ),
                    None,
                )
                if target is not None:
                    pairs.append(TransferPair(source, target))

    if not pairs:
        raise RuntimeError(f"No valid cross-customer transfer pairs for {schema}.")

    for pair in pairs:
        if pair.source.customer_id == pair.target.customer_id:
            raise RuntimeError("Cross-customer pair contains the same customer.")
        if schema == "BANK_CUST" and pair.expected_scope != "cross_shard":
            raise RuntimeError("BANK_CUST cross-customer pair was not cross-shard.")
        if schema == "BANK_ACCT" and pair.expected_scope != "single_shard":
            raise RuntimeError("BANK_ACCT cross-customer pair was not single-shard.")

    return pairs


def expected_lookup_scope(schema: str, workload: str) -> str:
    if workload == "customer_account_lookup":
        return "single_shard" if schema == "BANK_CUST" else "multi_shard"
    if workload == "individual_account_lookup":
        return "multi_shard" if schema == "BANK_CUST" else "single_shard"
    raise ValueError(workload)


def execute_customer_lookup(
    cursor: Any,
    customer_id: int,
) -> tuple[int, dict[str, int | None]]:
    cursor.execute(
        """
        SELECT account_id, customer_id, account_type, balance, currency, account_state
        FROM accounts
        WHERE customer_id = :customer_id
        ORDER BY account_id
        """,
        {"customer_id": customer_id},
    )
    rows = cursor.fetchall()
    if len(rows) != 2:
        raise RuntimeError(
            f"Customer lookup returned {len(rows)} rows for customer {customer_id}; expected 2."
        )
    return len(rows), {"customer_id": customer_id}


def execute_account_lookup(
    cursor: Any,
    account: Account,
) -> tuple[int, dict[str, int | None]]:
    cursor.execute(
        """
        SELECT account_id, customer_id, account_type, balance, currency, account_state
        FROM accounts
        WHERE account_id = :account_id
        """,
        {"account_id": account.account_id},
    )
    rows = cursor.fetchall()
    if len(rows) != 1:
        raise RuntimeError(
            f"Account lookup returned {len(rows)} rows for account {account.account_id}; expected 1."
        )
    return len(rows), {
        "customer_id": account.customer_id,
        "account_id": account.account_id,
    }


def execute_transfer(
    connection: Any,
    cursor: Any,
    pair: TransferPair,
    amount: Decimal,
) -> tuple[int, dict[str, int | None]]:
    """Apply a rolled-back transfer using a canonical account lock order.

    Concurrent benchmark pairs can overlap. Always touching the lower account ID
    first prevents cycles such as A->B, B->C, C->A from acquiring row locks in
    conflicting orders and producing artificial ORA-00060 deadlocks.
    """

    steps = sorted(
        (
            ("debit", pair.source),
            ("credit", pair.target),
        ),
        key=lambda item: item[1].account_id,
    )

    try:
        for action, account in steps:
            if action == "debit":
                cursor.execute(
                    """
                    UPDATE accounts
                    SET balance = balance - :amount
                    WHERE account_id = :account_id
                      AND customer_id = :customer_id
                      AND balance >= :amount
                    """,
                    {
                        "amount": amount,
                        "account_id": account.account_id,
                        "customer_id": account.customer_id,
                    },
                )
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Debit updated {cursor.rowcount} rows "
                        f"for account {account.account_id}."
                    )
            else:
                cursor.execute(
                    """
                    UPDATE accounts
                    SET balance = balance + :amount
                    WHERE account_id = :account_id
                      AND customer_id = :customer_id
                    """,
                    {
                        "amount": amount,
                        "account_id": account.account_id,
                        "customer_id": account.customer_id,
                    },
                )
                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"Credit updated {cursor.rowcount} rows "
                        f"for account {account.account_id}."
                    )

        connection.rollback()
        return 2, {
            "source_customer_id": pair.source.customer_id,
            "target_customer_id": pair.target.customer_id,
            "source_account_id": pair.source.account_id,
            "target_account_id": pair.target.account_id,
        }
    except Exception:
        connection.rollback()
        raise


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def worker_run(
    *,
    barrier: threading.Barrier,
    user: str,
    password: str,
    schema: str,
    dataset_size: int,
    workload: str,
    concurrency: int,
    repeat: int,
    worker_id: int,
    iterations: int,
    warmup: int,
    transfer_amount: Decimal,
    customers: list[int],
    customer_shard: dict[int, str],
    accounts: list[Account],
    same_pairs: list[TransferPair],
    cross_pairs: list[TransferPair],
    direct_routing_keys: dict[str, int],
) -> list[OperationResult]:
    direct_connections: dict[str, Any] = {}
    coordinator_connection = None

    try:
        direct_mode = uses_direct_routing(schema, workload)

        if direct_mode:
            for shard, sharding_key in sorted(direct_routing_keys.items()):
                direct_connections[shard] = connect(
                    GSM_DSN,
                    user,
                    password,
                    sharding_key=sharding_key,
                )
        else:
            coordinator_connection = connect(COORDINATOR_DSN, user, password)

        def choose_connection(shard: str) -> Any:
            if direct_mode:
                return direct_connections[shard]
            if coordinator_connection is None:
                raise RuntimeError("Coordinator connection was not initialized.")
            return coordinator_connection

        def perform(sequence_number: int) -> tuple[int, dict[str, int | None], str]:
            selection = worker_id + sequence_number

            if workload == "customer_account_lookup":
                customer_id = customers[selection % len(customers)]
                connection = choose_connection(customer_shard[customer_id])
                row_count, metadata = execute_customer_lookup(
                    connection.cursor(), customer_id
                )
                scope = expected_lookup_scope(schema, workload)

            elif workload == "individual_account_lookup":
                account = accounts[selection % len(accounts)]
                connection = choose_connection(account.shard)
                row_count, metadata = execute_account_lookup(
                    connection.cursor(), account
                )
                scope = expected_lookup_scope(schema, workload)

            elif workload == "same_customer_transfer":
                pair = same_pairs[selection % len(same_pairs)]
                connection = choose_connection(pair.source.shard)
                row_count, metadata = execute_transfer(
                    connection, connection.cursor(), pair, transfer_amount
                )
                scope = pair.expected_scope

            elif workload == "cross_customer_transfer":
                pair = cross_pairs[selection % len(cross_pairs)]
                connection = choose_connection(pair.source.shard)
                row_count, metadata = execute_transfer(
                    connection, connection.cursor(), pair, transfer_amount
                )
                scope = pair.expected_scope

            else:
                raise ValueError(workload)

            return row_count, metadata, scope

        for warmup_index in range(warmup):
            perform(-(warmup_index + 1))

        barrier.wait(timeout=180)

        results: list[OperationResult] = []
        for iteration in range(iterations):
            start_ns = time.perf_counter_ns()
            try:
                row_count, metadata, scope = perform(iteration)
                latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
                results.append(
                    OperationResult(
                        schema=schema,
                        dataset_size=dataset_size,
                        workload=workload,
                        concurrency=concurrency,
                        repeat=repeat,
                        worker_id=worker_id,
                        iteration=iteration,
                        latency_ms=latency_ms,
                        success=True,
                        expected_scope=scope,
                        row_count=row_count,
                        **metadata,
                    )
                )
            except Exception as exc:
                for connection in [coordinator_connection, *direct_connections.values()]:
                    if connection is None:
                        continue
                    try:
                        connection.rollback()
                    except Exception:
                        pass

                latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
                results.append(
                    OperationResult(
                        schema=schema,
                        dataset_size=dataset_size,
                        workload=workload,
                        concurrency=concurrency,
                        repeat=repeat,
                        worker_id=worker_id,
                        iteration=iteration,
                        latency_ms=latency_ms,
                        success=False,
                        expected_scope="unknown",
                        error_type=type(exc).__name__,
                        error_message=str(exc)[:500],
                    )
                )
        return results

    except Exception as exc:
        try:
            barrier.abort()
        except Exception:
            pass
        return [
            OperationResult(
                schema=schema,
                dataset_size=dataset_size,
                workload=workload,
                concurrency=concurrency,
                repeat=repeat,
                worker_id=worker_id,
                iteration=-1,
                latency_ms=0.0,
                success=False,
                expected_scope="unknown",
                error_type=type(exc).__name__,
                error_message=f"Worker setup failed: {str(exc)[:450]}",
            )
        ]
    finally:
        safe_close(coordinator_connection)
        for connection in direct_connections.values():
            safe_close(connection)


def run_scenario(
    *,
    user: str,
    password: str,
    schema: str,
    dataset_size: int,
    workload: str,
    concurrency: int,
    repeat: int,
    iterations: int,
    warmup: int,
    transfer_amount: Decimal,
    topology: Topology,
    same_pairs: list[TransferPair],
    cross_pairs: list[TransferPair],
    direct_routing_keys: dict[str, int],
) -> tuple[list[OperationResult], float]:
    barrier = threading.Barrier(concurrency + 1)
    customers = sorted(topology.accounts_by_customer)
    start_ns = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                worker_run,
                barrier=barrier,
                user=user,
                password=password,
                schema=schema,
                dataset_size=dataset_size,
                workload=workload,
                concurrency=concurrency,
                repeat=repeat,
                worker_id=worker_id,
                iterations=iterations,
                warmup=warmup,
                transfer_amount=transfer_amount,
                customers=customers,
                customer_shard=topology.customer_shard,
                accounts=topology.accounts,
                same_pairs=same_pairs,
                cross_pairs=cross_pairs,
                direct_routing_keys=direct_routing_keys,
            )
            for worker_id in range(concurrency)
        ]

        try:
            start_ns = time.perf_counter_ns()
            barrier.wait(timeout=180)
        except threading.BrokenBarrierError:
            pass

        results: list[OperationResult] = []
        for future in as_completed(futures):
            results.extend(future.result())

    elapsed_seconds = max((time.perf_counter_ns() - start_ns) / 1_000_000_000, 0.000001)
    return sorted(
        results,
        key=lambda row: (row.worker_id, row.iteration),
    ), elapsed_seconds


def summary_row(
    results: list[OperationResult],
    elapsed_seconds: float,
) -> dict[str, Any]:
    sample = results[0]
    successful_latencies = [row.latency_ms for row in results if row.success]
    success_count = sum(1 for row in results if row.success)
    failure_count = len(results) - success_count
    scopes = sorted({row.expected_scope for row in results if row.success})

    return {
        "schema": sample.schema,
        "dataset_size": sample.dataset_size,
        "workload": sample.workload,
        "concurrency": sample.concurrency,
        "repeat": sample.repeat,
        "expected_scope": ",".join(scopes) if scopes else "unknown",
        "attempted_operations": len(results),
        "successful_operations": success_count,
        "failed_operations": failure_count,
        "elapsed_seconds": round(elapsed_seconds, 6),
        "throughput_ops_per_second": round(len(results) / elapsed_seconds, 6),
        "latency_min_ms": round(min(successful_latencies), 6) if successful_latencies else None,
        "latency_mean_ms": round(statistics.fmean(successful_latencies), 6)
        if successful_latencies
        else None,
        "latency_p50_ms": round(percentile(successful_latencies, 0.50), 6)
        if successful_latencies
        else None,
        "latency_p95_ms": round(percentile(successful_latencies, 0.95), 6)
        if successful_latencies
        else None,
        "latency_p99_ms": round(percentile(successful_latencies, 0.99), 6)
        if successful_latencies
        else None,
        "latency_max_ms": round(max(successful_latencies), 6) if successful_latencies else None,
        "status": "PASS" if failure_count == 0 else "FAIL",
    }


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    user = os.environ.get("DB_USER", args.schema)
    password = os.environ.get("DB_PASSWORD", "")
    if not password:
        raise RuntimeError("DB_PASSWORD is required.")
    if user != args.schema:
        raise RuntimeError(f"DB_USER={user} does not match --schema={args.schema}.")
    if args.iterations_per_client <= 0:
        raise ValueError("--iterations-per-client must be positive.")
    if args.warmup_per_client < 0:
        raise ValueError("--warmup-per-client cannot be negative.")
    if args.repeats <= 0:
        raise ValueError("--repeats must be positive.")
    if args.transfer_amount <= 0:
        raise ValueError("--transfer-amount must be positive.")

    workloads = parse_csv_list(args.workloads)
    unknown_workloads = sorted(set(workloads) - set(SUPPORTED_WORKLOADS))
    if unknown_workloads:
        raise ValueError(f"Unknown workloads: {unknown_workloads}")

    concurrencies = [int(value) for value in parse_csv_list(args.concurrencies)]
    if not concurrencies or any(value <= 0 for value in concurrencies):
        raise ValueError("All concurrency values must be positive.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    configure_oracle_client()
    print("=== BENCHMARK TOPOLOGY DISCOVERY ===", flush=True)
    topology_before = discover_topology(user, password, args.size)
    same_pairs = build_same_customer_pairs(topology_before)
    cross_pairs = build_cross_customer_pairs(args.schema, topology_before)
    direct_routing_keys = build_direct_routing_keys(args.schema, topology_before)

    same_scopes = sorted({pair.expected_scope for pair in same_pairs})
    cross_scopes = sorted({pair.expected_scope for pair in cross_pairs})
    print(f"SCHEMA={args.schema}", flush=True)
    print(f"DATASET_SIZE={args.size}", flush=True)
    print(f"SNAPSHOT_BEFORE={json.dumps(asdict(topology_before.snapshot), sort_keys=True)}", flush=True)
    print(f"COORDINATOR_DSN={COORDINATOR_DSN}", flush=True)
    print(
        f"DIRECT_ROUTING_KEYS={json.dumps(direct_routing_keys, sort_keys=True)}",
        flush=True,
    )
    print(f"SAME_CUSTOMER_TRANSFER_SCOPES={','.join(same_scopes)}", flush=True)
    print(f"CROSS_CUSTOMER_TRANSFER_SCOPES={','.join(cross_scopes)}", flush=True)

    operation_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for workload in workloads:
        for concurrency in concurrencies:
            for repeat in range(1, args.repeats + 1):
                print(
                    "RUN"
                    f"|schema={args.schema}"
                    f"|size={args.size}"
                    f"|workload={workload}"
                    f"|concurrency={concurrency}"
                    f"|repeat={repeat}",
                    flush=True,
                )
                results, elapsed_seconds = run_scenario(
                    user=user,
                    password=password,
                    schema=args.schema,
                    dataset_size=args.size,
                    workload=workload,
                    concurrency=concurrency,
                    repeat=repeat,
                    iterations=args.iterations_per_client,
                    warmup=args.warmup_per_client,
                    transfer_amount=args.transfer_amount,
                    topology=topology_before,
                    same_pairs=same_pairs,
                    cross_pairs=cross_pairs,
                    direct_routing_keys=direct_routing_keys,
                )
                row = summary_row(results, elapsed_seconds)
                summary_rows.append(row)
                operation_rows.extend(asdict(result) for result in results)
                print(
                    "RESULT"
                    f"|status={row['status']}"
                    f"|attempted={row['attempted_operations']}"
                    f"|failed={row['failed_operations']}"
                    f"|throughput={row['throughput_ops_per_second']}"
                    f"|p95_ms={row['latency_p95_ms']}",
                    flush=True,
                )

    print("=== POST-BENCHMARK STATE VERIFICATION ===", flush=True)
    topology_after = discover_topology(user, password, args.size)
    print(f"SNAPSHOT_AFTER={json.dumps(asdict(topology_after.snapshot), sort_keys=True)}", flush=True)

    state_unchanged = topology_before.snapshot == topology_after.snapshot
    print(f"DATASET_STATE_UNCHANGED={'PASS' if state_unchanged else 'FAIL'}", flush=True)

    operation_fields = [field.name for field in OperationResult.__dataclass_fields__.values()]
    summary_fields = list(summary_rows[0].keys())

    write_csv(output_dir / "operations.csv", operation_rows, operation_fields)
    write_csv(output_dir / "summary.csv", summary_rows, summary_fields)

    status = (
        "PASS"
        if state_unchanged and all(row["status"] == "PASS" for row in summary_rows)
        else "FAIL"
    )
    payload = {
        "metadata": {
            "schema": args.schema,
            "dataset_size": args.size,
            "workloads": workloads,
            "concurrencies": concurrencies,
            "iterations_per_client": args.iterations_per_client,
            "warmup_per_client": args.warmup_per_client,
            "repeats": args.repeats,
            "transfer_amount": str(args.transfer_amount),
            "gsm_dsn": GSM_DSN,
            "coordinator_dsn": COORDINATOR_DSN,
            "direct_routing_keys": direct_routing_keys,
            "routing_policy": {
                workload: (
                    "direct" if uses_direct_routing(args.schema, workload) else "coordinator"
                )
                for workload in workloads
            },
            "python_version": sys.version,
            "oracledb_version": oracledb.__version__,
            "thick_mode": not oracledb.is_thin_mode(),
        },
        "snapshot_before": asdict(topology_before.snapshot),
        "snapshot_after": asdict(topology_after.snapshot),
        "state_unchanged": state_unchanged,
        "summary": summary_rows,
        "status": status,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"OUTPUT_DIR={output_dir}", flush=True)
    print(f"BENCHMARK_RUNNER={status}", flush=True)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = main()
    except Exception as exc:
        print(f"BENCHMARK_RUNNER=FAIL", file=sys.stderr, flush=True)
        print(f"ERROR_TYPE={type(exc).__name__}", file=sys.stderr, flush=True)
        print(f"ERROR_MESSAGE={exc}", file=sys.stderr, flush=True)
        exit_code = 1
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)
