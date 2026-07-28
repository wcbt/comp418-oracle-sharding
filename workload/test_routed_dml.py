#!/usr/bin/env python3

import os

import oracledb


ORACLE_HOME = os.environ["ORACLE_HOME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_DSN = os.environ["DB_DSN"]

TEST_CUSTOMER_ID = int(
    os.environ.get("TEST_CUSTOMER_ID", "699999999")
)

oracledb.init_oracle_client(
    lib_dir=os.path.join(ORACLE_HOME, "lib")
)

if oracledb.is_thin_mode():
    raise RuntimeError("Thick mode is required for sharding-key routing.")

print("=== ROUTED DML ROLLBACK TEST ===")
print(f"database_user={DB_USER}")
print(f"test_customer_id={TEST_CUSTOMER_ID}")

connection = oracledb.connect(
    user=DB_USER,
    password=DB_PASSWORD,
    dsn=DB_DSN,
    shardingkey=[TEST_CUSTOMER_ID],
)

try:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                SYS_CONTEXT('USERENV', 'CON_NAME'),
                SYS_CONTEXT('USERENV', 'SERVER_HOST'),
                SYS_CONTEXT('USERENV', 'SERVICE_NAME')
            FROM dual
            """
        )

        container, host, service = cursor.fetchone()

        print(f"container={container}")
        print(f"server_host={host}")
        print(f"service={service}")

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM customers
            WHERE customer_id = :customer_id
            """,
            customer_id=TEST_CUSTOMER_ID,
        )

        count_before = cursor.fetchone()[0]
        print(f"count_before_insert={count_before}")

        if count_before != 0:
            raise RuntimeError(
                f"Test customer {TEST_CUSTOMER_ID} already exists."
            )

        cursor.execute(
            """
            INSERT INTO customers
            (
                customer_id,
                full_name,
                email,
                customer_state
            )
            VALUES
            (
                :customer_id,
                :full_name,
                :email,
                :customer_state
            )
            """,
            customer_id=TEST_CUSTOMER_ID,
            full_name="Rollback Test Customer",
            email="rollback-test@example.invalid",
            customer_state="ACTIVE",
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM customers
            WHERE customer_id = :customer_id
            """,
            customer_id=TEST_CUSTOMER_ID,
        )

        count_after_insert = cursor.fetchone()[0]
        print(f"count_after_insert={count_after_insert}")

        if count_after_insert != 1:
            raise RuntimeError(
                "Inserted test row was not visible in the transaction."
            )

        connection.rollback()
        print("transaction_action=ROLLBACK")

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM customers
            WHERE customer_id = :customer_id
            """,
            customer_id=TEST_CUSTOMER_ID,
        )

        count_after_rollback = cursor.fetchone()[0]
        print(f"count_after_rollback={count_after_rollback}")

        if count_after_rollback != 0:
            raise RuntimeError(
                "Test row still exists after rollback."
            )

finally:
    connection.rollback()
    connection.close()

print("ROUTED_DML_ROLLBACK_TEST=PASS")
