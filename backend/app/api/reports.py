"""Report download API — serves generated PDF files."""
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# Reports are stored in backend/reports/
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"


@router.get("/reports/download/{filename}")
async def download_report(filename: str):
    """Serve a generated report file (PDF or MD).

    Files are served from the backend/reports/ directory.
    """
    # Security: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Report not found: {filename}")

    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {
        ".pdf": "application/pdf",
        ".md": "text/markdown; charset=utf-8",
        ".html": "text/html; charset=utf-8",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )
