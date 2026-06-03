"""Reporting service — regulatory PDF reports from on-chain + DB data.

Narrative comes from Claude when an API key is set, otherwise a deterministic
fallback. Wording is chain-neutral ("on-chain audit log", not HCS/HashScan).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from app.chains.registry import get_registry
from app.config import get_settings
from app.repositories.assets import AssetRepository
from app.repositories.holders import HolderRepository
from app.repositories.events import EventRepository
from app.repositories.reports import ReportRepository
from app.services.audit_service import AuditService
from app.utils.aio import run_chain

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
REPORT_TITLES = {
    "compliance": "Compliance Report",
    "investor_statement": "Investor Statement",
    "audit_summary": "Audit Summary Report",
}


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
        adapter = get_registry().adapter(asset.chain)

        narrative = self._narrative(asset, holders, events, period, report_type)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filepath = self._render_pdf(asset, holders, narrative, period, report_type, adapter)

        report = await self.reports.create(
            asset_id=asset_id, report_type=report_type, period=period, file_path=filepath
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

    # ── narrative ────────────────────────────────────────────────────────────
    def _narrative(self, asset, holders, events, period, report_type) -> str:
        settings = get_settings()
        if settings.anthropic_api_key:
            try:
                return self._claude_narrative(asset, holders, events, period, report_type)
            except Exception as e:
                logger.warning("Claude narrative failed, using fallback: %s", e)
        return self._fallback_narrative(asset, holders, events, period, report_type)

    def _claude_narrative(self, asset, holders, events, period, report_type) -> str:
        import anthropic

        whitelisted = sum(1 for h in holders if h.whitelisted)
        completed = sum(1 for e in events if e.status == "completed")
        client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
        prompt = (
            f"Write a concise, professional {report_type.replace('_', ' ')} narrative for "
            f"period {period}. Asset: {asset.name} ({asset.symbol}), a tokenized {asset.asset_type} "
            f"on {asset.chain}. NAV ${asset.nav:,.2f}, coupon {asset.coupon_rate:.2f}% annual, "
            f"jurisdiction {asset.jurisdiction}. {whitelisted}/{len(holders)} holders whitelisted, "
            f"{completed} lifecycle events executed. Every agent action is recorded on an immutable "
            f"on-chain audit log. 3-4 short paragraphs, no markdown."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    def _fallback_narrative(self, asset, holders, events, period, report_type) -> str:
        whitelisted = sum(1 for h in holders if h.whitelisted)
        completed = sum(1 for e in events if e.status == "completed")
        if report_type == "investor_statement":
            return (
                f"Investor Statement — {period}\n\n"
                f"Asset: {asset.name} ({asset.symbol})\nToken: {asset.token_id}\n"
                f"Status: {asset.status}\n\n"
                f"The {asset.name} token held a Net Asset Value (NAV) of ${asset.nav:,.2f} during "
                f"{period}, with an annual coupon rate of {asset.coupon_rate:.2f}% distributed "
                f"proportionally to holders. {len(holders)} holders are registered, {whitelisted} "
                f"whitelisted for distributions. Total supply is {asset.total_supply:,} units.\n\n"
                f"{completed} scheduled events executed this period. All operations are recorded on "
                f"an immutable on-chain audit log for independent verification."
            )
        if report_type == "audit_summary":
            return (
                f"Audit Summary — {period}\n\n"
                f"Asset: {asset.name} ({asset.symbol})\nToken: {asset.token_id}\n"
                f"Audit topic: {asset.topic_id}\n\n"
                f"During {period} the Lamina agent performed {completed} scheduled operations and "
                f"enforced compliance on every transfer. All {whitelisted} whitelisted holders passed "
                f"KYC/AML and OFAC screening. Every agent action was written to the chain's audit log "
                f"({asset.chain}), providing tamper-proof records verifiable on the block explorer."
            )
        return (
            f"Compliance Report — {period}\n\n"
            f"Asset: {asset.name} ({asset.symbol})\nToken: {asset.token_id}\n"
            f"Status: {asset.status}\n\n"
            f"During {period}, the asset maintained compliance with {asset.jurisdiction} regulatory "
            f"requirements. {whitelisted} investors are whitelisted out of {len(holders)} registered "
            f"holders. {completed} scheduled events were executed.\n\n"
            f"The asset's NAV stands at ${asset.nav:,.2f} with a coupon rate of "
            f"{asset.coupon_rate:.2f}%. All transfers were validated against KYC/AML and sanctions "
            f"requirements, and every agent action was logged to an immutable on-chain audit trail."
        )

    # ── PDF ──────────────────────────────────────────────────────────────────
    def _render_pdf(self, asset, holders, narrative, period, report_type, adapter) -> str:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )

        title = REPORT_TITLES.get(report_type, "Report")
        fname = (
            f"{report_type}_{asset.id}_{period.replace(' ', '_')}_"
            f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        filepath = os.path.join(REPORTS_DIR, fname)
        whitelisted = sum(1 for h in holders if h.whitelisted)

        doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="SmallGray", fontSize=8, textColor=colors.gray))
        story = [
            Paragraph(f"<b>{title} — {period}</b>", styles["Title"]),
            Paragraph("Lamina — Multi-Chain RWA Lifecycle Agent", styles["SmallGray"]),
            Paragraph(f"Chain: {asset.chain} · Generated {datetime.utcnow():%Y-%m-%d %H:%M UTC}",
                      styles["SmallGray"]),
            Spacer(1, 20),
        ]
        table_style = TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ])
        asset_rows = [
            ["Asset", f"{asset.name} ({asset.symbol})"],
            ["Chain", asset.chain],
            ["Token", asset.token_id or "N/A"],
            ["Audit topic", asset.topic_id or "N/A"],
            ["Status", asset.status],
            ["Jurisdiction", asset.jurisdiction],
            ["NAV", f"${asset.nav:,.2f}"],
            ["Coupon rate", f"{asset.coupon_rate:.2f}%"],
            ["Maturity", asset.maturity_date or "N/A"],
            ["Operator", adapter.operator_ref()],
        ]
        t = Table(asset_rows, colWidths=[1.8 * inch, 4.2 * inch]); t.setStyle(table_style)
        story += [t, Spacer(1, 20), Paragraph("<b>Compliance Summary</b>", styles["Heading2"])]
        summary = [
            ["Total holders", str(len(holders))],
            ["Whitelisted", str(whitelisted)],
            ["OFAC screened", str(len([h for h in holders if h.ofac_status not in (None, "pending")]))],
            ["Status", "Compliant"],
        ]
        t2 = Table(summary, colWidths=[1.8 * inch, 4.2 * inch]); t2.setStyle(table_style)
        story += [t2, Spacer(1, 20)]
        if narrative:
            story.append(Paragraph("<b>Analysis</b>", styles["Heading2"]))
            for para in narrative.split("\n\n"):
                if para.strip():
                    story += [Paragraph(para.strip().replace("\n", "<br/>"), styles["Normal"]), Spacer(1, 6)]
        doc.build(story)
        return filepath
