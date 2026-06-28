#!/usr/bin/env bash
# Deploy ModClear lên GenLayer testnet (hoặc localnet).
#
# Chuẩn bị:
#   1. npm install -g genlayer
#   2. Lấy testnet GEN: https://www.genlayer.com/testnet
#   3. genlayer keygen / import account
#
# Quy trình: deploy storage_test.py TRƯỚC, rồi mod_clear.py.

set -euo pipefail
NETWORK="${1:-testnet-asimov}"   # 'localnet' để chạy local

echo "==> Deploying sanity contract (storage_test.py)"
genlayer deploy --contract contracts/storage_test.py --network "$NETWORK"

echo ""
echo "==> Sanity OK. Deploying main contract (mod_clear.py)"
genlayer deploy --contract contracts/mod_clear.py --network "$NETWORK"

echo ""
echo "==> Done. Dán địa chỉ contract vào frontend/src/config.js"
