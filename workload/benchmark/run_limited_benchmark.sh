#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

MODE="${1:-smoke}"
case "$MODE" in
  smoke)
    SCHEMAS=(BANK_CUST BANK_ACCT)
    SIZES=(5)
    CONCURRENCIES="1"
    ITERATIONS=3
    WARMUP=1
    REPEATS=1
    EVIDENCE_FILE="evidence/step-15a-benchmark-smoke.txt"
    ;;
  transfer-smoke)
    SCHEMAS=(BANK_CUST BANK_ACCT)
    SIZES=(5)
    CONCURRENCIES="1,5,10"
    ITERATIONS=3
    WARMUP=1
    REPEATS=1
    WORKLOADS="same_customer_transfer,cross_customer_transfer"
    EVIDENCE_FILE="evidence/step-15a2-transfer-concurrency-smoke.txt"
    ;;
  full)
    SCHEMAS=(BANK_CUST BANK_ACCT)
    SIZES=(5 10 20)
    CONCURRENCIES="1,5,10"
    ITERATIONS=10
    WARMUP=2
    REPEATS=3
    EVIDENCE_FILE="evidence/step-15b-limited-benchmark-matrix.txt"
    ;;
  *)
    echo "Usage: $0 smoke|transfer-smoke|full" >&2
    exit 64
    ;;
esac

NAMESPACE="comp418-gdd"
DATABASE="comp418-sharding"
POD="catalog-0"
ORACLE_HOME="/opt/oracle/product/26ai/dbhomeFree"
PYTHON_BIN="$ORACLE_HOME/python/bin/python3.13"
REMOTE_ROOT="/tmp/comp418-limited-benchmark"
REMOTE_SCRIPT="$REMOTE_ROOT/benchmark_runner.py"
WORKLOADS="${WORKLOADS:-customer_account_lookup,individual_account_lookup,same_customer_transfer,cross_customer_transfer}"

RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')"
LOCAL_ROOT="results/limited-benchmark/${RUN_ID}-${MODE}"
mkdir -p "$LOCAL_ROOT" evidence
: > "$EVIDENCE_FILE"

read -rsp "Enter BANK_CUST password: " BANK_CUST_PASSWORD
echo
if [[ " ${SCHEMAS[*]} " == *" BANK_ACCT "* ]]; then
  read -rsp "Enter BANK_ACCT password: " BANK_ACCT_PASSWORD
  echo
else
  BANK_ACCT_PASSWORD=""
fi

cleanup() {
  unset BANK_CUST_PASSWORD BANK_ACCT_PASSWORD
}
trap cleanup EXIT

exec > >(tee -a "$EVIDENCE_FILE") 2>&1

stable_health_gate() {
  echo "=== STABLE SHARD HEALTH GATE ==="

  local consecutive_healthy=0
  local operator_state=""
  local pods_ready=0
  local gds_output=""
  local gds_rc=0
  local shard1_registered=0
  local shard2_registered=0
  local online_count=0
  local ready_service_instances=0

  for attempt in $(seq 1 30); do
    operator_state="$(
      kubectl get shardingdatabase "$DATABASE" \
        -n "$NAMESPACE" \
        -o wide \
        --no-headers 2>/dev/null ||
        true
    )"

    pods_ready="$(
      kubectl get pods \
        -n "$NAMESPACE" \
        catalog-0 gsm1-0 gsm2-0 shard1-0 shard2-0 \
        --no-headers 2>/dev/null |
      awk '
        {
          checked++
          if ($2 != "1/1" || $3 != "Running") {
            bad++
          }
        }
        END {
          if (checked == 5 && bad == 0) {
            print 1
          } else {
            print 0
          }
        }
      '
    )"

    if gds_output="$(
      kubectl exec -i -n "$NAMESPACE" gsm1-0 -- bash -lc '
        GSM_HOME="${GSM_HOME:-/u01/app/oracle/product/23ai/gsmhome_1}"
        exec "$GSM_HOME/bin/gdsctl"
      ' <<'GDS'
