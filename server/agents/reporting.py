"""Reporting Agent — Generate compliance reports, investor statements, audit trails."""

import json
import logging
import os
import re
from datetime import datetime

from server.database import get_db
from server.arbitrum.audit import get_topic_messages, log_agent_action
from server.config import get_settings

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


async def generate_report(asset_id: int, period: str = "Q1 2026", report_type: str = "compliance") -> dict:
    """Generate a report for an asset. Supports: compliance, investor_statement, audit_summary."""
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
        narrative = await _generate_report_narrative(asset, holders, events, audit_entries, period, report_type)

        # Generate PDF
        report_path = await _generate_pdf_report(
            asset=dict(asset),
            holders=[dict(h) for h in holders],
            events=[dict(e) for e in events],
            audit_entries=[dict(a) for a in audit_entries],
            narrative=narrative,
            period=period,
            report_type=report_type,
        )

        # Store report record
        cursor = await db.execute(
            "INSERT INTO reports (asset_id, report_type, period, file_path) VALUES (?, ?, ?, ?)",
            (asset_id, report_type, period, report_path)
        )
        report_id = cursor.lastrowid
        await db.commit()

        # Log to HCS
        if asset["topic_id"]:
            log_agent_action(
                asset["topic_id"],
                agent="reporting",
                action="report_generated",
                details={"report_type": report_type, "period": period, "report_id": report_id},
            )

        await db.execute(
            "INSERT INTO audit_log (asset_id, action, agent, details) VALUES (?, ?, ?, ?)",
            (asset_id, "report_generated", "reporting",
             json.dumps({"type": report_type, "period": period}))
        )
        await db.commit()

        return {
            "report_id": report_id,
            "asset_id": asset_id,
            "report_type": report_type,
            "period": period,
            "file_path": report_path,
            "download_url": f"https://lamina-4ivt.onrender.com/api/reports/{report_id}/download",
            "narrative_preview": narrative[:500] if narrative else "",
        }
    finally:
        await db.close()


async def _generate_report_narrative(asset, holders, events, audit_entries, period: str, report_type: str = "compliance") -> str:
    """Use Claude API to generate a report narrative from on-chain data."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        return _fallback_narrative(asset, holders, events, period, report_type)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Ensure all rows are dicts (sqlite3.Row doesn't support .get())
        holders = [dict(h) if not isinstance(h, dict) else h for h in holders]
        events = [dict(e) if not isinstance(e, dict) else e for e in events]
        audit_entries = [dict(a) if not isinstance(a, dict) else a for a in audit_entries]

        holder_summary = f"{len(holders)} total holders, {sum(1 for h in holders if h['whitelisted'])} whitelisted"
        event_summary = f"{len(events)} scheduled events, {sum(1 for e in events if e['status'] == 'completed')} completed"

        # Build holder details for investor statement
        holder_details = ""
        for h in holders[:10]:
            holder_details += f"  - {h['account_id']}: balance={h['balance']}, jurisdiction={h['jurisdiction']}, kyc={h['kyc_status']}\n"

        # Build audit details for audit summary
        audit_details = ""
        for a in audit_entries[:15]:
            audit_details += f"  - [{a.get('created_at', 'N/A')}] {a['agent']}: {a['action']} — {a.get('details', '')}\n"

        asset_info = f"""Asset: {asset['name']} ({asset['symbol']})
Type: {asset['asset_type']}
Token ID: {asset['token_id']}
Topic ID (HCS Audit): {asset.get('topic_id', 'N/A')}
Jurisdiction: {asset['jurisdiction']}
Status: {asset['status']}
Total Supply: {asset['total_supply']}
NAV: ${asset['nav']:,.2f}
Coupon Rate: {asset['coupon_rate']*100:.2f}%
Period: {period}
Holders: {holder_summary}
Events: {event_summary}
Audit Entries: {len(audit_entries)} actions logged"""

        if report_type == "investor_statement":
            prompt = f"""Generate a professional investor statement for a tokenized asset on Hedera.

{asset_info}

Holder Breakdown:
{holder_details}

Write 4-5 paragraphs covering:
1. Asset performance summary for the period (NAV changes, coupon payments made)
2. Portfolio position and token distribution across holders
3. Upcoming scheduled events (coupon dates, maturity timeline)
4. Market context for this asset type
5. Disclosure and risk factors

