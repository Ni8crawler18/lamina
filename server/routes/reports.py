"""Report generation and download routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.database import get_db

router = APIRouter(tags=["reports"])


@router.get("/api/assets/{asset_id}/reports")
async def list_reports(asset_id: int):
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM reports WHERE asset_id = ? ORDER BY generated_at DESC", (asset_id,)
        )
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.post("/api/assets/{asset_id}/reports")
async def generate_report(asset_id: int, report_type: str = "compliance", period: str = "Q1 2026"):
    from server.agents.reporting import generate_report
    return await generate_report(asset_id, period, report_type=report_type)


@router.get("/api/reports/{report_id}/download")
async def download_report(report_id: int):
    db = await get_db()
    try:
        row = await db.execute_fetchone("SELECT * FROM reports WHERE id = ?", (report_id,))
        if not row or not row["file_path"]:
            raise HTTPException(status_code=404, detail="Report not found")
        return FileResponse(
            row["file_path"],
            media_type="application/pdf",
            filename=f"lamina_report_{report_id}.pdf",
        )
    finally:
        await db.close()
