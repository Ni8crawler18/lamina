#!/usr/bin/env bash
set -e

export PATH="$HOME/.foundry/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load env
source "$SCRIPT_DIR/../server/.env"

if [ -z "$PRIVATE_KEY" ]; then
  echo "ERROR: PRIVATE_KEY not set in server/.env"
  exit 1
fi

WALLET=$(cast wallet address --private-key "$PRIVATE_KEY")
BALANCE=$(cast balance "$WALLET" --rpc-url "$ARBITRUM_RPC_URL" --ether 2>/dev/null || echo "0")
echo ""
echo "  Wallet  : $WALLET"
echo "  Balance : $BALANCE ETH"
echo "  Chain   : Robinhood Chain testnet (ID 46630)"
echo ""

# Minimum balance check
if python3 -c "exit(0 if float('$BALANCE') >= 0.01 else 1)" 2>/dev/null; then
  echo "Sufficient balance. Deploying..."
else
  echo "❌ Insufficient balance. Need at least 0.01 ETH."
  echo ""
  echo "  Get testnet ETH from:"
  echo "  → https://faucet.testnet.chain.robinhood.com"
  echo "    (paste your address: $WALLET)"
  echo ""
  echo "  Or bridge Sepolia ETH:"
  echo "  → https://bridge.testnet.chain.robinhood.com"
  echo ""
  exit 1
fi

echo "Building contracts..."
forge build --quiet

echo "Deploying..."
forge script script/Deploy.s.sol \
  --rpc-url "$ARBITRUM_RPC_URL" \
  --private-key "$PRIVATE_KEY" \
  --broadcast \
  --chain-id 46630 \
  -vv 2>&1 | tee /tmp/lamina_deploy.log

# Extract addresses from log
AUDIT=$(grep "AuditLog deployed" /tmp/lamina_deploy.log | awk '{print $NF}' | tail -1)
FACTORY=$(grep "LaminaFactory deployed" /tmp/lamina_deploy.log | awk '{print $NF}' | tail -1)

if [ -n "$AUDIT" ] && [ -n "$FACTORY" ]; then
  echo ""
  echo "✅ Deployment complete!"
  echo ""
  echo "  AuditLog    : $AUDIT"
  echo "  Factory     : $FACTORY"
  echo ""
  echo "  Explorer:"
  echo "  → $EXPLORER_URL/address/$AUDIT"
  echo "  → $EXPLORER_URL/address/$FACTORY"
  echo ""

  # Patch server/.env automatically
  ENV_FILE="$SCRIPT_DIR/../server/.env"
  sed -i "s|^AUDIT_LOG_ADDRESS=.*|AUDIT_LOG_ADDRESS=$AUDIT|" "$ENV_FILE"
  sed -i "s|^FACTORY_ADDRESS=.*|FACTORY_ADDRESS=$FACTORY|" "$ENV_FILE"
  echo "  ✅ server/.env updated with contract addresses"
else
  echo ""
  echo "⚠️  Could not parse addresses from output."
  echo "  Check /tmp/lamina_deploy.log and update server/.env manually."
fi
