# Add real estate and carbon credits as asset types

Status: implemented (backend + frontend), verified with tests, a real build, and a live
end-to-end check against Postgres. Not yet committed to git.

## Context

Laminaa currently supports three asset types (bond, equity, fund), all of which are secretly
the same shape under the hood: a fixed annual rate paid periodically against face value,
redeemed 1:1 for USDC principal at a scheduled maturity date. The goal is to add two more
asset classes: **real estate** (with a self-serve SME onboarding form using a real, free map)
and **carbon credits**. This is step one of two planned changes; auth (adding an investor-side
role/dashboard) is deliberately out of scope here and comes next.

Three parallel Explore passes over the actual code (not just CLAUDE.md's description) found
that this isn't a drop-in: the existing "asset-type handler" strategy pattern only covers
*payout amount*, and several other places (NAV valuation, redemption, creation-time fields)
have zero per-type behavior today, hardcoded to bond-shaped assumptions. Two decisions were
confirmed with the product owner that materially change carbon credits' shape: retirement
must be on-demand, per-holder, partial-amount, not a scheduled batch event like bond maturity,
and the real estate form needs a real interactive map, using OpenStreetMap (free, no API key),
not just plain text fields.

There's also a currently-dead precedent already in the repo: `server/config/asset_types.json`
already has a `real_estate` entry (`has_coupon: false`, `dividend_frequency: "monthly"`, etc.)
but nothing imports it (`ASSET_TYPES` has zero callers). This plan revives and extends that
file instead of inventing a new config mechanism.

## Key findings from exploration (grounding for the plan below)

- `app/handlers/__init__.py`'s `AssetTypeHandler` strategy is consulted **only** by
  `payout_service.py:44` (`get_handler(asset.asset_type)` for coupon amount). It is never
  consulted by `lifecycle_service.py` (NAV, maturity) or `issuance_service.py` (scheduling
  cadence), those are 100% asset-type-agnostic today, hardcoded bond-shaped.
- `issuance_service.py:22` hardcodes `_COUPON_INTERVAL_DAYS = 182` (semi-annual) for
  **every** asset type's scheduled events, regardless of what `periods_per_year` its handler
  claims. Equity/fund already claim quarterly but get scheduled semi-annually, a pre-existing
  bug this work should fix, since real estate's monthly cadence would otherwise be silently
  wrong too.
- `lifecycle_service.py:42-53` (`update_nav_from_oracle`) hardcodes a bond-shaped
  coupon-rate-vs-treasury-yield pricing formula inline, calling `treasury_rates.py` directly.
  There is no valuation-source abstraction (no `handlers/`-style registry for NAV).
- `chains/base.py`'s `force_redeem(token_ref, holder_ref, amount)` already burns from a
  *specific holder's* balance, fully decoupled from `pay_stable` (verified in
  `lifecycle_service.py:66-87`: two independent try/except'd calls, and there's already a
  precedent of calling `adapter.burn` with no payout at all, for the treasury remainder at
  maturity). This means on-demand, no-payout, per-holder retirement can reuse `force_redeem`
  as-is, no new `ChainAdapter` primitive needed. One known cosmetic wart: the EVM adapter
  hardcodes the on-chain memo string `"maturity_settlement"` inside `force_redeem`
  (`chains/evm/adapter.py:184`), so a carbon retirement will carry that (wrong) on-chain
  wording even though the off-chain audit log will correctly say `"credits_retired"`. Fixing
  that string properly means threading a `reason` param through all 4 chain adapters
  (EVM/Hedera/Solana/Sui), out of scope for this pass, flagged as a documented follow-up.
- `Asset` (orm.py:31-54) has no JSON/flexible column. `AuditLogEntry.details` and
  `ScheduledEvent.details` are both `Text` columns holding JSON-serialized payloads, an
  existing precedent to reuse for asset-type-specific metadata rather than adding N typed
  columns or new tables.
- `audit_log.action`/`.agent` are unconstrained `String` columns, a new action value like
  `"credits_retired"` needs zero schema change.
