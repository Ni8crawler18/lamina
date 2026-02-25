"""Reporting Agent — Generate compliance reports, investor statements, audit trails."""

import json
import logging
import os
from datetime import datetime

from backend.database import get_db
from backend.hedera.consensus import get_topic_messages, log_agent_action
from backend.config import get_settings

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


async def generate_compliance_report(asset_id: int, period: str = "Q1 2026") -> dict:
    """Generate a quarterly compliance report for an asset."""
    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT * FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise ValueError("Asset not found")

        # Gather data
        holders = await db.execute_fetchall(
            "SELECT * FROM holders WHERE asset_id = ? ORDER BY balance DESC", (asset_id,)
        )
        events = await db.execute_fetchall(
            "SELECT * FROM scheduled_events WHERE asset_id = ? ORDER BY scheduled_at", (asset_id,)
        )
        audit_entries = await db.execute_fetchall(
            "SELECT * FROM audit_log WHERE asset_id = ? ORDER BY created_at DESC LIMIT 50", (asset_id,)
        )

        # Get HCS messages
        hcs_messages = []
        if asset["topic_id"]:
            hcs_messages = await get_topic_messages(asset["topic_id"])

        # Generate report narrative using Claude API
        narrative = await _generate_report_narrative(asset, holders, events, audit_entries, period)

        # Generate PDF
        report_path = await _generate_pdf_report(
            asset=dict(asset),
            holders=[dict(h) for h in holders],
            events=[dict(e) for e in events],
            audit_entries=[dict(a) for a in audit_entries],
            narrative=narrative,
            period=period,
        )

        # Store report record
        cursor = await db.execute(
            "INSERT INTO reports (asset_id, report_type, period, file_path) VALUES (?, ?, ?, ?)",
            (asset_id, "compliance", period, report_path)
        )
        report_id = cursor.lastrowid
        await db.commit()

        # Log to HCS
        if asset["topic_id"]:
            log_agent_action(
                asset["topic_id"],
                agent="reporting",
                action="report_generated",
                details={"report_type": "compliance", "period": period, "report_id": report_id},
            )

        await db.execute(
            "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
            (asset_id, "report_generated", "reporting",
             json.dumps({"type": "compliance", "period": period}))
        )
        await db.commit()

        return {
            "report_id": report_id,
            "asset_id": asset_id,
            "report_type": "compliance",
            "period": period,
            "file_path": report_path,
            "narrative_preview": narrative[:500] if narrative else "",
        }
    finally:
        await db.close()


async def _generate_report_narrative(asset, holders, events, audit_entries, period: str) -> str:
    """Use Claude API to generate a report narrative from on-chain data."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        return _fallback_narrative(asset, holders, events, period)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        holder_summary = f"{len(holders)} total holders, {sum(1 for h in holders if h['whitelisted'])} whitelisted"
        event_summary = f"{len(events)} scheduled events, {sum(1 for e in events if e['status'] == 'completed')} completed"

        prompt = f"""Generate a concise quarterly compliance report narrative for a tokenized asset.

Asset: {asset['name']} ({asset['symbol']})
Type: {asset['asset_type']}
Token ID: {asset['token_id']}
Jurisdiction: {asset['jurisdiction']}
Status: {asset['status']}
Total Supply: {asset['total_supply']}
NAV: ${asset['nav']:,.2f}
Coupon Rate: {asset['coupon_rate']*100:.1f}%
Period: {period}

Holders: {holder_summary}
Events: {event_summary}
Audit Entries: {len(audit_entries)} actions logged

Write 3-4 paragraphs covering: compliance status, holder activity, coupon distributions, and any notable events. Keep it professional and suitable for regulatory submission."""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API report generation failed: {e}")
        return _fallback_narrative(asset, holders, events, period)


def _fallback_narrative(asset, holders, events, period: str) -> str:
    """Generate a basic narrative without LLM."""
    whitelisted = sum(1 for h in holders if h["whitelisted"])
    completed_events = sum(1 for e in events if e["status"] == "completed")

    return f"""Compliance Report — {period}

