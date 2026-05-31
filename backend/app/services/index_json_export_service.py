from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.models.document import Document
from app.services.document_type_mapper import DocumentTypeMapper

settings = get_settings()


class IndexJSONExportService:
    def __init__(self) -> None:
        self.root = Path(settings.EXPORT_STORAGE_DIR) / "index_json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.document_type_mapper = DocumentTypeMapper()

    def _safe_stem(self, file_name: str) -> str:
        stem = Path(file_name or "document").stem
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
        return stem[:120] or "document"

    def _parse_case_tokens(self, file_name: str, cnr_number: str | None = None) -> dict[str, Any]:
        source = (cnr_number or Path(file_name or "").stem or "").strip()
        parts = [p for p in re.split(r"[^A-Za-z0-9]+", source) if p]

        document_code = None
        case_number = None
        case_year = None

        if parts:
            if re.fullmatch(r"[A-Za-z]+", parts[0]):
                document_code = parts[0].upper()
            else:
                m = re.match(r"([A-Za-z]+)", parts[0])
                if m:
                    document_code = m.group(1).upper()

        if len(parts) >= 2 and parts[1].isdigit():
            case_number = int(parts[1])

        for token in reversed(parts):
            if token.isdigit() and len(token) == 4 and token.startswith(("19", "20")):
                case_year = int(token)
                break

        return {
            "document_code": document_code,
            "case_type": document_code,
            "case_number": case_number,
            "case_year": case_year,
        }

    def save_index_json(self, document: Document, rows: list[dict]) -> str:
        parsed = self._parse_case_tokens(document.file_name, document.cnr_number)
        generated_at = datetime.now(timezone.utc).isoformat()
        mapped_rows = self.document_type_mapper.enrich_rows(rows)

        payload = {
            "cnr_no": document.cnr_number or Path(document.file_name).stem,
            "pdf_name": document.file_name,
            "document_id": document.id,
            "document_code": parsed["document_code"],
            "case_type": parsed["case_type"],
            "case_number": parsed["case_number"],
            "case_year": parsed["case_year"],
            "batch_no": document.batch_no,
            "page_count": document.page_count,
            "generated_at": generated_at,
            "rows": mapped_rows,
            "others": {},
        }

        file_name = f"doc_{document.id}_{self._safe_stem(document.file_name)}_index.json"
        target = self.root / file_name
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(target)
