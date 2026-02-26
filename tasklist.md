# Lamina v1.2 — From Prototype to Product

## Tier 1: Makes the demo believable (real compliance, real payments, real user value)

- [ ] **OFAC Sanctions Screening**
  - Hit the free OFAC SDN API on every whitelist add and transfer validation
  - Block sanctioned addresses/names before any on-chain operation
  - Log screening results to HCS audit trail
  - Show screening status in the compliance dashboard

- [ ] **USDC Coupon Payments**
  - Use Hedera's native USDC token (testnet) for coupon distribution instead of HBAR
  - Create a treasury/escrow pattern — fund manager deposits USDC, agent distributes
  - Show payment amounts in USD terms, not HBAR
  - Receipt per payment with tx hash

- [ ] **Investor Portal**
  - New `/portfolio` page — an investor connects wallet and sees their holdings
  - Position summary: token balance, current NAV value, accrued interest
  - Payment history: all coupons received with dates and amounts
  - Upcoming events: next coupon date, maturity date, estimated payout
  - Download: investor statement PDF for their holdings only

- [ ] **Human-in-the-Loop Approvals**
  - Agent proposes actions, manager confirms before execution
  - Approval queue page: pending coupon distributions, whitelist additions, large transfers
  - Threshold-based: auto-approve below $X, require approval above
  - Approval/rejection logged to HCS

- [ ] **Event Timeline**
  - Visual timeline on dashboard showing full asset lifecycle
  - Upcoming coupons with countdown timers
  - Maturity date with progress bar (% of bond life elapsed)
  - Past events with status (completed/failed) and tx links to HashScan
  - Calendar view option

## Tier 2: Makes it usable by a real pilot customer

- [ ] **Authentication & Roles**
  - Login system (wallet-based or email)
  - Roles: fund manager, compliance officer, investor, admin
  - Role-based page access and action permissions

- [ ] **Document Management**
  - Upload/attach offering documents (PPM, subscription agreements)
  - Store on Hedera File Service (HFS) for immutability
  - Link documents to specific assets
  - Investor-facing document downloads

- [ ] **API & Webhooks**
  - REST API with API key auth for external integrations
  - Webhook notifications: asset created, coupon paid, compliance alert
  - OpenAPI/Swagger documentation
  - SDK for programmatic access

- [ ] **Multi-Asset Portfolio View**
  - Aggregate dashboard across all managed assets
  - Total AUM, total holders, upcoming obligations
  - Risk indicators: assets nearing maturity, overdue coupons
  - Filterable by asset type, jurisdiction, status

- [ ] **Tax Document Generation**
  - 1099-INT for US bond holders
  - Per-investor annual tax summary
  - Bulk generation and distribution
