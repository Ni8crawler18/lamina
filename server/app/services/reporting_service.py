"""Reporting service — production-grade regulatory PDF reports.

Three report types, each with a tailored layout but a shared production shell
(letterhead, document-control block, diagonal CONFIDENTIAL watermark, numbered
sections, on-chain verification with explorer links, attestation block with an
authorised-signature area and a SHA-256 document-integrity fingerprint, and a
standardised footer with page numbers):

  * compliance        — regulatory controls, investor compliance, holder register
  * investor_statement — holdings, valuation, distribution history for a holder
  * audit_summary     — controls operation and the on-chain audit trail

Narrative prose comes from Claude when an API key is set, otherwise a
deterministic fallback. Both are constrained to *verifiable, factual, technical*
statements — they do not assert legal/regulatory conclusions (e.g. "fully
compliant", specific regulation citations) or invent facts. All wording is
chain-neutral.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime

from app.chains.registry import get_registry
from app.config import get_settings
from app.repositories.assets import AssetRepository
from app.repositories.audit import AuditRepository
from app.repositories.events import EventRepository
from app.repositories.holders import HolderRepository
from app.repositories.reports import ReportRepository
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")

REPORT_META = {
    "compliance": ("Compliance Report", "CMP"),
    "investor_statement": ("Investor Statement", "INV"),
    "audit_summary": ("Audit Summary Report", "AUD"),
}

# ── brand palette (mirrors the house design system) ──────────────────────────
INK = 0x141420
MUTED = 0x6B7280
HAIRLINE = 0xE3E1EE
PANEL = 0xF6F5FC
IRIS = 0x6D5AE6
IRIS_DARK = 0x5A3DB5
IRIS_MID = 0x7C5CE7
IRIS_LIGHT = 0xA78BFA
GREEN = 0x16855A
AMBER = 0xB45309


def _mask(ref: str | None) -> str:
    if not ref:
        return "—"
    return ref if len(ref) <= 16 else f"{ref[:6]}…{ref[-4:]}"


def _clear(status: str | None) -> bool:
    return (status or "").lower() not in ("", "pending", "hit", "match", "blocked", "flagged")


def _details(entry) -> dict:
    raw = getattr(entry, "details", None)
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}


def _ts(value) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        return f"{value:%Y-%m-%d %H:%M UTC}"
    return str(value)[:19].replace("T", " ")


class ReportingError(Exception):
    pass


class ReportingService:
    def __init__(self, session):
        self.session = session
        self.assets = AssetRepository(session)
        self.holders = HolderRepository(session)
        self.events = EventRepository(session)
        self.reports = ReportRepository(session)
        self.audit_log = AuditRepository(session)
        self.audit = AuditService(session)

    async def _gather(self, asset_id: int):
        asset = await self.assets.get(asset_id)
        if not asset:
            raise ReportingError("Asset not found")
        holders = await self.holders.list_for_asset(asset_id)
        events = await self.events.list_for_asset(asset_id)
        audit_entries = await self.audit_log.list_for_asset(asset_id, limit=200)
        registry = get_registry()
        adapter = registry.adapter(asset.chain)
        try:
            cfg = registry.get_config(asset.chain)
        except Exception:
            cfg = None
        return asset, holders, events, audit_entries, adapter, cfg

    async def generate_report(
        self, asset_id: int, period: str = "Q1 2026", report_type: str = "compliance"
    ) -> dict:
        asset, holders, events, audit_entries, adapter, cfg = await self._gather(asset_id)

        narrative = self._narrative(asset, holders, events, audit_entries, period, report_type, cfg)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filepath, content = self._render_pdf(
            asset, holders, events, audit_entries, narrative, period, report_type, adapter, cfg
        )

        report = await self.reports.create(
            asset_id=asset_id, report_type=report_type, period=period,
            file_path=filepath, content=content,
        )
        await self.audit.record(
            adapter, asset.topic_id, asset.id, "reporting", "report_generated",
            {"report_type": report_type, "period": period},
        )
        return {
            "report_id": report.id, "asset_id": asset_id, "chain": asset.chain,
            "report_type": report_type, "period": period, "file_path": filepath,
            "narrative_preview": narrative[:400],
        }

    async def rerender_report(self, report) -> bytes:
        """Re-render an existing report whose PDF bytes were lost (e.g. ephemeral
        disk wiped on redeploy). Uses the deterministic fallback narrative so a
        download never blocks on, or costs, an LLM call. Backfills the row."""
        asset, holders, events, audit_entries, adapter, cfg = await self._gather(report.asset_id)
        narrative = self._fallback_narrative(
            asset, holders, events, audit_entries, report.period, report.report_type
        )
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filepath, content = self._render_pdf(
            asset, holders, events, audit_entries, narrative,
            report.period, report.report_type, adapter, cfg,
        )
        report.content = content
        report.file_path = filepath
        await self.session.flush()
        return content

    # ── narrative (constrained to verifiable facts) ───────────────────────────
    def _narrative(self, asset, holders, events, audit_entries, period, report_type, cfg) -> str:
        settings = get_settings()
        if settings.anthropic_api_key:
            try:
                return self._claude_narrative(
                    asset, holders, events, audit_entries, period, report_type, cfg
                )
            except Exception as e:
                logger.warning("Claude narrative failed, using fallback: %s", e)
        return self._fallback_narrative(asset, holders, events, audit_entries, period, report_type)

    @staticmethod
    def _stats(holders, events, audit_entries):
        whitelisted = sum(1 for h in holders if h.whitelisted)
        kyc_ok = sum(1 for h in holders if h.kyc_status == "approved" or h.kyc_granted)
        screened = sum(1 for h in holders if (h.ofac_status or "pending") != "pending")
        cleared = sum(1 for h in holders if _clear(h.ofac_status))
        completed = sum(1 for e in events if e.status == "completed")
        dists = [_details(e) for e in audit_entries if e.action == "coupon_distributed"]
        dist_total = round(sum(float(d.get("total_usdc", 0) or 0) for d in dists), 6)
        return whitelisted, kyc_ok, screened, cleared, completed, len(dists), dist_total

    def _claude_narrative(self, asset, holders, events, audit_entries, period, report_type, cfg) -> str:
        import anthropic

        wl, kyc, screened, cleared, completed, dist_n, dist_total = self._stats(
            holders, events, audit_entries
        )
        network = cfg.name if cfg else asset.chain
        client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
        facts = (
            f"- Security: {asset.name} ({asset.symbol}), a tokenized {asset.asset_type}\n"
            f"- Settlement network: {network}\n"
            f"- NAV (operator record): ${asset.nav:,.2f}\n"
            f"- Stated coupon rate: {asset.coupon_rate * 100:.2f}% per annum\n"
            f"- Declared jurisdiction tag: {asset.jurisdiction}\n"
            f"- Declared eligible-investor tag: {asset.investor_type}\n"
            f"- Registered holders: {len(holders)}; whitelisted: {wl}; "
            f"KYC-verified: {kyc}; OFAC-screened: {screened}; OFAC-cleared: {cleared}\n"
            f"- Lifecycle events completed: {completed}\n"
            f"- Coupon distributions recorded: {dist_n}, totalling {dist_total} USDC\n"
            f"- All actions written to an on-chain audit log and mirrored in the operator's database\n"
        )
        prompt = (
            f"You are drafting the factual narrative section of a {report_type.replace('_', ' ')} "
            f"for the reporting period {period}. Use ONLY the verified data below.\n\n"
            f"{facts}\n"
            "STRICT RULES:\n"
            "- State only what the data supports. Do NOT invent figures, dates, prospectus terms, "
            "or counterparties.\n"
            "- Do NOT assert legal or regulatory conclusions. Never say the security is 'compliant', "
            "'fully compliant', or 'in compliance with the law'. Do NOT cite specific regulations "
            "(e.g. Regulation D, MiCA) unless they appear verbatim in the data above.\n"
            "- Describe controls in factual, technical terms (e.g. 'transfers were gated against an "
            "on-chain identity registry'), and attribute status to 'the operator's records'.\n"
            "- Use measured, hedged language ('based on the records', 'as recorded'). "
            "Note that the jurisdiction and investor-type values are configuration tags, not legal "
            "determinations.\n"
            "Write exactly 3 short paragraphs. Plain prose, no markdown, no headings, no bullets."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=650,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    def _fallback_narrative(self, asset, holders, events, audit_entries, period, report_type) -> str:
        wl, kyc, screened, cleared, completed, dist_n, dist_total = self._stats(
            holders, events, audit_entries
        )
        n = len(holders)
        dist_line = (
            f"{dist_n} coupon distribution(s) totalling {dist_total:,.2f} USDC were recorded"
            if dist_n else "No coupon distributions were recorded"
        )
        if report_type == "investor_statement":
            return (
                f"This statement summarises, for the period {period}, the recorded position(s) in "
                f"{asset.name} ({asset.symbol}) held through the platform. Position data reflects the "
                f"operator's system of record as at the date of issue and is reconciled against the "
                f"token's on-chain balances.\n\n"
                f"{dist_line} for the security during the period. The instrument carries a stated "
                f"coupon rate of {asset.coupon_rate * 100:.2f}% per annum; distribution amounts are "
                f"settled in USDC to whitelisted holders.\n\n"
                f"All position changes and distributions are written to an on-chain audit log and "
                f"mirrored in the operator's database, enabling independent verification of the "
                f"figures shown in this statement."
            )
        if report_type == "audit_summary":
            return (
                f"This summary describes the operation of the platform's automated controls over "
                f"{asset.name} ({asset.symbol}) during {period}, based on the on-chain audit log and "
                f"the operator's system of record. {len(audit_entries)} audit record(s) were "
                f"reviewed.\n\n"
                f"During the period {completed} lifecycle event(s) were completed and {dist_line.lower()}. "
                f"Of {n} registered holder(s), {kyc} completed KYC/AML verification, {screened} were "
                f"screened against the OFAC SDN list, and {wl} were whitelisted for transfer. These "
                f"figures describe the technical controls applied; they are not a legal opinion on the "
                f"security's regulatory status.\n\n"
                f"Each state-changing action was written to an immutable on-chain audit log and mirrored "
                f"in the operator's database, producing a tamper-evident trail that can be reconciled "
                f"independently on the network's block explorer."
            )
        # compliance (default)
        return (
            f"During the period {period}, the platform's automated controls were applied to "
            f"{asset.name} ({asset.symbol}). Based on the operator's records as at the date of issue, "
            f"{wl} of {n} registered holder(s) were whitelisted for transfer; {kyc} completed KYC/AML "
            f"identity verification and {cleared} were cleared against OFAC sanctions screening. "
            f"The jurisdiction ({asset.jurisdiction}) and eligible-investor ({asset.investor_type}) "
            f"values are configuration tags applied at issuance, not legal determinations.\n\n"
            f"The instrument carries a stated coupon rate of {asset.coupon_rate * 100:.2f}% per annum "
            f"and an operator-recorded NAV of ${asset.nav:,.2f}. {completed} lifecycle event(s) were "
            f"completed and {dist_line.lower()} during the period. Transfers were gated on-chain "
            f"against an identity registry so that only verified, whitelisted accounts could hold or "
            f"receive units.\n\n"
            f"Every state-changing action was written to an immutable on-chain audit log and mirrored "
            f"in the operator's database, providing an independently verifiable, tamper-evident record "
            f"of all activity affecting the security during the period."
        )

    # ── PDF ──────────────────────────────────────────────────────────────────
    def _render_pdf(
        self, asset, holders, events, audit_entries, narrative, period, report_type, adapter, cfg
    ) -> tuple[str, bytes]:
        import io

        from reportlab.lib.colors import HexColor
        from reportlab.lib.enums import TA_JUSTIFY
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.platypus import (
            HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
            TableStyle,
        )

        title, code = REPORT_META.get(report_type, ("Report", "RPT"))
        gen = datetime.utcnow()
        report_no = f"LMNA-{code}-{asset.id:04d}-{gen:%Y%m%d}"

        wl, kyc_ok, screened, cleared, completed, dist_n, dist_total = self._stats(
            holders, events, audit_entries
        )
        distributions = [
            {**_details(e), "ts": getattr(e, "created_at", None)}
            for e in reversed(audit_entries) if e.action == "coupon_distributed"
        ]
        fingerprint_src = json.dumps(
            {
                "report_no": report_no, "type": report_type, "period": period,
                "asset": asset.id, "name": asset.name, "symbol": asset.symbol,
                "token": asset.token_id, "chain": asset.chain, "nav": asset.nav,
                "holders": len(holders), "whitelisted": wl, "kyc": kyc_ok,
                "ofac_cleared": cleared, "events": completed, "distributions": dist_n,
                "dist_total": dist_total, "generated": gen.isoformat(), "narrative": narrative,
            },
            sort_keys=True, default=str,
        )
        integrity = hashlib.sha256(fingerprint_src.encode()).hexdigest()

        fname = f"{report_no}.pdf"
        filepath = os.path.join(REPORTS_DIR, fname)
        buf = io.BytesIO()

        LEFT = 0.85 * inch
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=LEFT, rightMargin=0.85 * inch,
            topMargin=1.45 * inch, bottomMargin=1.0 * inch,
            title=f"{title} — {asset.name}", author="Laminaa",
            subject=f"{title} ({period})",
        )
        W = doc.width

        # ── styles ──
        base = getSampleStyleSheet()
        body = ParagraphStyle(
            "Body", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
            leading=14, textColor=HexColor(INK), alignment=TA_JUSTIFY,
        )
        kicker = ParagraphStyle(
            "Kicker", fontName="Helvetica-Bold", fontSize=8, leading=10,
            textColor=HexColor(IRIS), spaceAfter=4,
        )
        h_title = ParagraphStyle(
            "DocTitle", fontName="Helvetica-Bold", fontSize=22, leading=25,
            textColor=HexColor(INK), spaceAfter=2,
        )
        h_sub = ParagraphStyle(
            "DocSub", fontName="Helvetica", fontSize=11, leading=15, textColor=HexColor(MUTED),
        )
        section = ParagraphStyle(
            "Section", fontName="Helvetica-Bold", fontSize=11.5, leading=14,
            textColor=HexColor(IRIS_DARK), spaceBefore=2, spaceAfter=4,
        )
        cell = ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, leading=12,
                              textColor=HexColor(INK))
        cell_b = ParagraphStyle("CellB", parent=cell, fontName="Helvetica-Bold")
        cell_s = ParagraphStyle("CellS", parent=cell, fontSize=8, leading=11,
                                textColor=HexColor(MUTED))
        sig_lbl = ParagraphStyle("SigLbl", fontName="Helvetica-Bold", fontSize=8,
                                 textColor=HexColor(MUTED), leading=11)

        def link(text, url):
            return f'<a href="{url}" color="#6D5AE6">{text}</a>' if url else text

        def explorer_addr(ref):
            try:
                return adapter.explorer_address(ref) if ref else ""
            except Exception:
                return ""

        counter = {"n": 0}

        def sec(label):
            counter["n"] += 1
            return [
                Spacer(1, 12),
                Paragraph(f"{counter['n']}.&nbsp;&nbsp;{label}", section),
                HRFlowable(width="100%", thickness=0.6, color=HexColor(HAIRLINE),
                           spaceBefore=1, spaceAfter=7),
            ]

        def kv_table(rows, panel=False):
            data = [[Paragraph(str(k), cell_b),
                     v if isinstance(v, Paragraph) else Paragraph(str(v), cell)] for k, v in rows]
            t = Table(data, colWidths=[0.34 * W, 0.66 * W])
            style = [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 10 if panel else 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10 if panel else 0),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, HexColor(HAIRLINE)),
            ]
            if panel:
                style += [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor(PANEL)),
                    ("BOX", (0, 0), (-1, -1), 0.6, HexColor(HAIRLINE)),
                ]
            t.setStyle(TableStyle(style))
            return t

        def grid_table(head, rows, widths):
            data = [[Paragraph(f"<b>{h}</b>", cell_s) for h in head]]
            data += [[Paragraph(str(c), cell_s) for c in r] for r in rows]
            t = Table(data, colWidths=[w * W for w in widths], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor(IRIS_DARK)),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor(0xFFFFFF)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor(0xFFFFFF), HexColor(PANEL)]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, HexColor(HAIRLINE)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]))
            return t

        # ── header / footer / watermark (drawn on every page) ──
        def diamond(c, cx, cy, w, h, color):
            c.setFillColor(HexColor(color))
            p = c.beginPath()
            p.moveTo(cx, cy + h); p.lineTo(cx + w, cy)
            p.lineTo(cx, cy - h); p.lineTo(cx - w, cy); p.close()
            c.drawPath(p, fill=1, stroke=0)

        def decorate(c, page_no, page_count):
            pw, ph = A4
            # diagonal CONFIDENTIAL watermark (faint, behind the content visually)
            c.saveState()
            c.translate(pw / 2, ph / 2)
            c.rotate(45)
            c.setFont("Helvetica-Bold", 76)
            c.setFillColor(HexColor(IRIS))
            try:
                c.setFillAlpha(0.06)
            except Exception:
                c.setFillColor(HexColor(0xF0EEFB))
            c.drawCentredString(0, 0, "CONFIDENTIAL")
            c.restoreState()

            # logo + wordmark
            lx, ly = LEFT + 9, ph - 0.62 * inch
            diamond(c, lx, ly - 5, 9, 5, IRIS_DARK)
            diamond(c, lx, ly, 9, 5, IRIS_MID)
            diamond(c, lx, ly + 5, 9, 5, IRIS_LIGHT)
            c.setFillColor(HexColor(INK))
            c.setFont("Helvetica-Bold", 14)
            c.drawString(lx + 18, ly - 4, "LAMINAA")
            c.setFillColor(HexColor(MUTED))
            c.setFont("Helvetica", 6.6)
            c.drawString(lx + 18, ly - 13, "AUTONOMOUS RWA LIFECYCLE & COMPLIANCE PLATFORM")
            rx = pw - 0.85 * inch
            c.setFillColor(HexColor(IRIS))
            c.setFont("Helvetica-Bold", 7)
            c.drawRightString(rx, ly + 2, "CONFIDENTIAL")
            c.setFillColor(HexColor(MUTED))
            c.setFont("Helvetica", 7)
            c.drawRightString(rx, ly - 8, report_no)
            c.setStrokeColor(HexColor(IRIS))
            c.setLineWidth(1.2)
            c.line(LEFT, ph - 0.92 * inch, pw - 0.85 * inch, ph - 0.92 * inch)

            # footer
            fy = 0.62 * inch
            c.setStrokeColor(HexColor(HAIRLINE))
            c.setLineWidth(0.6)
            c.line(LEFT, fy + 14, pw - 0.85 * inch, fy + 14)
            c.setFillColor(HexColor(MUTED))
            c.setFont("Helvetica", 6.8)
            c.drawString(LEFT, fy + 4,
                         "Generated by the Laminaa autonomous agent. Informational record — "
                         "not legal, tax, or investment advice.")
            c.drawRightString(pw - 0.85 * inch, fy + 4, f"Page {page_no} of {page_count}")
            c.setFont("Helvetica", 6.2)
            c.drawString(LEFT, fy - 6, f"Doc {report_no}")
            c.drawRightString(pw - 0.85 * inch, fy - 6,
                              f"SHA-256 {integrity[:16]}…{integrity[-8:]}")

        class NumberedCanvas(pdfcanvas.Canvas):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self._saved = []

            def showPage(self):  # noqa: N802
                self._saved.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                n = len(self._saved)
                for state in self._saved:
                    self.__dict__.update(state)
                    decorate(self, self._pageNumber, n)
                    super().showPage()
                super().save()

        # ── shared values ──
        network = f"{cfg.name} (chain ID {cfg.chain_id})" if cfg else asset.chain
        token_std = "ERC-3643 permissioned security token" if (cfg and cfg.family == "evm") \
            else "Permissioned security token"
        token_url = explorer_addr(asset.token_id)
        issuer = asset.issuer_name or asset.owner or "Operator-managed"
        status_color = GREEN if (cleared >= wl and wl == len(holders) and len(holders) > 0) else AMBER
        status_txt = "CONTROLS SATISFIED" if status_color == GREEN else "REVIEW REQUIRED"

        # ── reusable section builders ──
        def particulars():
            return sec("Security Particulars") + [kv_table([
                ("Legal Name", asset.name),
                ("Ticker Symbol", asset.symbol),
                ("Asset Class", asset.asset_type.replace("_", " ").title()),
                ("Token Standard", token_std),
                ("Token Contract", Paragraph(link(asset.token_id or "—", token_url), cell)),
                ("Settlement Network", network),
                ("Total Supply", f"{asset.total_supply:,} units"),
                ("Net Asset Value (NAV)", f"${asset.nav:,.2f} (operator record)"),
                ("Coupon / Distribution Rate", f"{asset.coupon_rate * 100:.2f}% per annum"),
                ("Maturity Date", asset.maturity_date or "—"),
                ("Lifecycle Status", asset.status.title()),
                ("Eligible-Investor Tag", (asset.investor_type or "accredited").replace("_", " ").title()),
            ])]

        def framework():
            out = sec("Control Framework & Methodology")
            out.append(Paragraph(
                "The platform applies the following automated controls to every state-changing "
                "action affecting the security. These are technical controls; they are not a legal "
                "determination of regulatory status.", body))
            out.append(Spacer(1, 6))
            out.append(kv_table([
                ("Token Standard", f"{token_std}; transfers are gated on-chain against an identity "
                 "registry so only verified accounts can hold or receive units."),
                ("Investor Onboarding", "KYC/AML identity verification is recorded before an account "
                 "is whitelisted."),
                ("Sanctions Screening", "Accounts are screened against the OFAC SDN list using fuzzy "
                 "name matching (≈85% threshold) and exact address matching; the list is refreshed "
                 "daily."),
                ("Transfer Restrictions", "Only whitelisted, KYC-verified, non-frozen accounts may "
                 "transact; other transfers are rejected at the contract level."),
                ("Eligibility Tags", f"Configuration tags applied at issuance: jurisdiction "
                 f"'{asset.jurisdiction}', investor type '{asset.investor_type}'. Tags do not "
                 "constitute legal advice."),
                ("Audit & Recordkeeping", "Every action is written to an immutable on-chain audit log "
                 "and mirrored in the operator's database."),
            ]))
            return out

        def compliance_summary():
            out = sec("Investor Compliance Summary")
            out.append(kv_table([
                ("Registered Holders", str(len(holders))),
                ("KYC/AML Verified", f"{kyc_ok} of {len(holders)}"),
                ("OFAC Screened", f"{screened} of {len(holders)}"),
                ("OFAC Cleared", f"{cleared} of {len(holders)}"),
                ("Whitelisted for Transfer", f"{wl} of {len(holders)}"),
                ("Control Determination",
                 Paragraph(f'<b><font color="#{status_color:06X}">{status_txt}</font></b>', cell)),
            ], panel=True))
            if holders:
                out.append(Spacer(1, 10))
                out.append(Paragraph("Holder Register", cell_b))
                out.append(Spacer(1, 4))
                rows = [[
                    str(i), _mask(h.account_id), h.name or "—", f"{h.balance:,}",
                    (h.kyc_status or "—").title(), (h.ofac_status or "—").title(),
                    h.jurisdiction or "—", "Yes" if h.whitelisted else "No",
                ] for i, h in enumerate(holders[:60], 1)]
                out.append(grid_table(
                    ["#", "Holder Account", "Name", "Units", "KYC", "OFAC", "Juris.", "WL"], rows,
                    [0.04, 0.26, 0.18, 0.12, 0.12, 0.12, 0.08, 0.08]))
                if len(holders) > 60:
                    out += [Spacer(1, 4),
                            Paragraph(f"Showing first 60 of {len(holders)} holders.", cell_s)]
            return out

        def holdings():
            out = sec("Holdings & Valuation")
            whole = asset.total_supply / (10 ** asset.decimals) if asset.decimals else asset.total_supply
            rows = []
            for i, h in enumerate(holders[:60], 1):
                units = h.balance / (10 ** asset.decimals) if asset.decimals else h.balance
                pct = (h.balance / asset.total_supply * 100) if asset.total_supply else 0
                rows.append([str(i), _mask(h.account_id), h.name or "—",
                             f"{units:,.2f}", f"{pct:.2f}%",
                             "Yes" if h.whitelisted else "No"])
            if not rows:
                rows = [["—", "No positions on record", "—", "—", "—", "—"]]
            out.append(grid_table(
                ["#", "Holder Account", "Name", "Units Held", "% of Supply", "WL"], rows,
                [0.05, 0.30, 0.25, 0.16, 0.14, 0.10]))
            out += [Spacer(1, 6), Paragraph(
                f"Total issued: {whole:,.2f} units. Stated coupon rate "
                f"{asset.coupon_rate * 100:.2f}% per annum, settled in USDC to whitelisted holders. "
                f"Unit figures are reconciled against on-chain balances; no market valuation is "
                f"implied.", cell_s)]
            return out

        def distributions_section():
            out = sec("Distribution History")
            if distributions:
                rows = [[_ts(d.get("ts")),
                         str(d.get("num_holders", "—")),
                         f"{float(d.get('total_usdc', 0) or 0):,.2f}",
                         f"{float(d.get('coupon_rate', asset.coupon_rate) or 0) * 100:.2f}%"]
                        for d in distributions]
                out.append(grid_table(
                    ["Date (UTC)", "Holders Paid", "Total (USDC)", "Rate"], rows,
                    [0.34, 0.22, 0.24, 0.20]))
                out += [Spacer(1, 5), Paragraph(
                    f"{dist_n} distribution(s) recorded, totalling {dist_total:,.2f} USDC.", cell_s)]
            else:
                out.append(Paragraph(
                    "No coupon or dividend distributions were recorded for this security during the "
                    "period.", body))
            return out

        def lifecycle():
            out = sec("Lifecycle Activity")
            if events:
                agg: dict[str, list[int]] = {}
                for e in events:
                    a = agg.setdefault(e.event_type, [0, 0])
                    a[0] += 1
                    if e.status == "completed":
                        a[1] += 1
                rows = [[k.replace("_", " ").title(), str(v[0]), str(v[1])]
                        for k, v in sorted(agg.items())]
                out.append(grid_table(["Event Type", "Scheduled", "Completed"], rows,
                                      [0.5, 0.25, 0.25]))
            else:
                out.append(Paragraph("No lifecycle events were recorded for this period.", body))
            return out

        def audit_trail():
            out = sec("On-Chain Audit Trail")
            out.append(Paragraph(
                "Each entry below was written to the on-chain audit log and mirrored in the "
                "operator's database. Sequence numbers correspond to on-chain ordering where "
                "available.", body))
            out.append(Spacer(1, 6))
            if audit_entries:
                rows = []
                for e in audit_entries[:40]:
                    seq = e.onchain_sequence if e.onchain_sequence is not None else "—"
                    rows.append([str(seq), _ts(e.onchain_timestamp or e.created_at),
                                 (e.agent or "—").title(),
                                 (e.action or "—").replace("_", " ").title()])
                out.append(grid_table(["Seq", "Timestamp", "Domain", "Action"], rows,
                                      [0.10, 0.34, 0.22, 0.34]))
                if len(audit_entries) > 40:
                    out += [Spacer(1, 4),
                            Paragraph(f"Showing 40 of {len(audit_entries)} audit records.", cell_s)]
            else:
                out.append(Paragraph("No audit records were found for this security.", body))
            return out

        def onchain():
            audit_addr = ""
            try:
                audit_addr = cfg.contract("audit_log") if cfg else ""
            except Exception:
                audit_addr = ""
            try:
                operator = adapter.operator_ref()
            except Exception:
                operator = "—"
            out = sec("On-Chain Verification")
            out.append(Paragraph(
                "The records in this report are independently verifiable on the public ledger. The "
                "contracts and authority below may be inspected on the network's block explorer.", body))
            out.append(Spacer(1, 6))
            out.append(kv_table([
                ("Token Contract", Paragraph(link(asset.token_id or "—", token_url), cell)),
                ("Audit Log Contract",
                 Paragraph(link(audit_addr or "—", explorer_addr(audit_addr)), cell)),
                ("Signing Authority (Operator)",
                 Paragraph(link(operator, explorer_addr(operator)), cell)),
                ("Network", network),
                ("Audit Topic / Log Ref", asset.topic_id or "—"),
            ]))
            return out

        def narrative_section():
            out = sec("Narrative Analysis")
            for para in (narrative or "").split("\n\n"):
                if para.strip():
                    out += [Paragraph(para.strip().replace("\n", "<br/>"), body), Spacer(1, 6)]
            return out

        def attestation():
            out = sec("Attestation & Authorised Signature")
            out.append(Paragraph(
                "The undersigned attests that, to the best of the operator's knowledge and based on "
                "the on-chain records and the operator's system of record, the factual information set "
                "out in this report is accurate as at the date of issue. This report describes "
                "technical controls and recorded data; it is not a legal opinion on the regulatory "
                "status of the security. The document carries the SHA-256 integrity fingerprint below; "
                "any alteration invalidates the fingerprint.", body))
            out.append(Spacer(1, 18))
            sig_left = [
                HRFlowable(width="80%", thickness=0.8, color=HexColor(INK), hAlign="LEFT", spaceAfter=3),
                Paragraph("AUTHORISED SIGNATORY", sig_lbl),
                Paragraph(f"For: &nbsp;{issuer}", cell_s),
                Paragraph("Name: &nbsp;__________________________", cell_s),
                Paragraph("Title: &nbsp;Compliance Officer / Issuer Representative", cell_s),
                Paragraph(f"Date: &nbsp;{gen:%d %B %Y}", cell_s),
            ]
            sig_right = Table(
                [[Paragraph("DIGITAL SIGNATURE / e-SEAL", sig_lbl)],
                 [Paragraph("Affix qualified e-signature here", cell_s)]],
                colWidths=[0.34 * W], rowHeights=[16, 46],
            )
            sig_right.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.8, HexColor(IRIS)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, HexColor(HAIRLINE)),
                ("BACKGROUND", (0, 0), (-1, -1), HexColor(PANEL)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]))
            sig = Table([[sig_left, sig_right]], colWidths=[0.58 * W, 0.42 * W])
            sig.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                     ("LEFTPADDING", (0, 0), (0, 0), 0)]))
            out += [
                sig, Spacer(1, 14),
                Paragraph("DOCUMENT INTEGRITY FINGERPRINT (SHA-256)", sig_lbl),
                Paragraph(f'<font face="Courier" size="8" color="#141420">{integrity}</font>', cell_s),
            ]
            return [KeepTogether(out)]

        # ── cover / document control (common) ──
        story = [
            Paragraph(f"REGULATORY FILING — {title.upper()}", kicker),
            Paragraph(title, h_title),
            Paragraph(f"{asset.name} ({asset.symbol}) &nbsp;·&nbsp; Reporting period {period}", h_sub),
            Spacer(1, 14),
            kv_table([
                ("Report Reference", report_no),
                ("Report Type", title),
                ("Reporting Period", period),
                ("Date of Issue", f"{gen:%d %B %Y, %H:%M UTC}"),
                ("Issuer of Record", issuer),
                ("Issuer Identity (on-chain)", asset.owner or "—"),
                ("Prepared By", "Laminaa Autonomous Agent (operator-attested)"),
                ("Settlement Network", network),
            ], panel=True),
        ]

        # §1 Executive Summary (tailored)
        story += sec("Executive Summary")
        if report_type == "investor_statement":
            summary = (
                f"This investor statement summarises the recorded position(s) in "
                f"<b>{asset.name} ({asset.symbol})</b> for the period <b>{period}</b>. The security is "
                f"a tokenized {asset.asset_type} settled on {network}. {len(holders)} holder "
                f"position(s) are on record; {dist_n} distribution(s) totalling "
                f"{dist_total:,.2f} USDC were recorded during the period. Figures reflect the "
                f"operator's system of record reconciled against on-chain balances.")
        elif report_type == "audit_summary":
            summary = (
                f"This audit summary describes the operation of automated controls over "
                f"<b>{asset.name} ({asset.symbol})</b> for the period <b>{period}</b>, drawn from "
                f"{len(audit_entries)} on-chain audit record(s). {completed} lifecycle event(s) "
                f"completed and {dist_n} distribution(s) were recorded. Control operation is assessed "
                f'as <b><font color="#{status_color:06X}">{status_txt}</font></b> '
                f"(a technical assessment, not a legal opinion).")
        else:
            summary = (
                f"This compliance report sets out the control and lifecycle status of "
                f"<b>{asset.name} ({asset.symbol})</b>, a tokenized {asset.asset_type} settled on "
                f"{network}, for the period <b>{period}</b>. The security has {len(holders)} "
                f"registered holder(s), of which {wl} are whitelisted following KYC/AML and OFAC "
                f"screening. Control operation is assessed as "
                f'<b><font color="#{status_color:06X}">{status_txt}</font></b> '
                f"(a technical assessment based on the operator's records, not a legal opinion).")
        story.append(Paragraph(summary, body))

        # type-specific body
        if report_type == "investor_statement":
            story += particulars()
            story += holdings()
            story += distributions_section()
            story += lifecycle()
            story += onchain()
        elif report_type == "audit_summary":
            story += particulars()
            story += framework()
            story += lifecycle()
            story += distributions_section()
            story += audit_trail()
            story += onchain()
        else:  # compliance
            story += particulars()
            story += framework()
            story += compliance_summary()
            story += lifecycle()
            story += distributions_section()
            story += onchain()

        story += narrative_section()
        story += attestation()

        doc.build(story, canvasmaker=NumberedCanvas)
        pdf_bytes = buf.getvalue()
        # Best-effort local cache; the DB copy is the durable source of truth.
        try:
            with open(filepath, "wb") as fh:
                fh.write(pdf_bytes)
        except OSError:
            pass
        return filepath, pdf_bytes
