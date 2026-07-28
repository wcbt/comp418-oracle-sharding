#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path


def format_money(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def positive_int(value: str) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")

    return parsed


def generate(
    output_dir: Path,
    customer_count: int,
    accounts_per_customer: int,
    ledger_per_account: int,
    seed: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    customers_path = output_dir / "customers.csv"
    accounts_path = output_dir / "accounts.csv"
    ledger_path = output_dir / "ledger_entries.csv"
    summary_path = output_dir / "summary.json"

    rng = random.Random(seed)
    transfer_id = 980_000_000_000

    customer_rows = 0
    account_rows = 0
    ledger_rows = 0

    with (
        customers_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as customers_file,
        accounts_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as accounts_file,
        ledger_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as ledger_file,
    ):
        customers_writer = csv.DictWriter(
            customers_file,
            fieldnames=[
                "customer_id",
                "full_name",
                "email",
                "customer_state",
            ],
            lineterminator="\n",
        )

        accounts_writer = csv.DictWriter(
            accounts_file,
            fieldnames=[
                "account_id",
                "customer_id",
                "account_type",
                "balance",
                "currency",
                "account_state",
            ],
            lineterminator="\n",
        )

        ledger_writer = csv.DictWriter(
            ledger_file,
            fieldnames=[
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
            lineterminator="\n",
        )

        customers_writer.writeheader()
        accounts_writer.writeheader()
        ledger_writer.writeheader()

        for customer_number in range(1, customer_count + 1):
            customer_id = 600_000_000 + customer_number

            customers_writer.writerow(
                {
                    "customer_id": customer_id,
                    "full_name":
                        f"Benchmark Customer {customer_number:05d}",
                    "email":
                        f"benchmark.customer{customer_number:05d}"
                        "@example.test",
                    "customer_state": "ACTIVE",
                }
            )
            customer_rows += 1

            for account_number in range(
                1,
                accounts_per_customer + 1,
            ):
                account_id = (
                    700_000_000_000
                    + customer_number * 100
                    + account_number
                )

                account_type = (
                    "CHEQUING"
                    if account_number % 2 == 1
                    else "SAVINGS"
                )

                balance_cents = rng.randint(
                    100_000,
                    500_000,
                )

                entries: list[dict[str, object]] = []

                transfer_id += 1

                entries.append(
                    {
                        "account_id": account_id,
                        "entry_id": 1,
                        "transfer_id": transfer_id,
                        "customer_id": customer_id,
                        "entry_type": "CREDIT",
                        "amount": format_money(balance_cents),
                        "balance_after":
                            format_money(balance_cents),
                        "counterparty_customer_id": "",
                        "counterparty_account_id": "",
                    }
                )

                for entry_id in range(
                    2,
                    ledger_per_account + 1,
                ):
                    can_debit = balance_cents >= 20_000

                    entry_type = (
                        "DEBIT"
                        if can_debit and rng.random() < 0.55
                        else "CREDIT"
                    )

                    if entry_type == "DEBIT":
                        maximum = min(
                            50_000,
                            max(1_000, balance_cents // 4),
                        )

                        amount_cents = rng.randint(
                            1_000,
                            maximum,
                        )
                        balance_cents -= amount_cents
                    else:
                        amount_cents = rng.randint(
                            1_000,
                            50_000,
                        )
                        balance_cents += amount_cents

                    transfer_id += 1

                    entries.append(
                        {
                            "account_id": account_id,
                            "entry_id": entry_id,
                            "transfer_id": transfer_id,
                            "customer_id": customer_id,
                            "entry_type": entry_type,
                            "amount":
                                format_money(amount_cents),
                            "balance_after":
                                format_money(balance_cents),
                            "counterparty_customer_id": "",
                            "counterparty_account_id": "",
                        }
                    )

                accounts_writer.writerow(
                    {
                        "account_id": account_id,
                        "customer_id": customer_id,
                        "account_type": account_type,
                        "balance": format_money(balance_cents),
                        "currency": "CAD",
                        "account_state": "ACTIVE",
                    }
                )
                account_rows += 1

                ledger_writer.writerows(entries)
                ledger_rows += len(entries)

    expected_accounts = (
        customer_count * accounts_per_customer
    )
    expected_ledger = (
        expected_accounts * ledger_per_account
    )

    if customer_rows != customer_count:
        raise RuntimeError(
            "customer row-count mismatch"
        )

    if account_rows != expected_accounts:
        raise RuntimeError(
            "account row-count mismatch"
        )

    if ledger_rows != expected_ledger:
        raise RuntimeError(
            "ledger row-count mismatch"
        )

    summary = {
        "seed": seed,
        "customers": customer_rows,
        "accounts": account_rows,
        "ledger_entries": ledger_rows,
        "accounts_per_customer":
            accounts_per_customer,
        "ledger_entries_per_account":
            ledger_per_account,
        "files": {
            customers_path.name: {
                "bytes":
                    customers_path.stat().st_size,
                "sha256": sha256(customers_path),
            },
            accounts_path.name: {
                "bytes":
                    accounts_path.stat().st_size,
                "sha256": sha256(accounts_path),
            },
            ledger_path.name: {
                "bytes":
                    ledger_path.stat().st_size,
                "sha256": sha256(ledger_path),
            },
        },
    }

    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Output directory: {output_dir}")
    print(f"Customers:        {customer_rows}")
    print(f"Accounts:         {account_rows}")
    print(f"Ledger entries:   {ledger_rows}")
    print(f"Summary:          {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic benchmark data "
            "for both sharding designs."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "workload/generated/benchmark-10k"
        ),
    )

    parser.add_argument(
        "--customers",
        type=positive_int,
        default=10_000,
    )

    parser.add_argument(
        "--accounts-per-customer",
        type=positive_int,
        default=2,
    )

    parser.add_argument(
        "--ledger-per-account",
        type=positive_int,
        default=5,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=418,
    )

    args = parser.parse_args()

    generate(
        output_dir=args.output,
        customer_count=args.customers,
        accounts_per_customer=
            args.accounts_per_customer,
        ledger_per_account=
            args.ledger_per_account,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
