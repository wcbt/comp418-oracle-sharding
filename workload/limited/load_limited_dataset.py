#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import sys
import traceback
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import oracledb

ORACLE_HOME = os.environ["ORACLE_HOME"]
DB_DSN = os.environ["DB_DSN"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
SCENARIO_SIZE = int(os.environ["SCENARIO_SIZE"])
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/tmp/comp418-limited-data"))

DIRECT_DSNS = {
    "shard1": "//shard1-0.shard1:1521/shard1pdb",
    "shard2": "//shard2-0.shard2:1521/shard2pdb",
}

CUSTOMER_MIN = 700_000_001
CUSTOMER_MAX = 700_000_999
ACCOUNT_MIN = 710_000_001
ACCOUNT_MAX = 710_000_999

_OPEN_POOLS: list[oracledb.ConnectionPool] = []


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def cleanup_benchmark_range() -> None:
    print("=== CLEANING LIMITED BENCHMARK RANGE ===", flush=True)

    for shard, dsn in DIRECT_DSNS.items():
        with oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=dsn,
        ) as connection:
            with connection.cursor() as cursor:
                binds = {
                    "customer_min": CUSTOMER_MIN,
                    "customer_max": CUSTOMER_MAX,
                    "account_min": ACCOUNT_MIN,
                    "account_max": ACCOUNT_MAX,
                }

                cursor.execute(
                    """
                    DELETE FROM ledger_entries
                    WHERE customer_id BETWEEN :customer_min AND :customer_max
                       OR account_id BETWEEN :account_min AND :account_max
                    """,
                    binds,
                )
                ledger_deleted = cursor.rowcount

                cursor.execute(
                    """
                    DELETE FROM accounts
                    WHERE customer_id BETWEEN :customer_min AND :customer_max
                       OR account_id BETWEEN :account_min AND :account_max
                    """,
                    binds,
                )
                accounts_deleted = cursor.rowcount

                cursor.execute(
                    """
                    DELETE FROM customers
                    WHERE customer_id BETWEEN :customer_min AND :customer_max
                    """,
                    {
                        "customer_min": CUSTOMER_MIN,
                        "customer_max": CUSTOMER_MAX,
                    },
                )
                customers_deleted = cursor.rowcount

            connection.commit()

        print(
            f"{shard}|customers_deleted={customers_deleted}|"
            f"accounts_deleted={accounts_deleted}|"
            f"ledger_deleted={ledger_deleted}",
            flush=True,
        )


def ledger_bind(row: dict[str, str]) -> list[object]:
    return [
        int(row["account_id"]),
        int(row["entry_id"]),
        int(row["transfer_id"]),
        int(row["customer_id"]),
        row["entry_type"],
        Decimal(row["amount"]),
        Decimal(row["balance_after"]),
        (
            int(row["counterparty_customer_id"])
            if row["counterparty_customer_id"]
            else None
        ),
        (
            int(row["counterparty_account_id"])
            if row["counterparty_account_id"]
            else None
        ),
    ]