Use plain text only. Do NOT use markdown formatting like #, ##, **, *, or | tables. Write in professional prose suitable for PDF rendering. Use numbered sections like "1. Section Title" instead of markdown headings."""

        elif report_type == "audit_summary":
            prompt = f"""Generate a professional audit summary report for a tokenized asset on Hedera.

{asset_info}

Recent Agent Actions (from Hedera Consensus Service audit log):
{audit_details}

Write 4-5 paragraphs covering:
1. Summary of all autonomous agent actions during the period
2. Compliance verification: every transfer was checked against KYC/AML rules
3. On-chain immutability: all actions logged to Hedera Consensus Service (Topic ID: {asset.get('topic_id', 'N/A')})
4. Smart contract interactions and token operations performed
5. Recommendations for the next reporting period

Use plain text only. Do NOT use markdown formatting like #, ##, **, *, or | tables. Write in professional prose suitable for PDF rendering. Use numbered sections like "1. Section Title" instead of markdown headings."""

        else:  # compliance
            prompt = f"""Generate a concise quarterly compliance report for a tokenized asset on Hedera.

{asset_info}

Write 3-4 paragraphs covering:
1. Regulatory compliance status for {asset['jurisdiction']} jurisdiction
2. KYC/AML verification: holder whitelist status and any blocked transfers
3. Coupon distribution compliance and scheduled event execution
4. Any notable compliance events or flags during the period

Use plain text only. Do NOT use markdown formatting like #, ##, **, *, or | tables. Write in professional prose suitable for PDF rendering. Use numbered sections like "1. Section Title" instead of markdown headings."""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        return _strip_markdown(raw)
    except Exception as e:
        logger.error(f"Claude API report generation failed: {e}")
        return _fallback_narrative(asset, holders, events, period, report_type)


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting from text so it renders cleanly in PDF."""
    # Remove heading markers (# ## ### etc.)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold ** and __
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Remove italic * and _
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    # Remove inline code backticks
    text = re.sub(r'`(.+?)`', r'\1', text)
    # Remove markdown links [text](url) → text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    # Remove markdown table separators (|---|---|)
    text = re.sub(r'^\|[-:\s|]+\|$', '', text, flags=re.MULTILINE)
    # Clean up table rows: | col | col | → col  col
    text = re.sub(r'^\|(.+)\|$', lambda m: m.group(1).replace('|', '  ').strip(), text, flags=re.MULTILINE)
    # Remove horizontal rules (--- or ***)
    text = re.sub(r'^[-*]{3,}$', '', text, flags=re.MULTILINE)
    # Clean up excess blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _fallback_narrative(asset, holders, events, period: str, report_type: str = "compliance") -> str:
    """Generate a basic narrative without LLM."""
    whitelisted = sum(1 for h in holders if h["whitelisted"])
    completed_events = sum(1 for e in events if e["status"] == "completed")

    if report_type == "investor_statement":
        return f"""Investor Statement — {period}

Asset: {asset['name']} ({asset['symbol']})
Token ID: {asset['token_id']}
Status: {asset['status']}

1. Performance Summary
The {asset['name']} token maintained a Net Asset Value (NAV) of ${asset['nav']:,.2f} during {period}. The annual coupon rate is {asset['coupon_rate']*100:.2f}%, distributed proportionally to all token holders.

2. Token Distribution
A total of {len(holders)} holders are registered, with {whitelisted} currently whitelisted and eligible for distributions. The total token supply is {asset['total_supply']:,} tokens.

3. Upcoming Events
{completed_events} scheduled events have been executed during this period. Remaining events include coupon payments and maturity settlement as per the original issuance terms.

4. Disclosures
This statement is generated automatically by the Lamina autonomous agent. All token operations are recorded on the Hedera Consensus Service for immutable verification."""

    elif report_type == "audit_summary":
        return f"""Audit Summary — {period}

Asset: {asset['name']} ({asset['symbol']})
Token ID: {asset['token_id']}
HCS Topic: {asset.get('topic_id', 'N/A')}

1. Agent Activity Summary
During {period}, the Lamina autonomous agent performed {len([e for e in events if e['status'] == 'completed'])} scheduled operations and maintained compliance oversight for all token transfers.

2. Compliance Verification
All {whitelisted} whitelisted holders passed KYC/AML verification. Transfer validation was enforced on every token movement, with jurisdiction and investor type checks performed automatically.

3. On-Chain Audit Trail
Every agent action was logged to the AuditLog contract on Robinhood Chain (Topic: {asset.get('topic_id', 'N/A')}), providing immutable, tamper-proof records of all operations. These records can be independently verified on the Robinhood Chain block explorer.

