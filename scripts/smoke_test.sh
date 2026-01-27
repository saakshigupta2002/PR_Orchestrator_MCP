#!/usr/bin/env bash
set -euo pipefail

# Simple smoke test: create and destroy a workspace via stdio interface.

REQ_CREATE='{"tool": "workspace_create", "args": {"mode": "code", "ttl_minutes": 5}}'
REQ_DESTROY_PREFIX='{"tool": "workspace_destroy", "args": {"workspace_id": "'

echo "Running smoke test..."
output=$(printf "%s\n" "$REQ_CREATE" | python -m pr_orchestrator.server)
workspace_id=$(echo "$output" | jq -r '.workspace_id')
echo "Created workspace: $workspace_id"

REQ_DESTROY="${REQ_DESTROY_PREFIX}${workspace_id}'"\n'}"
printf "%s\n" "$REQ_DESTROY" | python -m pr_orchestrator.server
echo "Destroyed workspace: $workspace_id"