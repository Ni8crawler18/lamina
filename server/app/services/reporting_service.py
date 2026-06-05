"""Reporting service — production-grade regulatory PDF reports.

Generates compliance / investor / audit reports formatted for regulatory
submission: letterhead, document-control block, numbered sections, the
compliance framework the protocol enforces, an on-chain verification section
with explorer links, and an attestation block with an authorised-signature
area and a SHA-256 document-integrity fingerprint.

Narrative prose comes from Claude when an API key is set, otherwise a
deterministic fallback. All wording is chain-neutral.
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


class ReportingError(Exception):
    pass


class ReportingService:
    def __init__(self, session):
        self.session = session
        self.assets = AssetRepository(session)
        self.holders = HolderRepository(session)
        self.events = EventRepository(session)
        self.reports = ReportRepository(session)
        self.audit = AuditService(session)

    async def generate_report(
        self, asset_id: int, period: str = "Q1 2026", report_type: str = "compliance"
    ) -> dict:
        asset = await self.assets.get(asset_id)
        if not asset:
            raise ReportingError("Asset not found")
        holders = await self.holders.list_for_asset(asset_id)
        events = await self.events.list_for_asset(asset_id)
        registry = get_registry()
        adapter = registry.adapter(asset.chain)
        try:
            cfg = registry.get_config(asset.chain)
        except Exception:
            cfg = None

        narrative = self._narrative(asset, holders, events, period, report_type, cfg)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filepath, content = self._render_pdf(
            asset, holders, events, narrative, period, report_type, adapter, cfg
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
        asset = await self.assets.get(report.asset_id)
        if not asset:
            raise ReportingError("Asset not found")
        holders = await self.holders.list_for_asset(report.asset_id)
        events = await self.events.list_for_asset(report.asset_id)
        registry = get_registry()
        adapter = registry.adapter(asset.chain)
        try:
            cfg = registry.get_config(asset.chain)
        except Exception:
            cfg = None
        narrative = self._fallback_narrative(
            asset, holders, events, report.period, report.report_type
        )
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filepath, content = self._render_pdf(
            asset, holders, events, narrative, report.period, report.report_type, adapter, cfg
        )
        report.content = content
        report.file_path = filepath
        await self.session.flush()
        return content

    # ── narrative ────────────────────────────────────────────────────────────
    def _narrative(self, asset, holders, events, period, report_type, cfg) -> str:
        settings = get_settings()
        if settings.anthropic_api_key:
            try:
                return self._claude_narrative(asset, holders, events, period, report_type, cfg)
            except Exception as e:
                logger.warning("Claude narrative failed, using fallback: %s", e)
        return self._fallback_narrative(asset, holders, events, period, report_type)

    def _claude_narrative(self, asset, holders, events, period, report_type, cfg) -> str:
        import anthropic

        whitelisted = sum(1 for h in holders if h.whitelisted)
        completed = sum(1 for e in events if e.status == "completed")
        network = cfg.name if cfg else asset.chain
        client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
        prompt = (
            f"Write the narrative analysis section of a regulatory "
            f"{report_type.replace('_', ' ')} for the reporting period {period}. "
            f"Security: {asset.name} ({asset.symbol}), a tokenized {asset.asset_type} settled "
            f"on {network}. NAV ${asset.nav:,.2f}, coupon {asset.coupon_rate * 100:.2f}% per annum, "
            f"jurisdiction {asset.jurisdiction}, eligible investors: {asset.investor_type}. "
            f"{whitelisted} of {len(holders)} holders are whitelisted following KYC/AML and OFAC "
            f"screening; {completed} lifecycle events executed. Every agent action is written to an "
            f"immutable on-chain audit log. Write 3 short, formal paragraphs in the measured tone of "
            f"a compliance filing. No markdown, no headings, no bullet points."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    def _fallback_narrative(self, asset, holders, events, period, report_type) -> str:
        whitelisted = sum(1 for h in holders if h.whitelisted)
        completed = sum(1 for e in events if e.status == "completed")
        return (
            f"During the reporting period {period}, {asset.name} ({asset.symbol}) maintained "
            f"compliance with applicable {asset.jurisdiction} regulatory requirements governing the "
            f"issuance and transfer of tokenized {asset.asset_type} instruments. Holdings remained "
            f"restricted to verified, whitelisted investors, and {whitelisted} of {len(holders)} "
            f"registered holders satisfied identity-verification and sanctions-screening controls.\n\n"
            f"The instrument carried a Net Asset Value of ${asset.nav:,.2f} and an annual coupon rate "
            f"of {asset.coupon_rate * 100:.2f}%. {completed} scheduled lifecycle events were executed during "
            f"the period, each subject to automated pre-transfer compliance validation.\n\n"
            f"Every state-changing action was recorded to an immutable on-chain audit log and mirrored "
            f"in the operator's system of record, providing an independently verifiable, tamper-evident "
            f"trail of all activity affecting the security."
        )

    # ── PDF ──────────────────────────────────────────────────────────────────
    def _render_pdf(
        self, asset, holders, events, narrative, period, report_type, adapter, cfg
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

        # Document-integrity fingerprint over the canonical content set.
        whitelisted = sum(1 for h in holders if h.whitelisted)
        kyc_ok = sum(1 for h in holders if h.kyc_status == "approved" or h.kyc_granted)
        screened = sum(1 for h in holders if (h.ofac_status or "pending") != "pending")
        cleared = sum(1 for h in holders if _clear(h.ofac_status))
        completed = sum(1 for e in events if e.status == "completed")
        fingerprint_src = json.dumps(
            {
                "report_no": report_no, "type": report_type, "period": period,
                "asset": asset.id, "name": asset.name, "symbol": asset.symbol,
                "token": asset.token_id, "chain": asset.chain, "nav": asset.nav,
                "holders": len(holders), "whitelisted": whitelisted, "kyc": kyc_ok,
                "ofac_cleared": cleared, "events": completed,
                "generated": gen.isoformat(), "narrative": narrative,
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
            "DocSub", fontName="Helvetica", fontSize=11, leading=15,
            textColor=HexColor(MUTED),
        )
        section = ParagraphStyle(
            "Section", fontName="Helvetica-Bold", fontSize=11.5, leading=14,
            textColor=HexColor(IRIS_DARK), spaceBefore=2, spaceAfter=4,
        )
        cell = ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, leading=12,
                              textColor=HexColor(INK))
        cell_b = ParagraphStyle("CellB", parent=cell, fontName="Helvetica-Bold")
        cell_s = ParagraphStyle("CellS", parent=cell, fontSize=8, textColor=HexColor(MUTED))
        sig_lbl = ParagraphStyle("SigLbl", fontName="Helvetica-Bold", fontSize=8,
                                 textColor=HexColor(MUTED), leading=11)

        def link(text, url):
            return f'<a href="{url}" color="#6D5AE6">{text}</a>' if url else text

        def explorer_addr(ref):
            try:
                return adapter.explorer_address(ref) if ref else ""
            except Exception:
                return ""

        def sec(n, label):
            return [
                Spacer(1, 12),
                Paragraph(f"{n}&nbsp;&nbsp;{label}", section),
                HRFlowable(width="100%", thickness=0.6, color=HexColor(HAIRLINE),
                           spaceBefore=1, spaceAfter=7),
            ]

        def kv_table(rows, panel=False):
            data = [[Paragraph(str(k), cell_b), v if hasattr(v, "build") or
                     isinstance(v, Paragraph) else Paragraph(str(v), cell)] for k, v in rows]
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
                    ("LINEBELOW", (0, 0), (-1, -2), 0.4, HexColor(HAIRLINE)),
                ]
            t.setStyle(TableStyle(style))
            return t

        # ── header / footer (drawn on every page) ──
        def diamond(c, cx, cy, w, h, color):
            c.setFillColor(HexColor(color))
            p = c.beginPath()
            p.moveTo(cx, cy + h); p.lineTo(cx + w, cy)
            p.lineTo(cx, cy - h); p.lineTo(cx - w, cy); p.close()
            c.drawPath(p, fill=1, stroke=0)

        def decorate(c, page_no, page_count):
            ph = A4[1]
            pw = A4[0]
            # logo
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
            # right: classification + report no
            rx = pw - 0.85 * inch
            c.setFillColor(HexColor(IRIS))
            c.setFont("Helvetica-Bold", 7)
            c.drawRightString(rx, ly + 2, "CONFIDENTIAL")
            c.setFillColor(HexColor(MUTED))
            c.setFont("Helvetica", 7)
            c.drawRightString(rx, ly - 8, report_no)
            # header rule
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
                         "Generated by the Laminaa autonomous agent. Informational compliance "
                         "record — not legal, tax, or investment advice.")
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

        # ── story ──
        network = f"{cfg.name} (chain ID {cfg.chain_id})" if cfg else asset.chain
        token_std = "ERC-3643 permissioned security token" if (cfg and cfg.family == "evm") \
            else "Permissioned security token"
        token_url = explorer_addr(asset.token_id)
        story = [
            Paragraph("REGULATORY FILING — TOKENIZED SECURITY", kicker),
            Paragraph(title, h_title),
            Paragraph(f"{asset.name} ({asset.symbol}) &nbsp;·&nbsp; Reporting period {period}", h_sub),
            Spacer(1, 14),
            kv_table([
                ("Report Reference", report_no),
                ("Report Type", title),
                ("Reporting Period", period),
                ("Date of Issue", f"{gen:%d %B %Y, %H:%M UTC}"),
                ("Issuer of Record", asset.owner or "Operator-managed"),
                ("Prepared By", "Laminaa Autonomous Agent (operator-attested)"),
                ("Jurisdiction", asset.jurisdiction),
                ("Settlement Network", network),
            ], panel=True),
        ]

        # §1 Executive Summary
        status_color = GREEN if cleared >= whitelisted and whitelisted == len(holders) else AMBER
        status_txt = "COMPLIANT" if status_color == GREEN else "REVIEW REQUIRED"
        story += sec("1.", "Executive Summary")
        story.append(Paragraph(
            f"This {title.lower()} sets out the compliance and lifecycle status of "
            f"<b>{asset.name} ({asset.symbol})</b>, a tokenized {asset.asset_type} issued under "
            f"{asset.jurisdiction} requirements and settled on {network}, for the period "
            f"<b>{period}</b>. As at the date of issue the security has {len(holders)} registered "
            f"holder(s), of which {whitelisted} are whitelisted for transfer following "
            f"KYC/AML and OFAC sanctions screening. The overall compliance posture is assessed as "
            f'<b><font color="#{status_color:06X}">{status_txt}</font></b>.', body))

        # §2 Security Particulars
        story += sec("2.", "Security Particulars")
        tok_cell = Paragraph(link(asset.token_id or "—", token_url), cell)
        story.append(kv_table([
            ("Legal Name", asset.name),
            ("Ticker Symbol", asset.symbol),
            ("Asset Class", asset.asset_type.replace("_", " ").title()),
            ("Token Standard", token_std),
            ("Token Contract", tok_cell),
            ("Settlement Network", network),
            ("Total Supply", f"{asset.total_supply:,} units"),
            ("Net Asset Value (NAV)", f"${asset.nav:,.2f}"),
            ("Coupon / Distribution Rate", f"{asset.coupon_rate * 100:.2f}% per annum"),
            ("Maturity Date", asset.maturity_date or "—"),
            ("Lifecycle Status", asset.status.title()),
            ("Eligible Investors", (asset.investor_type or "accredited").replace("_", " ").title()),
        ]))

        # §3 Regulatory Framework & Methodology
        story += sec("3.", "Regulatory Framework & Compliance Methodology")
        story.append(Paragraph(
            "The following controls are enforced programmatically by the protocol on every "
            "state-changing action affecting the security:", body))
        story.append(Spacer(1, 6))
        framework = [
            ("Token Standard", f"{token_std}; transfers are gated on-chain against an identity "
             "registry — only verified holders may hold or receive units."),
            ("Investor Onboarding", "KYC/AML identity verification is completed and recorded "
             "prior to any holder being whitelisted."),
            ("Sanctions Screening", "Holders are screened against the OFAC SDN list using fuzzy "
             "name matching (≈85% threshold) and exact wallet-address matching; the list is "
             "refreshed daily."),
            ("Transfer Restrictions", "Only whitelisted, KYC-approved, non-frozen wallets are "
             "permitted to transact; non-compliant transfers are rejected at the contract level."),
            ("Investor Eligibility", f"Holdings are restricted to "
             f"{(asset.investor_type or 'accredited')} investors in permitted jurisdictions."),
            ("Audit & Recordkeeping", "Every action is written to an immutable on-chain audit log "
             "and mirrored in the operator's system of record, producing a tamper-evident trail."),
        ]
        story.append(kv_table(framework))

        # §4 Investor Compliance Summary
        story += sec("4.", "Investor Compliance Summary")
        story.append(kv_table([
            ("Registered Holders", str(len(holders))),
            ("KYC/AML Approved", f"{kyc_ok} of {len(holders)}"),
            ("OFAC Screened", f"{screened} of {len(holders)}"),
            ("OFAC Cleared", f"{cleared} of {len(holders)}"),
            ("Whitelisted for Transfer", f"{whitelisted} of {len(holders)}"),
            ("Compliance Determination",
             Paragraph(f'<b><font color="#{status_color:06X}">{status_txt}</font></b>', cell)),
        ], panel=True))

        if holders:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Holder Register", cell_b))
            story.append(Spacer(1, 4))
            head = ["#", "Holder Account", "Name", "Units", "KYC", "OFAC", "Juris.", "WL"]
            rows = [[Paragraph(f"<b>{h}</b>", cell_s) for h in head]]
            for i, hd in enumerate(holders[:60], 1):
                rows.append([
                    Paragraph(str(i), cell_s),
                    Paragraph(_mask(hd.account_id), cell_s),
                    Paragraph(hd.name or "—", cell_s),
                    Paragraph(f"{hd.balance:,}", cell_s),
                    Paragraph((hd.kyc_status or "—").title(), cell_s),
                    Paragraph((hd.ofac_status or "—").title(), cell_s),
                    Paragraph(hd.jurisdiction or "—", cell_s),
                    Paragraph("Yes" if hd.whitelisted else "No", cell_s),
                ])
            cw = [0.04, 0.26, 0.18, 0.12, 0.12, 0.12, 0.08, 0.08]
            reg = Table(rows, colWidths=[c * W for c in cw], repeatRows=1)
            reg.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor(IRIS_DARK)),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor(0xFFFFFF)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor(0xFFFFFF), HexColor(PANEL)]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, HexColor(HAIRLINE)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(reg)
            if len(holders) > 60:
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"Showing first 60 of {len(holders)} holders.", cell_s))

        # §5 Lifecycle Activity
        story += sec("5.", "Lifecycle Activity")
        if events:
            by_type: dict[str, list[int]] = {}
            for e in events:
                t = by_type.setdefault(e.event_type, [0, 0])
                t[0] += 1
                if e.status == "completed":
                    t[1] += 1
            ev_rows = [[Paragraph("<b>Event Type</b>", cell_s),
                        Paragraph("<b>Scheduled</b>", cell_s),
                        Paragraph("<b>Completed</b>", cell_s)]]
            for et, (sched, done) in sorted(by_type.items()):
                ev_rows.append([
                    Paragraph(et.replace("_", " ").title(), cell_s),
                    Paragraph(str(sched), cell_s),
                    Paragraph(str(done), cell_s),
                ])
            et_tbl = Table(ev_rows, colWidths=[0.5 * W, 0.25 * W, 0.25 * W])
            et_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor(PANEL)),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, HexColor(HAIRLINE)),
                ("BOX", (0, 0), (-1, -1), 0.6, HexColor(HAIRLINE)),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(et_tbl)
        else:
            story.append(Paragraph("No lifecycle events were recorded for this period.", body))

        # §6 On-Chain Verification
        story += sec("6.", "On-Chain Verification")
        story.append(Paragraph(
            "The records in this report are independently verifiable on the public ledger. The "
            "contracts and authority below may be inspected on the network's block explorer.", body))
        story.append(Spacer(1, 6))
        audit_addr = ""
        try:
            audit_addr = cfg.contract("audit_log") if cfg else ""
        except Exception:
            audit_addr = ""
        try:
            operator = adapter.operator_ref()
        except Exception:
            operator = "—"
        story.append(kv_table([
            ("Token Contract", Paragraph(link(asset.token_id or "—", token_url), cell)),
            ("Audit Log Contract",
             Paragraph(link(audit_addr or "—", explorer_addr(audit_addr)), cell)),
            ("Signing Authority (Operator)",
             Paragraph(link(operator, explorer_addr(operator)), cell)),
            ("Network", network),
            ("Audit Topic / Log Ref", asset.topic_id or "—"),
        ]))

        # §7 Narrative Analysis
        story += sec("7.", "Narrative Analysis")
        for para in (narrative or "").split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip().replace("\n", "<br/>"), body))
                story.append(Spacer(1, 6))

        # §8 Attestation & Authorised Signature — kept together so the signature
        # block and the integrity fingerprint never split across a page break.
        sec8 = sec("8.", "Attestation & Authorised Signature")
        sec8.append(Paragraph(
            "The undersigned attests that, to the best of the operator's knowledge and based on the "
            "on-chain records and the operator's system of record, the information set out in this "
            "report is accurate and complete as at the date of issue. This document carries the "
            "SHA-256 integrity fingerprint below; any alteration invalidates the fingerprint.", body))
        sec8.append(Spacer(1, 18))

        line = HRFlowable(width="80%", thickness=0.8, color=HexColor(INK),
                          hAlign="LEFT", spaceAfter=3)
        sig_left = [
            line,
            Paragraph("AUTHORISED SIGNATORY", sig_lbl),
            Paragraph("Name: &nbsp;__________________________", cell_s),
            Paragraph("Title: &nbsp;Compliance Officer / Issuer Representative", cell_s),
            Paragraph(f"Date: &nbsp;{gen:%d %B %Y}", cell_s),
        ]
        sig_right_inner = Table(
            [[Paragraph("DIGITAL SIGNATURE / e-SEAL", sig_lbl)],
             [Paragraph("Affix qualified e-signature here", cell_s)]],
            colWidths=[0.34 * W], rowHeights=[16, 46],
        )
        sig_right_inner.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, HexColor(IRIS)),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, HexColor(HAIRLINE)),
            ("BACKGROUND", (0, 0), (-1, -1), HexColor(PANEL)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        sig = Table([[sig_left, sig_right_inner]], colWidths=[0.58 * W, 0.42 * W])
        sig.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (0, 0), 0)]))
        sec8 += [
            sig,
            Spacer(1, 14),
            Paragraph("DOCUMENT INTEGRITY FINGERPRINT (SHA-256)", sig_lbl),
            Paragraph(f'<font face="Courier" size="8" color="#141420">{integrity}</font>', cell_s),
        ]
        story.append(KeepTogether(sec8))

        doc.build(story, canvasmaker=NumberedCanvas)
        pdf_bytes = buf.getvalue()
        # Best-effort local cache; the DB copy is the durable source of truth.
        try:
            with open(filepath, "wb") as fh:
                fh.write(pdf_bytes)
        except OSError:
            pass
        return filepath, pdf_bytes