- The AI/MCP/Telegram tool layer (`services/ai/tools.py`) shares one `issue_asset` schema
  with the REST `AssetCreate` schema (`models/asset.py`), both need updating together, and a
  new `retire_credits` tool needs adding so all three interfaces get it at once (per
  CLAUDE.md's shared-tool-layer design).
- Frontend `create-asset-form.tsx` has a hardcoded 3-option `<select>` (bond/equity/fund) and
  renders every field (coupon rate, maturity date) unconditionally regardless of type. There
  is no existing asset-type-conditional field pattern to reuse (only chain-*family*
  conditionals exist), this is new UI work.

## Backend changes

1. **`server/config/asset_types.json`** — keep the existing `real_estate` entry, add a
   `carbon_credits` entry (`has_coupon: false`, `has_maturity: false`, `has_dividends: false`,
   `nav_update_frequency: "manual"`). This becomes the single source of truth for which
   fields apply to which type, used by both backend validation and the frontend form.

2. **`app/models/orm.py`** — add `Asset.metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)`
   (JSON-serialized), following the `AuditLogEntry.details` precedent. Holds type-specific
   fields: real estate maps to address, lat, lng, parcel/description; carbon credits maps to
   registry, vintage_year, serial/batch id, methodology. `Asset.status` gets a new valid
   value, `"retired"` (no schema change, it's already a free-text column).

3. **`app/handlers/__init__.py`** — add `RealEstateHandler(_RateHandler)` with
   `periods_per_year = 12` (monthly, matching the revived JSON config), and
   `CarbonCreditHandler(AssetTypeHandler)` (not rate-based, `period_payout_units` returns 0,
   since credits don't pay periodic income). Register both in `_HANDLERS` so `get_handler()`
   stops silently defaulting unknown types to `BondHandler`.

4. **`app/services/issuance_service.py`**:
   - Fix `_COUPON_INTERVAL_DAYS` to derive from `get_handler(asset_type).periods_per_year`
     (`365 // periods_per_year`) instead of one hardcoded constant.
   - Add creation-time validation driven by the (now-used) `ASSET_TYPES` config: reject
     `coupon_rate`/`maturity_date` for `carbon_credits`; require the new metadata fields for
     `real_estate` (address/lat/lng) and `carbon_credits` (registry/vintage/serial).
   - Accept a new optional `metadata: dict` param, JSON-serialize into `Asset.metadata_json`.

5. **`app/integrations/oracle/`** — add a small `ValuationSource` strategy mirroring the
   `handlers/` pattern (fixes the inline hardcoding found in `lifecycle_service.py`):
   - `BondFundValuationSource`: the existing coupon-rate-vs-treasury-yield formula, moved
     out of `lifecycle_service.py` verbatim (bond/equity/fund, no behavior change).
   - `RealEstateValuationSource` / `CarbonCreditValuationSource`: phase-1 stubs that
     preserve the last-set NAV (no live feed exists for either), issuers/agents update
     valuation via the already-generic `update_nav` direct-set path. Documented as a known
     phase-1 simplification with a clear seam to plug in a real feed later.
   - `LifecycleService.update_nav_from_oracle` calls `get_valuation_source(asset.asset_type)`
     instead of importing `get_yield_for_duration` directly.

6. **`app/services/lifecycle_service.py`** — add
   `retire_credits(asset_id, holder_ref, amount)`: validates `asset_type == "carbon_credits"`
   and `status == "active"`, calls `adapter.force_redeem(token_id, holder_ref, amount)` (no
   `pay_stable` call), decrements that holder's balance, sets `status = "retired"` only if
   total remaining supply hits 0 (partial retirement by one holder doesn't end the asset for
   others). Writes audit entry `agent="lifecycle"`, `action="credits_retired"`.

7. **`app/routes/assets.py`** — new `POST /api/assets/{asset_id}/retire` route
   (`holder_ref`, `amount`) calling the new service method.

8. **`app/services/ai/tools.py`** — add a `retire_credits` tool (same shared-layer pattern
   as every other tool, so chat/MCP/Telegram all get it); extend `issue_asset`'s schema with
   the new optional metadata fields; register `retire_credits` in `is_write_tool()`.

## Frontend changes

9. **`client/src/components/assets/create-asset-form.tsx`** — fetch the asset-type config
   (new thin route exposing `ASSET_TYPES`, or bundle it into an existing config response) to
   drive field visibility instead of the hardcoded 3-option `<select>` and always-visible
   coupon/maturity fields. Add `real_estate` and `carbon_credits` options; render each type's
   specific fields (address/map for real estate; registry/vintage/serial for carbon credits)
   conditionally.

10. **Real estate map** — add `leaflet` + `react-leaflet` (free, no API key) for an
    interactive map picker on the real estate form, using OpenStreetMap tiles, plus OSM's free
    Nominatim API for address search/geocoding. No new backend secret required.

11. **`client/src/app/(app)/assets/[id]/page.tsx`** — stop showing coupon_rate/maturity_date
    unconditionally; render type-specific fields from `metadata_json` (map view for real
    estate, registry/vintage for carbon credits); add a "Retire" action for carbon-credit
    holdings that calls the new endpoint.

## Explicitly out of scope for this pass

- Auth / investor-side dashboard (next planned phase).
- A live carbon-price or property-valuation feed (stubbed to manual NAV updates).
- Fixing the EVM adapter's hardcoded `"maturity_settlement"` on-chain memo string (cosmetic,
  needs touching all 4 adapters, flagged as a follow-up, not blocking).

## Verification

- `cd server && PYTHONPATH=. pytest` — extend `tests/test_chains.py`-style coverage with a
  case for `get_handler("real_estate")`/`get_handler("carbon_credits")` returning the new
  handlers, and a case confirming `_COUPON_INTERVAL_DAYS` derivation matches each handler's
  `periods_per_year`.
- Manually issue a `real_estate` asset via the dashboard form (with map-picked
  address/lat/lng) and confirm `ScheduledEvent` rows are created at the monthly cadence, not
  182 days.
- Manually issue a `carbon_credits` asset, confirm no coupon events are scheduled, call the
  new `/retire` endpoint for a partial amount, and confirm: the holder's balance drops by
  exactly that amount, no `pay_stable` call happens, the audit log shows `"credits_retired"`,
  and asset status stays `"active"` until the full supply is retired.
- Confirm the map picker renders OSM tiles and Nominatim address search works without any
  API key configured.