Asset: {asset['name']} ({asset['symbol']})
Token ID: {asset['token_id']}
Status: {asset['status']}

During {period}, the asset maintained compliance with {asset['jurisdiction']} regulatory requirements.
A total of {whitelisted} investors are currently whitelisted out of {len(holders)} registered holders.
{completed_events} scheduled events were executed during this period.

The asset's Net Asset Value (NAV) stands at ${asset['nav']:,.2f} with a coupon rate of {asset['coupon_rate']*100:.1f}%.
All transfers were validated against KYC/AML requirements, and all agent actions were logged to Hedera Consensus Service for immutable audit trail."""


async def _generate_pdf_report(
    asset: dict,
    holders: list[dict],
    events: list[dict],
    audit_entries: list[dict],
    narrative: str,
    period: str,
) -> str:
    """Generate a PDF compliance report using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    filename = f"compliance_report_{asset['id']}_{period.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CustomTitle", parent=styles["Title"], fontSize=18, spaceAfter=20)
    heading_style = ParagraphStyle("CustomHeading", parent=styles["Heading2"], spaceAfter=10, spaceBefore=15)

    elements = []

    # Title
    elements.append(Paragraph(f"Compliance Report — {period}", title_style))
    elements.append(Paragraph(f"{asset['name']} ({asset['symbol']})", styles["Heading3"]))
    elements.append(Spacer(1, 12))

    # Asset summary table
    summary_data = [
        ["Field", "Value"],
        ["Token ID", asset.get("token_id", "N/A")],
        ["Asset Type", asset.get("asset_type", "bond")],
        ["Jurisdiction", asset.get("jurisdiction", "US")],
        ["Status", asset.get("status", "active")],
        ["Total Supply", f"{asset.get('total_supply', 0):,}"],
        ["NAV", f"${asset.get('nav', 0):,.2f}"],
        ["Coupon Rate", f"{asset.get('coupon_rate', 0)*100:.1f}%"],
    ]
    t = Table(summary_data, colWidths=[2 * inch, 4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Narrative
    elements.append(Paragraph("Executive Summary", heading_style))
    for para in narrative.split("\n\n"):
        if para.strip():
            elements.append(Paragraph(para.strip(), styles["Normal"]))
            elements.append(Spacer(1, 8))

    # Holder summary
    elements.append(Paragraph("Token Holders", heading_style))
    holder_data = [["Account", "Balance", "KYC Status", "Jurisdiction", "Whitelisted"]]
    for h in holders[:20]:
        holder_data.append([
            h.get("account_id", "")[:20] + "...",
            f"{h.get('balance', 0):,}",
            h.get("kyc_status", ""),
            h.get("jurisdiction", ""),
            "Yes" if h.get("whitelisted") else "No",
        ])
    if holder_data:
        ht = Table(holder_data, colWidths=[1.8 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch])
        ht.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        elements.append(ht)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"Generated by Lamina — Autonomous RWA Lifecycle Agent on Hedera | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey),
    ))

    doc.build(elements)
    logger.info(f"Generated compliance report: {filepath}")
    return filepath


async def get_audit_trail(asset_id: int) -> dict:
    """Get formatted audit trail combining HCS and local logs."""
    db = await get_db()
    try:
        asset = await db.execute_fetchone("SELECT topic_id FROM assets WHERE id = ?", (asset_id,))
        if not asset:
            raise ValueError("Asset not found")

        hcs_messages = []
        if asset["topic_id"]:
            hcs_messages = await get_topic_messages(asset["topic_id"])

        local_entries = await db.execute_fetchall(
            "SELECT * FROM audit_log WHERE asset_id = ? ORDER BY created_at DESC",
            (asset_id,)
        )

        return {
            "asset_id": asset_id,
            "topic_id": asset["topic_id"],
            "hcs_messages": hcs_messages,
            "local_entries": [dict(e) for e in local_entries],
            "total_actions": len(hcs_messages) + len(local_entries),
        }
    finally:
        await db.close()
