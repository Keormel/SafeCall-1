#!/usr/bin/env bash
#
# Fill SafeCall through the public FastAPI endpoints.
#
# Usage:
#   ./backend/scripts/seed_api.sh [number_count]
#
# Environment:
#   API_URL=http://localhost:8000/api/v1 (also read from the repository .env)
#   PARALLELISM=8
#   VERBOSE=1

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/../../.env}"
api_url_was_set="${API_URL+x}"
api_url_value="${API_URL-}"
next_public_api_url_was_set="${NEXT_PUBLIC_API_URL+x}"
next_public_api_url_value="${NEXT_PUBLIC_API_URL-}"
parallelism_was_set="${PARALLELISM+x}"
parallelism_value="${PARALLELISM-}"
verbose_was_set="${VERBOSE+x}"
verbose_value="${VERBOSE-}"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi
if [[ -n "$api_url_was_set" ]]; then API_URL="$api_url_value"; fi
if [[ -n "$next_public_api_url_was_set" ]]; then NEXT_PUBLIC_API_URL="$next_public_api_url_value"; fi
if [[ -n "$parallelism_was_set" ]]; then PARALLELISM="$parallelism_value"; fi
if [[ -n "$verbose_was_set" ]]; then VERBOSE="$verbose_value"; fi

API_URL="${API_URL:-${NEXT_PUBLIC_API_URL:-http://localhost:8000}/api/v1}"
API_URL="${API_URL%/}"
COUNT="${1:-100}"
PARALLELISM="${PARALLELISM:-8}"
VERBOSE="${VERBOSE:-1}"
REPORTS_PER_DEVICE=10
AUTH_PER_MINUTE=20
AUTH_INTERVAL_SECONDS=3
AUTH_RETRY_DELAY_SECONDS=5
AUTH_RETRY_MAX_TIME_SECONDS=180
HEALTH_URL="${API_URL%/api/v1}/health"

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

[[ "$COUNT" =~ ^[1-9][0-9]*$ ]] || die "number_count must be a positive integer"
[[ "$PARALLELISM" =~ ^[1-9][0-9]*$ ]] || die "PARALLELISM must be a positive integer"
[[ "$VERBOSE" == 0 || "$VERBOSE" == 1 ]] || die "VERBOSE must be 0 or 1"
(( COUNT <= 1000000 )) || die "number_count cannot exceed 1000000"

for command in curl jq shuf; do
    command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

curl_options=(--silent --show-error --fail-with-body --retry 3 --retry-all-errors)
if (( VERBOSE )); then
    curl_options+=(--verbose)
fi

printf 'Checking %s ... ' "$API_URL"
curl --silent --show-error --fail --retry 3 --retry-all-errors \
    "$HEALTH_URL" >/dev/null
printf 'ok\n'

patterns=(
    'BANK|OTP,URGENCY'
    'BANK|OTP,SUSPICIOUS_TRANSACTION'
    'POLICE|TRANSFER,THREAT'
    'DELIVERY|CARD_DATA'
    'RELATIVE|TRANSFER,URGENCY'
    'INVESTMENT|CARD_DATA,INSTALL_APP'
    'OTHER|THREAT'
)
prefixes=(60 62 67 68 69 78 79)
tokens=()

worker_count=$(( (COUNT + REPORTS_PER_DEVICE - 1) / REPORTS_PER_DEVICE ))
(( worker_count < PARALLELISM )) && PARALLELISM="$worker_count"

json_actions() {
    local actions="$1"
    local result='['
    local action
    local first=true
    IFS=',' read -r -a action_list <<<"$actions"
    for action in "${action_list[@]}"; do
        if [[ "$first" == true ]]; then
            first=false
        else
            result+=','
        fi
        result+="\"$action\""
    done
    printf '%s]' "$result"
}

