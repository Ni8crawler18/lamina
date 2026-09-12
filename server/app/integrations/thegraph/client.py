"""Query the Laminaa subgraph (see /subgraph at the repo root) on The Graph.

Gives the agent a live, on-chain-sourced view of an asset's full lifecycle
history (issuance, KYC grants, transfer approvals, audit trail), independent
of Laminaa's own Postgres mirror. Used by the `query_lifecycle_history`
agent tool in `services/ai/tools.py`.
"""

import logging

import aiohttp

from app.config import get_settings

logger = logging.getLogger(__name__)

_QUERY = """
query AssetHistory($tokenAddress: ID!) {
  asset(id: $tokenAddress) {
    id
    name
    symbol
    topicId
    deployer
    deployedAt
    auditEntries(orderBy: sequenceNumber) {
      sequenceNumber
      agent
      action
      timestamp
      txHash
    }
    kycEvents(orderBy: timestamp) {
      account
      granted
      timestamp
      txHash
    }
    transfers(orderBy: timestamp) {
      from
      to
      amount
      timestamp
      txHash
    }
  }
}
"""


async def get_asset_history(token_address: str) -> dict:
    """Fetch one asset's full on-chain history from the deployed subgraph.

    Returns {"error": ...} if THEGRAPH_SUBGRAPH_URL isn't configured yet, or
    if the query fails — callers (the agent) should surface that plainly
    rather than pretend there's no history.
    """
    url = get_settings().thegraph_subgraph_url
    if not url:
        return {"error": "THEGRAPH_SUBGRAPH_URL is not configured — deploy /subgraph to "
                          "Subgraph Studio first and set the env var to its query URL."}
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"query": _QUERY, "variables": {"tokenAddress": token_address.lower()}}
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return {"error": f"subgraph query failed: HTTP {resp.status}"}
                data = await resp.json()
                if "errors" in data:
                    return {"error": f"subgraph query errors: {data['errors']}"}
                asset = data.get("data", {}).get("asset")
                if asset is None:
                    return {"error": f"no asset indexed for token {token_address} "
                                      "(not deployed via LaminaFactory on this chain, or not yet synced)"}
                return asset
    except Exception as e:
        logger.warning("[thegraph] query failed: %s", e)
        return {"error": str(e)}
