#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(git rev-parse --show-toplevel)"

NAMESPACE="comp418-gdd"
DATABASE="comp418-sharding"
POD="catalog-0"
ORACLE_HOME="/opt/oracle/product/26ai/dbhomeFree"
PYTHON_BIN="$ORACLE_HOME/python/bin/python3.13"
DB_DSN="//gsm1-0.gsm1.comp418-gdd.svc.cluster.local:1522/oltp_rw_svc.catalog.oradbcloud"
REMOTE_TOOLS="/tmp/comp418-limited-tools"
REMOTE_DATA="/tmp/comp418-limited-data"
LOCAL_DATA="workload/generated/limited"
EVIDENCE="evidence/step-14a-limited-dataset-preparation.txt"

[[ -n "${BANK_CUST_PASSWORD:-}" ]] || {
  read -rsp "Enter BANK_CUST password: " BANK_CUST_PASSWORD
  echo
}

[[ -n "${BANK_ACCT_PASSWORD:-}" ]] || {
  read -rsp "Enter BANK_ACCT password: " BANK_ACCT_PASSWORD
  echo
}

cleanup() {
  unset BANK_CUST_PASSWORD BANK_ACCT_PASSWORD
}
trap cleanup EXIT

(
  echo "=== LIMITED DATASET PREPARATION ==="
  date -u '+UTC_TIME=%Y-%m-%dT%H:%M:%SZ'
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
    exit 2
  fi

  echo
  echo "=== STAGE PREPARATION SCRIPT ==="
  kubectl exec -n "$NAMESPACE" "$POD" -- \
    mkdir -p "$REMOTE_TOOLS"

  kubectl exec -i -n "$NAMESPACE" "$POD" -- \
    bash -lc "cat > '$REMOTE_TOOLS/prepare_limited_datasets.py'" \
    < workload/limited/prepare_limited_datasets.py

  local_sha="$(sha256sum workload/limited/prepare_limited_datasets.py | awk '{print $1}')"
  remote_sha="$(
    kubectl exec -n "$NAMESPACE" "$POD" -- \
      sha256sum "$REMOTE_TOOLS/prepare_limited_datasets.py" |
      awk '{print $1}'
  )"

  echo "LOCAL_SCRIPT_SHA256=$local_sha"
  echo "REMOTE_SCRIPT_SHA256=$remote_sha"
  [[ "$local_sha" == "$remote_sha" ]]
  echo "SCRIPT_STAGING=PASS"

  echo
  echo "=== GENERATE ROUTED 5/10/20 DATASETS ==="
  kubectl exec -i -n "$NAMESPACE" "$POD" -- \
    env ORACLE_HOME="$ORACLE_HOME" \
        DB_DSN="$DB_DSN" \
        BANK_CUST_PASSWORD="$BANK_CUST_PASSWORD" \
        BANK_ACCT_PASSWORD="$BANK_ACCT_PASSWORD" \
        OUTPUT_ROOT="$REMOTE_DATA" \
    bash -lc '
      set -Eeuo pipefail
      rm -rf "$OUTPUT_ROOT"
      exec /opt/oracle/product/26ai/dbhomeFree/python/bin/python3.13 \
        /tmp/comp418-limited-tools/prepare_limited_datasets.py
    '

  echo
  echo "=== COPY GENERATED DATA TO REPOSITORY ==="
  rm -rf "$LOCAL_DATA"
  mkdir -p "$LOCAL_DATA"

  kubectl exec -n "$NAMESPACE" "$POD" -- \
    tar -C "$REMOTE_DATA" -cf - . |
    tar -C "$LOCAL_DATA" -xf -

  echo
  echo "=== VERIFY LOCAL DATASETS ==="
  for size in 5 10 20; do
    scenario="$LOCAL_DATA/customers-$size"

    customers=$(( $(wc -l < "$scenario/customers.csv") - 1 ))
    accounts=$(( $(wc -l < "$scenario/accounts.csv") - 1 ))
    ledger=$(( $(wc -l < "$scenario/ledger_entries.csv") - 1 ))

    echo "size=$size customers=$customers accounts=$accounts ledger_entries=$ledger"

    [[ "$customers" -eq "$size" ]]
    [[ "$accounts" -eq $((size * 2)) ]]
    [[ "$ledger" -eq $((size * 10)) ]]

    grep -q '"shard1"' "$scenario/manifest.json"
    grep -q '"shard2"' "$scenario/manifest.json"
  done

  if grep -IRl $'\r' "$LOCAL_DATA" --include='*.csv' | grep -q .; then
    echo "CRLF_CHECK=FAIL"
    exit 3
  fi

  echo "CRLF_CHECK=PASS"
  echo "LIMITED_DATASET_PREPARATION=PASS"

) 2>&1 | tee "$EVIDENCE"

rc=${PIPESTATUS[0]}
echo
echo "LIMITED_DATASET_PREPARATION_RC=$rc"
exit "$rc"
