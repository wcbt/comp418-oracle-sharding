#!/usr/bin/env bash
set -Eeuo pipefail

: "${DB_USER:?Set DB_USER to BANK_CUST or BANK_ACCT}"
: "${DB_PASSWORD:?Set DB_PASSWORD}"

case "$DB_USER" in
  BANK_CUST|BANK_ACCT) ;;
  *)
    echo "DB_USER must be BANK_CUST or BANK_ACCT." >&2
    exit 2
    ;;
esac

NAMESPACE="comp418-gdd"
POD="catalog-0"

REMOTE_DIR="/tmp/comp418-benchmark-10k"
GSM_NAME="oltp_rw_svc.catalog.oradbcloud"
GSM_HOST="gsm1-0.gsm1.comp418-gdd.svc.cluster.local"
GSM_PORT="1522"

CATALOG_CONNECT='//localhost:1521/GDS$CATALOG.oradbcloud'

CUSTOMER_MIN=600000001
CUSTOMER_MAX=600010000

run_id="$(date -u +%Y%m%dT%H%M%SZ)"
schema_slug="$(printf '%s' "$DB_USER" | tr '[:upper:]' '[:lower:]')"

REMOTE_LOG_DIR="$REMOTE_DIR/logs/${run_id}-${schema_slug}"
LOCAL_LOG_DIR="results/benchmark-load/${run_id}-${schema_slug}"

mkdir -p "$LOCAL_LOG_DIR"

kubectl exec -n "$NAMESPACE" "$POD" -- \
  bash -lc "mkdir -p '$REMOTE_LOG_DIR'"

query_counts() {
  kubectl exec -i -n "$NAMESPACE" "$POD" -- \
    env DB_USER="$DB_USER" \
        DB_PASSWORD="$DB_PASSWORD" \
        CATALOG_CONNECT="$CATALOG_CONNECT" \
    bash -lc '
      {
        printf "WHENEVER SQLERROR EXIT SQL.SQLCODE\n"
        printf "CONNECT %s/\"%s\"@%s\n" \
          "$DB_USER" "$DB_PASSWORD" "$CATALOG_CONNECT"
        cat
      } | sqlplus -L -s /nolog
    ' <<SQL
SET PAGESIZE 100
SET LINESIZE 180
SET FEEDBACK ON
SET HEADING ON

COLUMN object_name FORMAT A20

SELECT 'CUSTOMERS' AS object_name, COUNT(*) AS benchmark_rows
FROM customers
WHERE customer_id BETWEEN $CUSTOMER_MIN AND $CUSTOMER_MAX
UNION ALL
SELECT 'ACCOUNTS', COUNT(*)
FROM accounts
WHERE customer_id BETWEEN $CUSTOMER_MIN AND $CUSTOMER_MAX
UNION ALL
SELECT 'LEDGER_ENTRIES', COUNT(*)
FROM ledger_entries
WHERE customer_id BETWEEN $CUSTOMER_MIN AND $CUSTOMER_MAX;

EXIT SUCCESS
SQL
}

query_total() {
  local result

  result="$(
    kubectl exec -i -n "$NAMESPACE" "$POD" -- \
      env DB_USER="$DB_USER" \
          DB_PASSWORD="$DB_PASSWORD" \
          CATALOG_CONNECT="$CATALOG_CONNECT" \
      bash -lc '
        {
          printf "WHENEVER SQLERROR EXIT SQL.SQLCODE\n"
          printf "CONNECT %s/\"%s\"@%s\n" \
            "$DB_USER" "$DB_PASSWORD" "$CATALOG_CONNECT"
          cat
        } | sqlplus -L -s /nolog
      ' <<SQL
SET PAGESIZE 0
SET HEADING OFF
SET FEEDBACK OFF
SET VERIFY OFF
SET ECHO OFF

SELECT
      (SELECT COUNT(*)
         FROM customers
        WHERE customer_id BETWEEN $CUSTOMER_MIN AND $CUSTOMER_MAX)
    + (SELECT COUNT(*)
         FROM accounts
        WHERE customer_id BETWEEN $CUSTOMER_MIN AND $CUSTOMER_MAX)
    + (SELECT COUNT(*)
         FROM ledger_entries
        WHERE customer_id BETWEEN $CUSTOMER_MIN AND $CUSTOMER_MAX)
FROM dual;

EXIT SUCCESS
SQL
  )"

  printf '%s' "$result" | tr -d '[:space:]'
}


