from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HighCourtPDFResolverService:
    def __init__(self) -> None:
        self.root = Path(settings.HC_MOUNT_ROOT)

    def _clean_batch_no(self, batch_no: str | int) -> str:
        value = str(batch_no).strip()
        value = value.replace(",", "")
        value = value.replace(" ", "")
        return value

    def resolve_pdf(self, batch_no: str | int) -> Optional[Path]:
        batch = self._clean_batch_no(batch_no)
        if not batch:
            logger.error("[HC_IMPORT] batch_no=%s resolved_path=<empty> exists=false pdf_count=0 reason=empty_batch_no", batch_no)
            return None

        base_path = self.root / batch
        logger.info("[HC_IMPORT] batch_no=%s folder_path=%s", batch, base_path)

        if not base_path.exists():
            logger.error(
                "[HC_IMPORT] batch_no=%s resolved_path=%s exists=false pdf_count=0 reason=path_not_found",
                batch,
                base_path,
            )
            return None

        if not base_path.is_dir():
            logger.error(
                "[HC_IMPORT] batch_no=%s resolved_path=%s exists=true pdf_count=0 reason=path_not_directory",
                batch,
                base_path,
            )
            return None

        try:
            all_files = list(base_path.iterdir())
        except Exception:
            logger.exception(
                "[HC_IMPORT] batch_no=%s resolved_path=%s reason=directory_read_failed",
                batch,
                base_path,
            )
            return None

        total_files = len(all_files)
        pdfs = [path for path in all_files if path.is_file() and path.suffix.lower() == ".pdf"]

        if not pdfs and settings.HC_PDF_RESOLVE_RECURSIVE:
            max_depth = max(1, int(settings.HC_PDF_RESOLVE_MAX_DEPTH or 3))
            try:
                pdfs = [
                    path
                    for path in base_path.rglob("*.pdf")
                    if path.is_file() and len(path.relative_to(base_path).parts) <= max_depth
                ]
            except Exception:
                logger.exception(
                    "[HC_IMPORT] batch_no=%s resolved_path=%s reason=recursive_scan_failed",
                    batch,
                    base_path,
                )
                return None

        pdf_count = len(pdfs)
        logger.info(
            "[HC_IMPORT] batch_no=%s folder_path=%s total_files=%s pdf_count=%s",
            batch,
            base_path,
            total_files,
            pdf_count,
        )

        if not pdfs:
            logger.error(
                "[HC_IMPORT] batch_no=%s folder_path=%s total_files=%s pdf_count=0 reason=no_pdfs_found",
                batch,
                base_path,
                total_files,
            )
            return None

        # Pick first PDF deterministically (alphabetical) for stable repeatable imports.
        pdfs.sort(key=lambda p: p.name.lower())
        selected = pdfs[0]
        logger.info(
            "[HC_IMPORT] batch_no=%s resolved_path=%s exists=true pdf_count=%s selected=%s selected_mtime=%s",
            batch,
            base_path,
            pdf_count,
            selected,
            int(selected.stat().st_mtime),
        )
        return selected


def resolve_pdf_path(batch_no: str | int) -> str | None:
    """
    Backward-compatible helper used by older call sites.
    Returns resolved PDF path as string or None.
    """
    resolved = HighCourtPDFResolverService().resolve_pdf(batch_no)
    return str(resolved) if resolved else None