databases
status service
config shard -shard SHARD1_SHARD1PDB
config shard -shard SHARD2_SHARD2PDB
exit
GDS
    )"; then
      gds_rc=0
    else
      gds_rc=$?
    fi

    shard1_registered=0
    shard2_registered=0

    grep -Fq \
      'Database: "shard1_shard1pdb" Registered: Y' \
      <<< "$gds_output" &&
      shard1_registered=1

    grep -Fq \
      'Database: "shard2_shard2pdb" Registered: Y' \
      <<< "$gds_output" &&
      shard2_registered=1

    online_count="$(
      grep -Fc 'Availability: ONLINE' <<< "$gds_output" ||
      true
    )"

    ready_service_instances="$(
      grep -Ec \
        'db: "shard(1|2)_shard(1|2)pdb".*status: ready' \
        <<< "$gds_output" ||
      true
    )"

    echo "ATTEMPT=$attempt CONSECUTIVE_HEALTHY=$consecutive_healthy"
    echo "OPERATOR_STATE=$operator_state"
    echo "PODS_READY=$pods_ready"
    echo "GDSCTL_RC=$gds_rc"
    echo "SHARD1_REGISTERED=$shard1_registered"
    echo "SHARD2_REGISTERED=$shard2_registered"
    echo "ONLINE_SHARD_COUNT=$online_count"
    echo "READY_SERVICE_INSTANCE_LINES=$ready_service_instances"

    if (( pods_ready == 1 )) &&
       (( gds_rc == 0 )) &&
       (( shard1_registered == 1 )) &&
       (( shard2_registered == 1 )) &&
       (( online_count >= 2 )) &&
       (( ready_service_instances >= 4 )); then
      consecutive_healthy=$((consecutive_healthy + 1))
      echo "GDS_HEALTH_RESULT=PASS"
    else
      consecutive_healthy=0
      echo "GDS_HEALTH_RESULT=FAIL"
    fi

    if (( consecutive_healthy >= 3 )); then
      echo "STABLE_SHARD_HEALTH_SOURCE=GDSCTL_AND_PODS"
      echo "STABLE_SHARD_HEALTH=PASS"
      return 0
    fi

    echo
    sleep 10
  done

  echo "=== FINAL FAILED GDSCTL OUTPUT ===" >&2
  printf '%s
' "$gds_output" >&2
  echo "STABLE_SHARD_HEALTH_SOURCE=GDSCTL_AND_PODS" >&2
  echo "STABLE_SHARD_HEALTH=FAIL" >&2
  return 2
}

schema_password() {
  case "$1" in
    BANK_CUST) printf '%s' "$BANK_CUST_PASSWORD" ;;
    BANK_ACCT) printf '%s' "$BANK_ACCT_PASSWORD" ;;
    *) return 64 ;;
  esac
}

load_dataset() {
  local schema="$1"
  local size="$2"
  local password="$3"
  local scenario_dir="$4"
  local schema_lower="${schema,,}"
  local load_evidence="evidence/step-14b-load-${schema_lower}-${size}-customers.txt"

  echo
  echo "=== RELOAD DATASET ==="
  echo "SCHEMA=$schema"
  echo "SIZE=$size"

  set +e
  ./workload/limited/load_limited_dataset.sh "$schema" "$size" \
    <<< "$password" 2>&1 |
    tee "$scenario_dir/load.log"
  local load_rc="${PIPESTATUS[0]}"
  set -e

  # Preserve the committed Step 14 evidence; this benchmark has its own logs.
  git restore -- "$load_evidence" 2>/dev/null || true

  echo "DATASET_RELOAD_RC=$load_rc"
  if (( load_rc != 0 )); then
    return "$load_rc"
  fi
}

copy_remote_results() {
  local remote_dir="$1"
  local local_dir="$2"

  mkdir -p "$local_dir"
  kubectl exec -n "$NAMESPACE" "$POD" -- \
    tar -C "$remote_dir" -cf - . |
    tar -C "$local_dir" -xf -
}

