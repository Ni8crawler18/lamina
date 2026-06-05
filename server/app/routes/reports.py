"""Report endpoints — list, generate, download."""

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories.reports import ReportRepository
from app.services.reporting_service import ReportingError, ReportingService

router = APIRouter(tags=["reports"])


@router.get("/api/assets/{asset_id}/reports")
async def list_reports(asset_id: int, session: AsyncSession = Depends(get_session)):
    rows = await ReportRepository(session).list_for_asset(asset_id)
    return [
        {"id": r.id, "report_type": r.report_type, "period": r.period,
         "generated_at": r.generated_at, "download_url": f"/api/reports/{r.id}/download"}
        for r in rows
    ]


@router.delete("/api/reports/{report_id}")
async def delete_report(report_id: int, session: AsyncSession = Depends(get_session)):
    if not await ReportRepository(session).delete(report_id):
        raise HTTPException(404, "Report not found")
    return {"deleted": report_id}


@router.post("/api/assets/{asset_id}/reports")
async def generate_report(
    asset_id: int, report_type: str = "compliance", period: str = "Q1 2026",
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ReportingService(session).generate_report(asset_id, period, report_type)
    except ReportingError as e:
        raise HTTPException(404, str(e))


@router.get("/api/reports/{report_id}/download")
async def download_report(report_id: int, session: AsyncSession = Depends(get_session)):
    report = await ReportRepository(session).get(report_id)
    if not report:
        raise HTTPException(404, "Report not found")

    # Prefer the durable DB copy; fall back to the on-disk cache; otherwise
    # re-render on the fly (handles rows created before PDFs were stored in the
    # DB, whose files were wiped by an ephemeral-disk redeploy).
    content = report.content
    if not content and report.file_path and os.path.exists(report.file_path):
        with open(report.file_path, "rb") as fh:
            content = fh.read()
    if not content:
        try:
            content = await ReportingService(session).rerender_report(report)
        except ReportingError:
            raise HTTPException(404, "Report not found")

    filename = os.path.basename(report.file_path) if report.file_path else f"report-{report.id}.pdf"
    return Response(
        content, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