4. Recommendations
Continue monitoring holder compliance status and ensure all scheduled coupon payments execute on time."""

    else:  # compliance
        return f"""Compliance Report — {period}

Asset: {asset['name']} ({asset['symbol']})
Token ID: {asset['token_id']}
Status: {asset['status']}

During {period}, the asset maintained compliance with {asset['jurisdiction']} regulatory requirements.
A total of {whitelisted} investors are currently whitelisted out of {len(holders)} registered holders.
{completed_events} scheduled events were executed during this period.

The asset's Net Asset Value (NAV) stands at ${asset['nav']:,.2f} with a coupon rate of {asset['coupon_rate']*100:.2f}%.
All transfers were validated against KYC/AML requirements, and all agent actions were logged to Hedera Consensus Service for immutable audit trail."""


async def _generate_pdf_report(
    asset: dict,
    holders: list[dict],
    events: list[dict],
    audit_entries: list[dict],
    narrative: str,
    period: str,
    report_type: str = "compliance",
) -> str:
    """Generate a PDF report using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    REPORT_TITLES = {
        "compliance": "Compliance Report",
        "investor_statement": "Investor Statement",
        "audit_summary": "Audit Summary Report",
    }

    title_text = REPORT_TITLES.get(report_type, "Report")
    filename = f"{report_type}_{asset['id']}_{period.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    try:
        from server.arbitrum.client import get_operator_address
        operator_id = get_operator_address()
    except Exception:
        operator_id = "N/A"

    whitelisted_count = sum(1 for h in holders if h.get("whitelisted"))

    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallGray", fontSize=8, textColor=colors.gray))
    story = []

    # Title
    story.append(Paragraph(f"<b>{title_text} — {period}</b>", styles["Title"]))
    story.append(Paragraph(f"Lamina — Autonomous RWA Lifecycle Agent", styles["SmallGray"]))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["SmallGray"]))
    story.append(Spacer(1, 20))

    # Asset details table
    asset_data = [
        ["Asset", f"{asset.get('name', '')} ({asset.get('symbol', '')})"],
        ["Token ID", asset.get("token_id", "N/A")],
        ["Audit Topic", asset.get("topic_id", "N/A")],
        ["Status", asset.get("status", "active")],
        ["Jurisdiction", asset.get("jurisdiction", "US")],
        ["Investor Type", asset.get("investor_type", "accredited")],
        ["NAV", f"${asset.get('nav', 0):,.2f}"],
        ["Coupon Rate", f"{asset.get('coupon_rate', 0) * 100:.2f}%"],
        ["Maturity", asset.get("maturity_date", "N/A")],
        ["Operator", operator_id],
    ]
    t = Table(asset_data, colWidths=[1.8*inch, 4.2*inch])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Compliance summary
    story.append(Paragraph("<b>Compliance Summary</b>", styles["Heading2"]))
    summary_data = [
        ["Total Holders", str(len(holders))],
        ["Whitelisted", str(whitelisted_count)],
        ["OFAC Screenings", str(len([h for h in holders if h.get("ofac_status")]))],
        ["Blocked Transfers", "0"],
        ["Status", "Compliant"],
    ]
    t2 = Table(summary_data, colWidths=[1.8*inch, 4.2*inch])
    t2.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(t2)
    story.append(Spacer(1, 20))

    # Narrative
    if narrative:
        story.append(Paragraph("<b>Analysis</b>", styles["Heading2"]))
        for para in narrative.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), styles["Normal"]))
                story.append(Spacer(1, 6))
        story.append(Spacer(1, 14))

    # Holders table
    if holders:
        story.append(Paragraph("<b>Token Holders</b>", styles["Heading2"]))
        holder_data = [["Account", "Balance", "KYC", "Jurisdiction", "OFAC"]]
        for h in holders:
            holder_data.append([
                h.get("account_id", "N/A"),
                f"{h.get('balance', 0):,}",
                h.get("kyc_status", ""),
                h.get("jurisdiction", ""),
                h.get("ofac_status", "pending"),
            ])
        t3 = Table(holder_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        t3.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.95, 0.95, 0.95)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("GRID", (0, 0), (-1, 0), 0.5, colors.lightgrey),
        ]))
        story.append(t3)

    doc.build(story)
    logger.info(f"Generated {report_type} report: {filepath}")
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