authenticate() {
    local device_id="$1"
    local response
    local attempt=1
    local max_attempts=$((AUTH_RETRY_MAX_TIME_SECONDS / AUTH_RETRY_DELAY_SECONDS + 1))

    while (( attempt <= max_attempts )); do
        printf '[auth] registering device %s (attempt %d/%d)\n' \
            "$device_id" "$attempt" "$max_attempts" >&2
        if response="$(curl "${curl_options[@]}" \
            --retry 0 \
            -X POST "${API_URL}/auth/device" \
            -H 'Content-Type: application/json' \
            --data "{\"device_id\":\"$device_id\"}")"; then
            if (( VERBOSE )); then
                printf '[auth] response: %s\n' "$(jq -c 'del(.access_token)' <<<"$response")" >&2
            fi
            jq --exit-status --raw-output '.access_token' <<<"$response"
            return 0
        fi

        wait_seconds=$AUTH_RETRY_DELAY_SECONDS
        printf '[auth] request was rejected; retrying in %ss\n' "$wait_seconds" >&2
        sleep "$wait_seconds"
        ((attempt++))
    done

    printf '[auth] failed after %d attempts\n' "$max_attempts" >&2
    return 1
}

printf 'Registering %d API devices ...\n' "$worker_count"
for ((worker = 0; worker < worker_count; worker++)); do
    if (( worker > 0 && worker % AUTH_PER_MINUTE == 0 )); then
        printf 'Auth safety window reached; waiting 60 seconds ...\n' >&2
        sleep 60
    fi
    token="$(authenticate "$(cat /proc/sys/kernel/random/uuid)")" ||
        die "could not register device $((worker + 1))"
    tokens[$worker]="$token"
    if (( worker + 1 < worker_count )); then
        sleep "$AUTH_INTERVAL_SECONDS"
    fi
done

submit_worker() {
    local worker="$1"
    local token="${tokens[$worker]}"
    local phone
    local category
    local actions
    local payload
    local response
    local pattern
    local prefix
    local report
    local report_start=$((worker * REPORTS_PER_DEVICE))

    for ((report = 0; report < REPORTS_PER_DEVICE && report_start + report < COUNT; report++)); do
        pattern="${patterns[$((RANDOM % ${#patterns[@]}))]}"
        prefix="${prefixes[$((RANDOM % ${#prefixes[@]}))]}"
        category="${pattern%%|*}"
        actions="${pattern#*|}"
        phone="+373${prefix}$(printf '%06d' "$(shuf -i 0-999999 -n 1)")"
        payload="$(jq -cn \
            --arg phone "$phone" \
            --arg category "$category" \
            --argjson actions "$(json_actions "$actions")" \
            '{phone: $phone, category: $category, actions: $actions}')"
        if (( VERBOSE )); then
            printf '[worker %s] POST /report phone=%s category=%s actions=%s\n' \
                "$worker" "$phone" "$category" "$actions" >&2
        fi
        if ! response="$(curl "${curl_options[@]}" \
            -X POST "${API_URL}/report" \
            -H "Authorization: Bearer ${token}" \
            -H 'Content-Type: application/json' \
            --data "$payload")"; then
            printf 'worker %s failed for %s\n' "$worker" "$phone" >&2
            return 1
        fi
        if (( VERBOSE )); then
            printf '[worker %s] response for %s: %s\n' "$worker" "$phone" "$response" >&2
        fi
    done
}

printf 'Submitting reports with %d concurrent workers ...\n' "$PARALLELISM"
pids=()
for ((worker = 0; worker < worker_count; worker++)); do
    submit_worker "$worker" &
    pids+=("$!")
    if (( ${#pids[@]} >= PARALLELISM )); then
        for pid in "${pids[@]}"; do
            wait "$pid"
        done
        pids=()
    fi
done
for pid in "${pids[@]}"; do
    wait "$pid"
done

printf 'Inserted %d numbers through %s/report\n' "$COUNT" "$API_URL"