echo "=== LIMITED BENCHMARK ${MODE^^} ==="
echo "UTC_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "RUN_ID=$RUN_ID"
echo "RESULT_ROOT=$LOCAL_ROOT"
echo "SCHEMAS=${SCHEMAS[*]}"
echo "SIZES=${SIZES[*]}"
echo "CONCURRENCIES=$CONCURRENCIES"
echo "ITERATIONS_PER_CLIENT=$ITERATIONS"
echo "WARMUP_PER_CLIENT=$WARMUP"
echo "REPEATS=$REPEATS"

echo
echo "=== LOCAL VALIDATION ==="
bash -n workload/benchmark/run_limited_benchmark.sh
python3 -m py_compile \
  workload/benchmark/benchmark_runner.py \
  workload/benchmark/combine_results.py
rm -rf workload/benchmark/__pycache__
echo "LOCAL_VALIDATION=PASS"

echo
echo "=== STAGE BENCHMARK RUNNER ==="
kubectl exec -n "$NAMESPACE" "$POD" -- \
  mkdir -p "$REMOTE_ROOT"
kubectl cp \
  workload/benchmark/benchmark_runner.py \
  "$NAMESPACE/$POD:$REMOTE_SCRIPT"

local_sha="$(sha256sum workload/benchmark/benchmark_runner.py | awk '{print $1}')"
remote_sha="$(
  kubectl exec -n "$NAMESPACE" "$POD" -- \
    sha256sum "$REMOTE_SCRIPT" |
    awk '{print $1}'
)"
echo "LOCAL_RUNNER_SHA256=$local_sha"
echo "REMOTE_RUNNER_SHA256=$remote_sha"
[[ "$local_sha" == "$remote_sha" ]]
echo "RUNNER_STAGING=PASS"

for schema in "${SCHEMAS[@]}"; do
  password="$(schema_password "$schema")"

  for size in "${SIZES[@]}"; do
    scenario_name="${schema,,}-customers-${size}"
    local_dir="$LOCAL_ROOT/$scenario_name"
    remote_dir="$REMOTE_ROOT/results/$RUN_ID/$scenario_name"
    mkdir -p "$local_dir"

    load_dataset "$schema" "$size" "$password" "$local_dir"

    echo
    stable_health_gate

    echo
    echo "=== RUN BENCHMARK SCENARIO ==="
    echo "SCHEMA=$schema"
    echo "SIZE=$size"
    echo "REMOTE_RESULT_DIR=$remote_dir"

    kubectl exec -n "$NAMESPACE" "$POD" -- \
      rm -rf "$remote_dir"
    kubectl exec -n "$NAMESPACE" "$POD" -- \
      mkdir -p "$remote_dir"

    set +e
    kubectl exec -i -n "$NAMESPACE" "$POD" -- \
      env \
        DB_USER="$schema" \
        DB_PASSWORD="$password" \
        ORACLE_HOME="$ORACLE_HOME" \
      "$PYTHON_BIN" "$REMOTE_SCRIPT" \
        --schema "$schema" \
        --size "$size" \
        --workloads "$WORKLOADS" \
        --concurrencies "$CONCURRENCIES" \
        --iterations-per-client "$ITERATIONS" \
        --warmup-per-client "$WARMUP" \
        --repeats "$REPEATS" \
        --output-dir "$remote_dir" \
      2>&1 |
      tee "$local_dir/runner.log"
    runner_rc="${PIPESTATUS[0]}"
    set -e

    copy_remote_results "$remote_dir" "$local_dir"

    echo "BENCHMARK_SCENARIO_RC=$runner_rc"
    if (( runner_rc != 0 )); then
      echo "LIMITED_BENCHMARK_${MODE^^}=FAIL" >&2
      exit "$runner_rc"
    fi
  done
done

echo
echo "=== COMBINE RESULTS ==="
python3 workload/benchmark/combine_results.py "$LOCAL_ROOT"

echo
echo "=== RESULT FILES ==="
find "$LOCAL_ROOT" -type f -printf '%P\n' | sort

echo
echo "LIMITED_BENCHMARK_${MODE^^}=PASS"
echo "RESULT_ROOT=$LOCAL_ROOT"
echo "EVIDENCE_FILE=$EVIDENCE_FILE"