echo "========================================"
echo "BENCHMARK LOAD"
echo "Schema:     $DB_USER"
echo "Run ID:     $run_id"
echo "Local logs: $LOCAL_LOG_DIR"
echo "========================================"

echo
echo "=== PRE-LOAD COUNTS ==="
query_counts | tee "$LOCAL_LOG_DIR/pre-load-counts.txt"

existing_total="$(query_total)"

if [[ ! "$existing_total" =~ ^[0-9]+$ ]]; then
  echo "Could not determine the existing benchmark-row count." >&2
  echo "Returned value: $existing_total" >&2
  exit 1
fi

if [[ "$existing_total" -ne 0 ]]; then
  echo
  echo "Refusing to load: $existing_total benchmark rows already exist."
  echo "Do not rerun an APPEND load against existing benchmark data."
  exit 1
fi

load_table() {
  local table="$1"
  local control="$REMOTE_DIR/${table}.ctl"
  local data="$REMOTE_DIR/${table}.csv"
  local log="$REMOTE_LOG_DIR/${table}.log"
  local bad="$REMOTE_LOG_DIR/${table}.bad"
  local stdout_file="$LOCAL_LOG_DIR/${table}-sqlldr-output.txt"

  echo
  echo "========================================"
  echo "LOADING $DB_USER.$table"
  echo "========================================"

  local start_epoch
  local end_epoch
  local elapsed
  local rc

  start_epoch="$(date +%s)"

  set +e
  kubectl exec -i -n "$NAMESPACE" "$POD" -- \
    env DB_USER="$DB_USER" \
        DB_PASSWORD="$DB_PASSWORD" \
        CONTROL_FILE="$control" \
        DATA_FILE="$data" \
        LOG_FILE="$log" \
        BAD_FILE="$bad" \
        GSM_NAME="$GSM_NAME" \
        GSM_HOST="$GSM_HOST" \
        GSM_PORT="$GSM_PORT" \
    bash -lc '
      userid="${DB_USER}/\"${DB_PASSWORD}\""

      exec sqlldr \
        userid="$userid" \
        control="$CONTROL_FILE" \
        data="$DATA_FILE" \
        log="$LOG_FILE" \
        bad="$BAD_FILE" \
        gsm_name="$GSM_NAME" \
        gsm_host="$GSM_HOST" \
        gsm_port="$GSM_PORT" \
        direct=false \
        parallel=false \
        errors=0
    ' 2>&1 | tee "$stdout_file"

  rc="${PIPESTATUS[0]}"
  set -e

  end_epoch="$(date +%s)"
  elapsed=$((end_epoch - start_epoch))

  {
    echo "table=$table"
    echo "exit_code=$rc"
    echo "elapsed_seconds=$elapsed"
  } > "$LOCAL_LOG_DIR/${table}-result.txt"

  echo
  echo "$table exit code: $rc"
  echo "$table elapsed seconds: $elapsed"

  if [[ "$rc" -ne 0 ]]; then
    echo "$table load failed. Stopping before dependent tables." >&2
    exit "$rc"
  fi
}

load_table customers
load_table accounts
load_table ledger_entries

echo
echo "=== POST-LOAD COUNTS ==="
query_counts | tee "$LOCAL_LOG_DIR/post-load-counts.txt"

echo
echo "=== COPYING SQL*LOADER LOGS ==="

kubectl exec -n "$NAMESPACE" "$POD" -- \
  tar -C "$REMOTE_LOG_DIR" -cf - . |
  tar -C "$LOCAL_LOG_DIR" -xf -

echo
echo "=== LOCAL EVIDENCE FILES ==="
find "$LOCAL_LOG_DIR" -maxdepth 2 -type f -printf '%P\n' | sort

echo
echo "Benchmark load completed for $DB_USER."
echo "Evidence directory: $LOCAL_LOG_DIR"
