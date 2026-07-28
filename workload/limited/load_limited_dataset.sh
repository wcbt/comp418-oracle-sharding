#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(git rev-parse --show-toplevel)"

if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 BANK_CUST|BANK_ACCT 5|10|20" >&2
  exit 2
fi

DB_USER="$1"
SCENARIO_SIZE="$2"

case "$DB_USER" in
  BANK_CUST|BANK_ACCT) ;;
  *)
    echo "DB_USER must be BANK_CUST or BANK_ACCT." >&2
    exit 2
    ;;
esac

case "$SCENARIO_SIZE" in
  5|10|20) ;;
  *)
    echo "Scenario size must be 5, 10, or 20." >&2
    exit 2
    ;;
esac

if [[ "$DB_USER" == "BANK_CUST" ]]; then
  [[ -n "${BANK_CUST_PASSWORD:-}" ]] || {
    read -rsp "Enter BANK_CUST password: " BANK_CUST_PASSWORD
    echo
  }
  DB_PASSWORD="$BANK_CUST_PASSWORD"
else
  [[ -n "${BANK_ACCT_PASSWORD:-}" ]] || {
    read -rsp "Enter BANK_ACCT password: " BANK_ACCT_PASSWORD
    echo
  }
  DB_PASSWORD="$BANK_ACCT_PASSWORD"
fi

cleanup() {
  unset DB_PASSWORD BANK_CUST_PASSWORD BANK_ACCT_PASSWORD
}
trap cleanup EXIT

NAMESPACE="comp418-gdd"
DATABASE="comp418-sharding"
POD="catalog-0"
ORACLE_HOME="/opt/oracle/product/26ai/dbhomeFree"
DB_DSN="//gsm1-0.gsm1.comp418-gdd.svc.cluster.local:1522/oltp_rw_svc.catalog.oradbcloud"
REMOTE_TOOLS="/tmp/comp418-limited-tools"
REMOTE_DATA="/tmp/comp418-limited-data"
LOCAL_DATA="workload/generated/limited"
slug="$(printf '%s' "$DB_USER" | tr '[:upper:]' '[:lower:]')"
EVIDENCE="evidence/step-14b-load-${slug}-${SCENARIO_SIZE}-customers.txt"

(
  echo "=== LIMITED DATASET LOAD ==="
  date -u '+UTC_TIME=%Y-%m-%dT%H:%M:%SZ'
  echo "DB_USER=$DB_USER"
  echo "SCENARIO_SIZE=$SCENARIO_SIZE"
  echo

  scenario="$LOCAL_DATA/customers-$SCENARIO_SIZE"

  for file in customers.csv accounts.csv ledger_entries.csv manifest.json; do
    test -f "$scenario/$file"
    echo "FOUND=$scenario/$file"
  done

  echo
  echo "=== STABLE SHARD HEALTH GATE ==="
  consecutive=0

  for attempt in $(seq 1 30); do
    state="$(
      kubectl get shardingdatabase "$DATABASE" \
        -n "$NAMESPACE" \
        -o wide \
        --no-headers
    )"

    echo "ATTEMPT=$attempt CONSECUTIVE_HEALTHY=$consecutive"
    echo "$state"

    if [[ "$state" == *"AVAILABLE"* &&
          "$state" == *'"shard1":"ONLINE_SHARD"'* &&
          "$state" == *'"shard2":"ONLINE_SHARD"'* ]]; then
      consecutive=$((consecutive + 1))
    else
      consecutive=0
    fi

    if (( consecutive >= 3 )); then
      echo "STABLE_SHARD_HEALTH=PASS"
      break
    fi

    sleep 10
  done

  if (( consecutive < 3 )); then
    echo "STABLE_SHARD_HEALTH=FAIL"
    exit 3
  fi

  echo
  echo "=== STAGE LOADER AND DATA ==="
  kubectl exec -n "$NAMESPACE" "$POD" -- \
    bash -lc "mkdir -p '$REMOTE_TOOLS' '$REMOTE_DATA'"

  kubectl exec -i -n "$NAMESPACE" "$POD" -- \
    bash -lc "cat > '$REMOTE_TOOLS/load_limited_dataset.py'" \
    < workload/limited/load_limited_dataset.py

  tar -C "$LOCAL_DATA" -cf - . |
    kubectl exec -i -n "$NAMESPACE" "$POD" -- \
      tar -C "$REMOTE_DATA" -xf -

  echo "REMOTE_STAGING=PASS"

  echo
  echo "=== CLEAN, LOAD, AND VERIFY TARGET SCHEMA ==="
  kubectl exec -i -n "$NAMESPACE" "$POD" -- \
    env ORACLE_HOME="$ORACLE_HOME" \
        DB_DSN="$DB_DSN" \
        DB_USER="$DB_USER" \
        DB_PASSWORD="$DB_PASSWORD" \
        SCENARIO_SIZE="$SCENARIO_SIZE" \
        DATA_ROOT="$REMOTE_DATA" \
    bash -lc '
      set -Eeuo pipefail
      exec /opt/oracle/product/26ai/dbhomeFree/python/bin/python3.13 \
        /tmp/comp418-limited-tools/load_limited_dataset.py
    '

  echo
  echo "LIMITED_SCHEMA_LOAD=PASS"

) 2>&1 | tee "$EVIDENCE"

rc=${PIPESTATUS[0]}
echo
echo "LIMITED_SCHEMA_LOAD_RC=$rc"
exit "$rc"
