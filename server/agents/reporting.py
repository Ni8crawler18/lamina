"""Reporting Agent — Generate compliance reports, investor statements, audit trails."""

import json
import logging
import os
import re
from datetime import datetime

from server.database import get_db
from server.hedera.consensus import get_topic_messages, log_agent_action
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
Every agent action was logged to Hedera Consensus Service (Topic: {asset.get('topic_id', 'N/A')}), providing immutable, tamper-proof records of all operations. These records can be independently verified on HashScan.

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
    """Generate a PDF report using Jinja2 HTML template + xhtml2pdf."""
    from jinja2 import Environment, FileSystemLoader
    from xhtml2pdf import pisa

    REPORT_TITLES = {
        "compliance": "Compliance Report",
        "investor_statement": "Investor Statement",
        "audit_summary": "Audit Summary Report",
    }
    REPORT_TYPE_LABELS = {
        "compliance": "Compliance",
        "investor_statement": "Investor Statement",
        "audit_summary": "Audit Summary",
    }

    title_text = REPORT_TITLES.get(report_type, "Report")
    filename = f"{report_type}_{asset['id']}_{period.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    # Get operator account dynamically
    try:
        from server.hedera.client import get_operator_account_id
        operator_id = str(get_operator_account_id())
    except Exception:
        operator_id = "N/A"

    # Prepare holder data for template
    template_holders = []
    for h in holders:
        template_holders.append({
            "account_id": h.get("account_id", "N/A"),
            "balance_formatted": f"{h.get('balance', 0):,}",
            "kyc_status": h.get("kyc_status", ""),
            "jurisdiction": h.get("jurisdiction", ""),
            "whitelisted": bool(h.get("whitelisted")),
        })

    # Parse narrative into paragraphs
    narrative_paragraphs = [p.strip() for p in narrative.split("\n\n") if p.strip()]

    whitelisted_count = sum(1 for h in holders if h.get("whitelisted"))

    # Render HTML from Jinja2 template
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "data", "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("report.html")

    html_content = template.render(
        title=f"{title_text} — {period}",
        report_type=report_type,
        report_type_label=REPORT_TYPE_LABELS.get(report_type, report_type),
        asset_name=asset.get("name", ""),
        asset_symbol=asset.get("symbol", ""),
        asset_status=asset.get("status", "active"),
        asset_type=asset.get("asset_type", "bond"),
        period=period,
        generated_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        token_id=asset.get("token_id", "N/A"),
        topic_id=asset.get("topic_id", "N/A"),
        jurisdiction=asset.get("jurisdiction", "US"),
        investor_type=asset.get("investor_type", "accredited"),
        total_supply=f"{asset.get('total_supply', 0):,}",
        nav=f"{asset.get('nav', 0):,.2f}",
        coupon_rate=f"{asset.get('coupon_rate', 0) * 100:.2f}",
        maturity_date=asset.get("maturity_date", "N/A"),
        total_holders=len(holders),
        whitelisted_holders=whitelisted_count,
        narrative_paragraphs=narrative_paragraphs,
        holders=template_holders,
        events=events,
        audit_entries=audit_entries,
        operator_id=operator_id,
    )

    # Convert HTML to PDF
    with open(filepath, "w+b") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

    if pisa_status.err:
        logger.error(f"xhtml2pdf errors: {pisa_status.err}")

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
