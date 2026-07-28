#!/usr/bin/env bash
set -Eeuo pipefail

: "${BANK_CUST_PASSWORD:?BANK_CUST_PASSWORD is not set}"

NAMESPACE="comp418-gdd"
POD="catalog-0"
DB_USER="BANK_CUST"

CONTROL_DIR="/tmp/comp418-benchmark-10k"
DATA_DIR="/tmp/comp418-benchmark-10k/partitioned/bank_cust"

CUSTOMER_MIN=600000001
CUSTOMER_MAX=600010000

run_id="$(date -u +%Y%m%dT%H%M%SZ)"
REMOTE_LOG_DIR="$CONTROL_DIR/logs/${run_id}-bank-cust-direct"
LOCAL_LOG_DIR="results/benchmark-load/${run_id}-bank-cust-direct"

mkdir -p "$LOCAL_LOG_DIR"

kubectl exec -n "$NAMESPACE" "$POD" -- \
  mkdir -p "$REMOTE_LOG_DIR"

connection_for() {
  case "$1" in
    shard1)
      printf '%s' '//shard1-0.shard1:1521/shard1pdb'
      ;;
    shard2)
      printf '%s' '//shard2-0.shard2:1521/shard2pdb'
      ;;
    *)
      echo "Unknown shard: $1" >&2
      return 1
      ;;
  esac
}

expected_count() {
  case "$1:$2" in
    shard1:customers)       echo 5018 ;;
    shard1:accounts)        echo 10036 ;;
    shard1:ledger_entries)  echo 50180 ;;
    shard2:customers)       echo 4982 ;;
    shard2:accounts)        echo 9964 ;;
    shard2:ledger_entries)  echo 49820 ;;
    *)
      echo "No expected count for $1:$2" >&2
      return 1
      ;;
  esac
}

query_count() {
  local shard="$1"
  local table="$2"
  local db_connect

  db_connect="$(connection_for "$shard")"

  kubectl exec -i -n "$NAMESPACE" "$POD" -- \
    env DB_USER="$DB_USER" \
        DB_PASSWORD="$BANK_CUST_PASSWORD" \
        DB_CONNECT="$db_connect" \
    bash -lc '
      {
        printf "WHENEVER SQLERROR EXIT SQL.SQLCODE\n"
        printf "CONNECT %s/\"%s\"@%s\n" \
          "$DB_USER" "$DB_PASSWORD" "$DB_CONNECT"
        cat
      } | sqlplus -L -s /nolog
    ' <<SQL
SET PAGESIZE 0
SET HEADING OFF
SET FEEDBACK OFF
SET VERIFY OFF
SET ECHO OFF

SELECT COUNT(*)
FROM $table
WHERE customer_id BETWEEN $CUSTOMER_MIN AND $CUSTOMER_MAX;

EXIT SUCCESS
SQL
}

normalize_count() {
  tr -d '[:space:]'
}

echo "========================================"
echo "CUSTOMER-ID DIRECT SHARD LOAD"
echo "Run ID: $run_id"
echo "Logs:   $LOCAL_LOG_DIR"
echo "========================================"

echo
echo "=== PRE-LOAD COUNTS ==="

for shard in shard1 shard2; do
  for table in customers accounts ledger_entries; do
    count="$(
      query_count "$shard" "$table" |
        normalize_count
    )"

    if [[ ! "$count" =~ ^[0-9]+$ ]]; then
      echo "Invalid count returned for $shard.$table: $count" >&2
      exit 1
    fi

    printf '%s|%s|%s\n' "$shard" "$table" "$count" |
      tee -a "$LOCAL_LOG_DIR/pre-load-counts.txt"

    if [[ "$count" -ne 0 ]]; then
      echo "Refusing to load because benchmark rows already exist." >&2
      exit 1
    fi
  done
done

load_one() {
  local shard="$1"
  local table="$2"

  local db_connect
  local control_file
  local data_file
  local log_file
  local bad_file
  local output_file
  local result_file
  local started
  local finished
  local elapsed
  local rc

  db_connect="$(connection_for "$shard")"

  control_file="$CONTROL_DIR/${table}.ctl"
  data_file="$DATA_DIR/$shard/${table}.csv"
  log_file="$REMOTE_LOG_DIR/${shard}-${table}.log"
  bad_file="$REMOTE_LOG_DIR/${shard}-${table}.bad"

  output_file="$LOCAL_LOG_DIR/${shard}-${table}-output.txt"
  result_file="$LOCAL_LOG_DIR/${shard}-${table}-result.txt"

  echo
  echo "========================================"
  echo "LOADING $shard: $DB_USER.$table"
  echo "========================================"

  started="$(date +%s)"

  set +e

  kubectl exec -i -n "$NAMESPACE" "$POD" -- \
    env DB_USER="$DB_USER" \
        DB_PASSWORD="$BANK_CUST_PASSWORD" \
        DB_CONNECT="$db_connect" \
        CONTROL_FILE="$control_file" \
        DATA_FILE="$data_file" \
        LOG_FILE="$log_file" \
        BAD_FILE="$bad_file" \
    bash -lc '
      userid="${DB_USER}/${DB_PASSWORD}@${DB_CONNECT}"

      exec sqlldr \
        userid="$userid" \
        control="$CONTROL_FILE" \
        data="$DATA_FILE" \
        log="$LOG_FILE" \
        bad="$BAD_FILE" \
        direct=false \
        errors=0
    ' 2>&1 |
    tee "$output_file"

  rc="${PIPESTATUS[0]}"

  set -e

  finished="$(date +%s)"
  elapsed=$((finished - started))

  {
    echo "shard=$shard"
    echo "table=$table"
    echo "exit_code=$rc"
    echo "elapsed_seconds=$elapsed"
  } > "$result_file"

  echo
  echo "$shard.$table exit code: $rc"
  echo "$shard.$table elapsed seconds: $elapsed"

  if [[ "$rc" -ne 0 ]]; then
    echo "Load failed; stopping before dependent data." >&2
    exit "$rc"
  fi
}

# Load all parents first, then their dependent tables.
for table in customers accounts ledger_entries; do
  for shard in shard1 shard2; do
    load_one "$shard" "$table"
  done
done

echo
echo "=== POST-LOAD VERIFICATION ==="

verification_failed=0

for shard in shard1 shard2; do
  for table in customers accounts ledger_entries; do
    actual="$(
      query_count "$shard" "$table" |
        normalize_count
    )"

    expected="$(expected_count "$shard" "$table")"

    printf '%s|%s|actual=%s|expected=%s\n' \
      "$shard" "$table" "$actual" "$expected" |
      tee -a "$LOCAL_LOG_DIR/post-load-counts.txt"

    if [[ "$actual" -ne "$expected" ]]; then
      verification_failed=1
    fi
  done
done

echo
echo "=== COPYING SQL*LOADER LOGS ==="

kubectl exec -n "$NAMESPACE" "$POD" -- \
  tar -C "$REMOTE_LOG_DIR" -cf - . |
  tar -C "$LOCAL_LOG_DIR" -xf -

if [[ "$verification_failed" -ne 0 ]]; then
  echo "POST_LOAD_VERIFICATION=FAIL" >&2
  exit 1
fi

echo
echo "=== EVIDENCE FILES ==="

find "$LOCAL_LOG_DIR" \
  -maxdepth 1 \
  -type f \
  -printf '%f\n' |
  sort

echo
echo "POST_LOAD_VERIFICATION=PASS"
echo "CUSTOMER_ID_DIRECT_LOAD=PASS"
echo "Evidence directory: $LOCAL_LOG_DIR"