def insert_bank_cust(
    pool: oracledb.ConnectionPool,
    customers: list[dict[str, str]],
    accounts: list[dict[str, str]],
    ledger_entries: list[dict[str, str]],
) -> None:
    accounts_by_customer: dict[int, list[dict[str, str]]] = defaultdict(list)
    ledger_by_customer: dict[int, list[dict[str, str]]] = defaultdict(list)

    for row in accounts:
        accounts_by_customer[int(row["customer_id"])].append(row)

    for row in ledger_entries:
        ledger_by_customer[int(row["customer_id"])].append(row)

    for customer in customers:
        customer_id = int(customer["customer_id"])

        with pool.acquire(shardingkey=[customer_id]) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO customers (
                        customer_id, full_name, email, customer_state
                    )
                    VALUES (:1, :2, :3, :4)
                    """,
                    [
                        customer_id,
                        customer["full_name"],
                        customer["email"],
                        customer["customer_state"],
                    ],
                )

                cursor.executemany(
                    """
                    INSERT INTO accounts (
                        account_id, customer_id, account_type,
                        balance, currency, account_state
                    )
                    VALUES (:1, :2, :3, :4, :5, :6)
                    """,
                    [
                        [
                            int(row["account_id"]),
                            customer_id,
                            row["account_type"],
                            Decimal(row["balance"]),
                            row["currency"],
                            row["account_state"],
                        ]
                        for row in accounts_by_customer[customer_id]
                    ],
                )

                cursor.executemany(
                    """
                    INSERT INTO ledger_entries (
                        account_id, entry_id, transfer_id, customer_id,
                        entry_type, amount, balance_after,
                        counterparty_customer_id, counterparty_account_id
                    )
                    VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9)
                    """,
                    [
                        ledger_bind(row)
                        for row in ledger_by_customer[customer_id]
                    ],
                )

            connection.commit()

        print(f"loaded_customer_id={customer_id}", flush=True)


def insert_bank_acct(
    pool: oracledb.ConnectionPool,
    customers: list[dict[str, str]],
    accounts: list[dict[str, str]],
    ledger_entries: list[dict[str, str]],
) -> None:
    ledger_by_account: dict[int, list[dict[str, str]]] = defaultdict(list)

    for row in ledger_entries:
        ledger_by_account[int(row["account_id"])].append(row)

    for customer in customers:
        customer_id = int(customer["customer_id"])

        with pool.acquire(shardingkey=[customer_id]) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO customers (
                        customer_id, full_name, email, customer_state
                    )
                    VALUES (:1, :2, :3, :4)
                    """,
                    [
                        customer_id,
                        customer["full_name"],
                        customer["email"],
                        customer["customer_state"],
                    ],
                )
            connection.commit()

        print(f"loaded_customer_id={customer_id}", flush=True)

    for account in accounts:
        account_id = int(account["account_id"])

        with pool.acquire(shardingkey=[account_id]) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO accounts (
                        account_id, customer_id, account_type,
                        balance, currency, account_state
                    )
                    VALUES (:1, :2, :3, :4, :5, :6)
                    """,
                    [
                        account_id,
                        int(account["customer_id"]),
                        account["account_type"],
                        Decimal(account["balance"]),
                        account["currency"],
                        account["account_state"],
                    ],
                )

                cursor.executemany(
                    """
                    INSERT INTO ledger_entries (
                        account_id, entry_id, transfer_id, customer_id,
                        entry_type, amount, balance_after,
                        counterparty_customer_id, counterparty_account_id
                    )
                    VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9)
                    """,
                    [ledger_bind(row) for row in ledger_by_account[account_id]],
                )

            connection.commit()

        print(f"loaded_account_id={account_id}", flush=True)


def query_shard_counts(shard: str, dsn: str) -> dict[str, int]:
    with oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=dsn,
    ) as connection:
        with connection.cursor() as cursor:
            binds = {
                "customer_min": CUSTOMER_MIN,
                "customer_max": CUSTOMER_MAX,
                "account_min": ACCOUNT_MIN,
                "account_max": ACCOUNT_MAX,
            }

            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM customers
                     WHERE customer_id BETWEEN :customer_min AND :customer_max),
                    (SELECT COUNT(*) FROM accounts
                     WHERE customer_id BETWEEN :customer_min AND :customer_max
                        OR account_id BETWEEN :account_min AND :account_max),
                    (SELECT COUNT(*) FROM ledger_entries
                     WHERE customer_id BETWEEN :customer_min AND :customer_max
                        OR account_id BETWEEN :account_min AND :account_max)
                FROM dual
                """,
                binds,
            )
            row = cursor.fetchone()

            if row is None:
                raise RuntimeError(f"No count row returned for {shard}.")

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT account_id
                    FROM ledger_entries
                    WHERE account_id BETWEEN :account_min AND :account_max
                    GROUP BY account_id
                    HAVING COUNT(*) <> 5
                )
                """,
                {
                    "account_min": ACCOUNT_MIN,
                    "account_max": ACCOUNT_MAX,
                },
            )
            invalid_ledger_groups = int(cursor.fetchone()[0])

    return {
        "customers": int(row[0]),
        "accounts": int(row[1]),
        "ledger_entries": int(row[2]),
        "invalid_ledger_groups": invalid_ledger_groups,
    }


def main() -> int:
    if DB_USER not in {"BANK_CUST", "BANK_ACCT"}:
        raise RuntimeError("DB_USER must be BANK_CUST or BANK_ACCT.")

    if SCENARIO_SIZE not in {5, 10, 20}:
        raise RuntimeError("SCENARIO_SIZE must be 5, 10, or 20.")

    scenario_dir = DATA_ROOT / f"customers-{SCENARIO_SIZE}"
    customers = read_csv(scenario_dir / "customers.csv")
    accounts = read_csv(scenario_dir / "accounts.csv")
    ledger_entries = read_csv(scenario_dir / "ledger_entries.csv")

    expected = {
        "customers": SCENARIO_SIZE,
        "accounts": SCENARIO_SIZE * 2,
        "ledger_entries": SCENARIO_SIZE * 10,
    }
    actual = {
        "customers": len(customers),
        "accounts": len(accounts),
        "ledger_entries": len(ledger_entries),
    }

    if actual != expected:
        raise RuntimeError(f"Source counts are wrong: actual={actual}, expected={expected}")

    oracledb.init_oracle_client(lib_dir=os.path.join(ORACLE_HOME, "lib"))

    if oracledb.is_thin_mode():
        raise RuntimeError("Thick mode is required for sharding-key routing.")

    print(f"DB_USER={DB_USER} SCENARIO_SIZE={SCENARIO_SIZE}", flush=True)
    cleanup_benchmark_range()

    pool = oracledb.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        min=0,
        max=8,
        increment=1,
    )
    _OPEN_POOLS.append(pool)

    print("=== INSERTING LIMITED DATASET ===", flush=True)

    if DB_USER == "BANK_CUST":
        insert_bank_cust(pool, customers, accounts, ledger_entries)
    else:
        insert_bank_acct(pool, customers, accounts, ledger_entries)

    print("=== VERIFYING DIRECT SHARD COUNTS ===", flush=True)
    shard_counts = {
        shard: query_shard_counts(shard, dsn)
        for shard, dsn in DIRECT_DSNS.items()
    }
    totals = {
        key: sum(shard_counts[shard][key] for shard in DIRECT_DSNS)
        for key in ("customers", "accounts", "ledger_entries")
    }

    for shard in ("shard1", "shard2"):
        counts = shard_counts[shard]
        print(
            f"{shard}|customers={counts['customers']}|"
            f"accounts={counts['accounts']}|"
            f"ledger_entries={counts['ledger_entries']}|"
            f"invalid_ledger_groups={counts['invalid_ledger_groups']}",
            flush=True,
        )

    print(
        f"TOTALS|customers={totals['customers']}|accounts={totals['accounts']}|"
        f"ledger_entries={totals['ledger_entries']}",
        flush=True,
    )

    if totals != expected:
        raise RuntimeError(f"Post-load totals are wrong: {totals}")

    if any(
        shard_counts[shard]["invalid_ledger_groups"] != 0
        for shard in DIRECT_DSNS
    ):
        raise RuntimeError("At least one account does not have five ledger entries.")

    if any(shard_counts[shard]["accounts"] == 0 for shard in DIRECT_DSNS):
        raise RuntimeError("Accounts are not represented on both shards.")

    summary = {
        "database_user": DB_USER,
        "scenario_size": SCENARIO_SIZE,
        "expected_counts": expected,
        "shard_counts": shard_counts,
        "totals": totals,
        "status": "PASS",
    }
    print(json.dumps(summary, indent=2), flush=True)
    print("LIMITED_DATASET_LOAD=PASS", flush=True)
    return 0


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = main()
    except Exception:
        traceback.print_exc()
        exit_code = 1
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)
