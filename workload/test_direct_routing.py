#!/usr/bin/env python3

import os
import sys
from collections import OrderedDict

import oracledb


ORACLE_HOME = os.environ["ORACLE_HOME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_DSN = os.environ["DB_DSN"]

CLIENT_LIB_DIR = os.path.join(ORACLE_HOME, "lib")

oracledb.init_oracle_client(lib_dir=CLIENT_LIB_DIR)

if oracledb.is_thin_mode():
    raise RuntimeError("Python-oracledb is still running in Thin mode.")


def locate_shard(sharding_key: int) -> tuple[str, str, str, str]:
    """Open a sharding-key connection and return its physical location."""

    with oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN,
        shardingkey=[sharding_key],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    SYS_CONTEXT('USERENV', 'CON_NAME'),
                    SYS_CONTEXT('USERENV', 'SERVER_HOST'),
                    SYS_CONTEXT('USERENV', 'SERVICE_NAME'),
                    SYS_CONTEXT('USERENV', 'DB_UNIQUE_NAME')
                FROM dual
                """
            )

            row = cursor.fetchone()

            if row is None:
                raise RuntimeError("Routing-location query returned no row.")

            return tuple(str(value) for value in row)


print("=== PYTHON DIRECT-ROUTING TEST ===")
print(f"python_version={sys.version.split()[0]}")
print(f"oracledb_version={oracledb.__version__}")
print(f"thick_mode={not oracledb.is_thin_mode()}")
print(f"oracle_client_version={oracledb.clientversion()}")
print(f"database_user={DB_USER}")
print(f"director_service={DB_DSN}")

print()
print("=== SHARD MAPPING SAMPLE ===")
print("customer_id|container|server_host|service|db_unique_name")

representatives: OrderedDict[str, tuple[int, str]] = OrderedDict()

for customer_id in range(600_000_001, 600_000_033):
    container, host, service, db_unique_name = locate_shard(customer_id)

    print(
        f"{customer_id}|{container}|{host}|"
        f"{service}|{db_unique_name}"
    )

    representatives.setdefault(container, (customer_id, host))

expected_containers = {"SHARD1PDB", "SHARD2PDB"}
observed_containers = set(representatives)

print()
print("=== OBSERVED CONTAINERS ===")
for container, (customer_id, host) in representatives.items():
    print(
        f"{container}: representative_customer_id={customer_id}, "
        f"server_host={host}"
    )

missing = expected_containers - observed_containers

if missing:
    raise RuntimeError(
        "The routing sample did not reach every expected shard. "
        f"Missing: {sorted(missing)}"
    )

print()
print("=== DETERMINISM CHECK ===")

for container, (customer_id, expected_host) in representatives.items():
    results = []

    for attempt in range(1, 4):
        actual_container, actual_host, service, db_unique_name = locate_shard(
            customer_id
        )

        results.append((actual_container, actual_host))

        print(
            f"customer_id={customer_id}, attempt={attempt}, "
            f"container={actual_container}, server_host={actual_host}"
        )

    if any(
        actual_container != container or actual_host != expected_host
        for actual_container, actual_host in results
    ):
        raise RuntimeError(
            f"Inconsistent routing detected for customer {customer_id}."
        )

print()
print("DIRECT_ROUTING_TEST=PASS")
