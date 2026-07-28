#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import sys
import traceback
from collections import Counter
from pathlib import Path

import oracledb

ORACLE_HOME = os.environ["ORACLE_HOME"]
DB_DSN = os.environ["DB_DSN"]
BANK_CUST_PASSWORD = os.environ["BANK_CUST_PASSWORD"]
BANK_ACCT_PASSWORD = os.environ["BANK_ACCT_PASSWORD"]
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/tmp/comp418-limited-data"))

SCENARIO_SIZES = (5, 10, 20)
CUSTOMER_BASE = 700_000_001
ACCOUNT_BASE = 710_000_001
ENTRY_BASE = 720_000_001
TRANSFER_BASE = 730_000_001

_OPEN_POOLS: list[oracledb.ConnectionPool] = []


def route_key(pool: oracledb.ConnectionPool, key: int) -> dict[str, object]:
    with pool.acquire(shardingkey=[key]) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT SYS_CONTEXT('USERENV', 'CON_NAME'),
                       SYS_CONTEXT('USERENV', 'SERVER_HOST')
                FROM dual
                """
            )
            row = cursor.fetchone()

    if row is None:
        raise RuntimeError(f"No routing result for key={key}")

    container = str(row[0])
    host = str(row[1])

    if container.upper() == "SHARD1PDB" or host.lower().startswith("shard1"):
        shard = "shard1"
    elif container.upper() == "SHARD2PDB" or host.lower().startswith("shard2"):
        shard = "shard2"
    else:
        raise RuntimeError(
            f"Unexpected route for key={key}: container={container}, host={host}"
        )

    return {
        "key": key,
        "shard": shard,
        "container": container,
        "host": host,
    }


def select_balanced_keys(
    pool: oracledb.ConnectionPool,
    base: int,
    per_shard: int,
    label: str,
) -> dict[str, list[dict[str, object]]]:
    selected: dict[str, list[dict[str, object]]] = {
        "shard1": [],
        "shard2": [],
    }

    for offset in range(1000):
        route = route_key(pool, base + offset)
        shard = str(route["shard"])

        if len(selected[shard]) < per_shard:
            selected[shard].append(route)

        if (offset + 1) % 20 == 0:
            print(
                f"{label}_scan={offset + 1} "
                f"shard1={len(selected['shard1'])} "
                f"shard2={len(selected['shard2'])}",
                flush=True,
            )

        if all(len(selected[shard]) >= per_shard for shard in selected):
            return selected

    raise RuntimeError(
        f"Could not select {per_shard} {label} keys for each shard."
    )



def select_block(
    candidates: list[dict[str, object]],
    size: int,
    target_cust_s1: int,
    target_acct_s1: int,
) -> list[dict[str, object]] | None:
    states: dict[tuple[int, int, int], list[int]] = {(0, 0, 0): []}

    for index, candidate in enumerate(candidates):
        cust_inc = int(candidate["bank_cust_shard"] == "shard1")
        acct_inc = int(candidate["bank_acct_shard"] == "shard1")
        next_states = dict(states)

        for state, chosen in states.items():
            count, cust_s1, acct_s1 = state
            if count >= size:
                continue

            new_state = (count + 1, cust_s1 + cust_inc, acct_s1 + acct_inc)
            if (
                new_state[0] <= size
                and new_state[1] <= target_cust_s1
                and new_state[2] <= target_acct_s1
                and new_state not in next_states
            ):
                next_states[new_state] = chosen + [index]

        states = next_states

    indexes = states.get((size, target_cust_s1, target_acct_s1))
    if indexes is None:
        return None

    return [candidates[index] for index in indexes]


def choose_customer_sequence(
    bank_cust_pool: oracledb.ConnectionPool,
    bank_acct_pool: oracledb.ConnectionPool,
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []

    for offset in range(400):
        customer_id = CUSTOMER_BASE + offset
        cust_route = route_key(bank_cust_pool, customer_id)
        acct_route = route_key(bank_acct_pool, customer_id)

        candidates.append(
            {
                "key": customer_id,
                "bank_cust_shard": cust_route["shard"],
                "bank_cust_container": cust_route["container"],
                "bank_cust_host": cust_route["host"],
                "bank_acct_shard": acct_route["shard"],
                "bank_acct_container": acct_route["container"],
                "bank_acct_host": acct_route["host"],
            }
        )

        if len(candidates) % 20 == 0:
            print(f"customer_candidate_progress={len(candidates)}", flush=True)

        if len(candidates) < 20:
            continue

        for first_cust_target in (3, 2):
            for first_acct_target in (3, 2):
                block1 = select_block(
                    candidates, 5, first_cust_target, first_acct_target
                )
                if block1 is None:
                    continue

                used = {int(row["key"]) for row in block1}
                remaining1 = [
                    row for row in candidates if int(row["key"]) not in used
                ]

                block2 = select_block(
                    remaining1,
                    5,
                    5 - first_cust_target,
                    5 - first_acct_target,
                )
                if block2 is None:
                    continue

                used.update(int(row["key"]) for row in block2)
                remaining2 = [
                    row for row in candidates if int(row["key"]) not in used
                ]

                block3 = select_block(remaining2, 10, 5, 5)
                if block3 is not None:
                    return block1 + block2 + block3

    raise RuntimeError(
        "Could not select balanced nested customer samples for both schemas."
    )

def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def build_scenario(
    size: int,
    customers_selected: list[dict[str, object]],
    accounts_selected: list[dict[str, object]],
) -> dict[str, object]:
    customers: list[dict[str, object]] = []
    accounts: list[dict[str, object]] = []
    ledger: list[dict[str, object]] = []

    for customer_index in range(size):
        customer_id = int(customers_selected[customer_index]["key"])

        customers.append(
            {
                "customer_id": customer_id,
                "full_name": f"Limited Customer {customer_index + 1:03d}",
                "email": f"limited.customer{customer_index + 1:03d}@example.test",
                "customer_state": "ACTIVE",
            }
        )

        pair = accounts_selected[customer_index * 2 : customer_index * 2 + 2]

        for account_position, account_route in enumerate(pair):
            account_id = int(account_route["key"])
            account_type = "CHEQUING" if account_position == 0 else "SAVINGS"
            final_balance = 1000 if account_type == "CHEQUING" else 2000
            entry_amount = final_balance // 5

            accounts.append(
                {
                    "account_id": account_id,
                    "customer_id": customer_id,
                    "account_type": account_type,
                    "balance": f"{final_balance:.2f}",
                    "currency": "CAD",
                    "account_state": "ACTIVE",
                }
            )

            account_index = customer_index * 2 + account_position

            for entry_position in range(5):
                entry_offset = account_index * 5 + entry_position
                ledger.append(
                    {
                        "account_id": account_id,
                        "entry_id": ENTRY_BASE + entry_offset,
                        "transfer_id": TRANSFER_BASE + entry_offset,
                        "customer_id": customer_id,
                        "entry_type": "CREDIT",
                        "amount": f"{entry_amount:.2f}",
                        "balance_after": f"{entry_amount * (entry_position + 1):.2f}",
                        "counterparty_customer_id": "",
                        "counterparty_account_id": "",
                    }
                )

    scenario_dir = OUTPUT_ROOT / f"customers-{size}"

    write_csv(
        scenario_dir / "customers.csv",
        ["customer_id", "full_name", "email", "customer_state"],
        customers,
    )
    write_csv(
        scenario_dir / "accounts.csv",
        [
            "account_id",
            "customer_id",
            "account_type",
            "balance",
            "currency",
            "account_state",
        ],
        accounts,
    )
    write_csv(
        scenario_dir / "ledger_entries.csv",
        [
            "account_id",
            "entry_id",
            "transfer_id",
            "customer_id",
            "entry_type",
            "amount",
            "balance_after",
            "counterparty_customer_id",
            "counterparty_account_id",
        ],
        ledger,
    )

    manifest = {
        "scenario_size": size,
        "customers": len(customers),
        "accounts": len(accounts),
        "ledger_entries": len(ledger),
        "bank_cust_customer_distribution": dict(
            Counter(str(row["bank_cust_shard"]) for row in customers_selected[:size])
        ),
        "bank_acct_customer_distribution": dict(
            Counter(str(row["bank_acct_shard"]) for row in customers_selected[:size])
        ),
        "bank_acct_account_distribution": dict(
            Counter(str(row["shard"]) for row in accounts_selected[: size * 2])
        ),
    }

    (scenario_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    return manifest


def main() -> int:
    oracledb.init_oracle_client(lib_dir=os.path.join(ORACLE_HOME, "lib"))

    if oracledb.is_thin_mode():
        raise RuntimeError("Thick mode is required for sharding-key routing.")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    bank_cust_pool = oracledb.create_pool(
        user="BANK_CUST",
        password=BANK_CUST_PASSWORD,
        dsn=DB_DSN,
        min=0,
        max=8,
        increment=1,
    )
    bank_acct_pool = oracledb.create_pool(
        user="BANK_ACCT",
        password=BANK_ACCT_PASSWORD,
        dsn=DB_DSN,
        min=0,
        max=8,
        increment=1,
    )
    _OPEN_POOLS.extend([bank_cust_pool, bank_acct_pool])

    print("=== SELECT CUSTOMER IDS ===", flush=True)
    customer_sequence = choose_customer_sequence(
        bank_cust_pool,
        bank_acct_pool,
    )

    print("=== SELECT ACCOUNT IDS ===", flush=True)
    account_groups = select_balanced_keys(
        bank_acct_pool,
        ACCOUNT_BASE,
        20,
        "account",
    )

    account_sequence: list[dict[str, object]] = []
    for index in range(20):
        shard_order = (
            ("shard1", "shard2")
            if index % 2 == 0
            else ("shard2", "shard1")
        )
        for shard in shard_order:
            account_sequence.append(dict(account_groups[shard][index]))

    routing_manifest = {
        "scenario_sizes": list(SCENARIO_SIZES),
        "customer_sequence": customer_sequence,
        "account_sequence": account_sequence,
    }
    (OUTPUT_ROOT / "routing-manifest.json").write_text(
        json.dumps(routing_manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    manifests = []
    for size in SCENARIO_SIZES:
        manifest = build_scenario(size, customer_sequence, account_sequence)
        manifests.append(manifest)
        print(
            f"SCENARIO={size} CUSTOMERS={size} "
            f"ACCOUNTS={size * 2} LEDGER_ENTRIES={size * 10} STATUS=PASS",
            flush=True,
        )

    (OUTPUT_ROOT / "scenarios.json").write_text(
        json.dumps(manifests, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"OUTPUT_ROOT={OUTPUT_ROOT}", flush=True)
    print("LIMITED_DATASET_PREPARATION=PASS", flush=True)
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
