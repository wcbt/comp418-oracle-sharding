#!/usr/bin/env python3

import csv
import json
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

import oracledb


# Retain the one-shot routing pool until os._exit() so the completed
# partition files are not lost to an Oracle Client teardown crash.
_OPEN_POOLS = []


ORACLE_HOME = os.environ["ORACLE_HOME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_DSN = os.environ["DB_DSN"]

INPUT_DIR = Path(
    os.environ.get(
        "INPUT_DIR",
        "/tmp/comp418-benchmark-10k",
    )
)

OUTPUT_DIR = Path(
    os.environ.get(
        "OUTPUT_DIR",
        "/tmp/comp418-benchmark-10k/partitioned/bank_cust",
    )
)

EXPECTED_FILES = (
    "customers.csv",
    "accounts.csv",
    "ledger_entries.csv",
)

EXPECTED_COUNTS = {
    "customers.csv": 10_000,
    "accounts.csv": 20_000,
    "ledger_entries.csv": 100_000,
}


def validate_inputs() -> None:
    for filename in EXPECTED_FILES:
        path = INPUT_DIR / filename

        if not path.is_file():
            raise FileNotFoundError(f"Missing input file: {path}")


def load_customer_ids() -> list[int]:
    customer_ids: list[int] = []
    seen: set[int] = set()

    path = INPUT_DIR / "customers.csv"

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        if "customer_id" not in (reader.fieldnames or []):
            raise RuntimeError(
                f"{path} does not contain customer_id."
            )

        for row in reader:
            customer_id = int(row["customer_id"])

            if customer_id in seen:
                raise RuntimeError(
                    f"Duplicate customer_id detected: {customer_id}"
                )

            seen.add(customer_id)
            customer_ids.append(customer_id)

    if len(customer_ids) != EXPECTED_COUNTS["customers.csv"]:
        raise RuntimeError(
            "Unexpected customer count: "
            f"{len(customer_ids)}"
        )

    return customer_ids


def normalize_shard(container: str, host: str) -> str:
    container_upper = container.upper()
    host_lower = host.lower()

    if container_upper == "SHARD1PDB" or host_lower.startswith("shard1"):
        return "shard1"

    if container_upper == "SHARD2PDB" or host_lower.startswith("shard2"):
        return "shard2"

    raise RuntimeError(
        "Unexpected routing destination: "
        f"container={container}, host={host}"
    )


def locate_customer(
    pool: oracledb.ConnectionPool,
    customer_id: int,
) -> tuple[str, str, str]:
    last_error: Exception | None = None

    for attempt in range(1, 4):
        connection = None

        try:
            connection = pool.acquire(
                shardingkey=[customer_id]
            )

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        SYS_CONTEXT('USERENV', 'CON_NAME'),
                        SYS_CONTEXT('USERENV', 'SERVER_HOST')
                    FROM dual
                    """
                )

                row = cursor.fetchone()

                if row is None:
                    raise RuntimeError(
                        "Routing query returned no row."
                    )

                container = str(row[0])
                host = str(row[1])
                shard = normalize_shard(container, host)

                return shard, container, host

        except Exception as exc:
            last_error = exc

            if attempt < 3:
                time.sleep(0.25 * attempt)

        finally:
            if connection is not None:
                connection.close()

    raise RuntimeError(
        f"Could not route customer_id={customer_id}"
    ) from last_error


def build_customer_mapping(
    customer_ids: list[int],
) -> tuple[dict[int, str], dict[str, dict[str, object]]]:
    pool = oracledb.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        min=0,
        max=8,
        increment=1,
    )

    mapping: dict[int, str] = {}
    representatives: dict[str, dict[str, object]] = {}

    try:
        for index, customer_id in enumerate(customer_ids, start=1):
            shard, container, host = locate_customer(
                pool,
                customer_id,
            )

            mapping[customer_id] = shard

            representatives.setdefault(
                shard,
                {
                    "customer_id": customer_id,
                    "container": container,
                    "host": host,
                },
            )

            if index % 1000 == 0 or index == len(customer_ids):
                print(
                    "routing_progress="
                    f"{index}/{len(customer_ids)}",
                    flush=True,
                )

    finally:
        # Routing has repeatedly completed all 10,000 keys and then
        # segfaulted while closing this Thick-mode connection pool.
        # Keep it referenced until the one-shot process exits.
        _OPEN_POOLS.append(pool)

    if set(representatives) != {"shard1", "shard2"}:
        raise RuntimeError(
            "Routing did not identify both expected shards: "
            f"{sorted(representatives)}"
        )

    return mapping, representatives


def split_csv(
    filename: str,
    mapping: dict[int, str],
) -> dict[str, int]:
    source = INPUT_DIR / filename

    shard_paths = {
        "shard1": OUTPUT_DIR / "shard1" / filename,
        "shard2": OUTPUT_DIR / "shard2" / filename,
    }

    handles = {}
    writers = {}
    counts = Counter()

    try:
        with source.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as input_handle:
            reader = csv.DictReader(input_handle)

            fieldnames = reader.fieldnames

            if not fieldnames:
                raise RuntimeError(
                    f"No CSV header found in {source}"
                )

            if "customer_id" not in fieldnames:
                raise RuntimeError(
                    f"{source} has no customer_id column."
                )

            for shard, destination in shard_paths.items():
                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                handle = destination.open(
                    "w",
                    encoding="utf-8",
                    newline="",
                )

                handles[shard] = handle
                writer = csv.DictWriter(
                    handle,
                    fieldnames=fieldnames,
                    lineterminator="\n",
                )
                writer.writeheader()
                writers[shard] = writer

            for row in reader:
                customer_id = int(row["customer_id"])

                try:
                    shard = mapping[customer_id]
                except KeyError as exc:
                    raise RuntimeError(
                        f"No shard mapping for customer_id="
                        f"{customer_id} in {filename}"
                    ) from exc

                writers[shard].writerow(row)
                counts[shard] += 1

    finally:
        for handle in handles.values():
            handle.close()

    total = counts["shard1"] + counts["shard2"]

    if total != EXPECTED_COUNTS[filename]:
        raise RuntimeError(
            f"{filename}: expected "
            f"{EXPECTED_COUNTS[filename]} rows, found {total}"
        )

    return {
        "shard1": counts["shard1"],
        "shard2": counts["shard2"],
        "total": total,
    }


def main() -> int:
    print("=== CUSTOMER-ID DATA PARTITIONING ===")
    print(f"python_version={sys.version.split()[0]}")
    print(f"oracledb_version={oracledb.__version__}")
    print(f"database_user={DB_USER}")
    print(f"input_directory={INPUT_DIR}")
    print(f"output_directory={OUTPUT_DIR}")

    validate_inputs()

    oracledb.init_oracle_client(
        lib_dir=os.path.join(ORACLE_HOME, "lib")
    )

    if oracledb.is_thin_mode():
        raise RuntimeError(
            "Thick mode is required for sharding-key routing."
        )

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True)

    customer_ids = load_customer_ids()

    print(f"unique_customer_ids={len(customer_ids)}")
    print()
    print("=== BUILDING CUSTOMER-TO-SHARD MAP ===")

    started = time.perf_counter()

    mapping, representatives = build_customer_mapping(
        customer_ids
    )

    routing_seconds = time.perf_counter() - started
    customer_distribution = Counter(mapping.values())

    print()
    print("=== CUSTOMER ROUTING DISTRIBUTION ===")
    print(f"shard1_customers={customer_distribution['shard1']}")
    print(f"shard2_customers={customer_distribution['shard2']}")
    print(f"routing_seconds={routing_seconds:.3f}")

    print()
    print("=== REPRESENTATIVE ROUTING KEYS ===")

    for shard in ("shard1", "shard2"):
        representative = representatives[shard]

        print(
            f"{shard}: "
            f"customer_id={representative['customer_id']}, "
            f"container={representative['container']}, "
            f"host={representative['host']}"
        )

    print()
    print("=== SPLITTING CSV FILES ===")

    table_counts = {}

    for filename in EXPECTED_FILES:
        counts = split_csv(filename, mapping)
        table_counts[filename] = counts

        print(
            f"{filename}: "
            f"shard1={counts['shard1']}, "
            f"shard2={counts['shard2']}, "
            f"total={counts['total']}"
        )

    summary = {
        "design": "customer-id",
        "database_user": DB_USER,
        "input_directory": str(INPUT_DIR),
        "output_directory": str(OUTPUT_DIR),
        "unique_customer_ids": len(customer_ids),
        "routing_seconds": round(routing_seconds, 3),
        "customer_distribution": {
            "shard1": customer_distribution["shard1"],
            "shard2": customer_distribution["shard2"],
        },
        "representatives": representatives,
        "table_counts": table_counts,
    }

    summary_path = OUTPUT_DIR / "partition-summary.json"

    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    print(f"summary_file={summary_path}")
    print("CUSTOMER_ID_PARTITIONING=PASS")

    # The CSV handles and summary file are already closed. Flush the
    # evidence stream and bypass native Oracle Client interpreter teardown.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
