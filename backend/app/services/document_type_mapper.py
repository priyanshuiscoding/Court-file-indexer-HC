from __future__ import annotations

import csv
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from app.core.config import get_settings

settings = get_settings()

XLSX_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@dataclass(frozen=True)
class DocmasterRow:
    doccode: int
    doccode1: int
    docdesc: str
    display: str
    doc_id: int | None
    norm_docdesc: str


@dataclass(frozen=True)
class MappingResult:
    row: DocmasterRow | None
    source: str
    confidence: float
    status: str


class DocumentTypeMapper:
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or settings.DOCMASTER_MAPPING_PATH)
        self._cache: list[DocmasterRow] = []
        self._last_loaded_at = 0.0
        self._last_mtime: float | None = None

    def enrich_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.enrich_row(row) for row in rows]

    def enrich_row(self, row: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(row)
        result = self.map_row(enriched)

        if result.row is None:
            enriched["mapped_document_type"] = None
            enriched["mapped_sub_document_type"] = None
            enriched["mapping_source"] = result.source
            enriched["mapping_confidence"] = result.confidence
            enriched["mapping_status"] = "UNMAPPED"
            enriched["status"] = "REVIEW"
            return enriched

        enriched["mapped_document_type"] = {
            "doccode": result.row.doccode,
            "doccode1": result.row.doccode1,
            "docdesc": result.row.docdesc,
        }
        enriched["mapped_sub_document_type"] = None
        enriched["mapping_source"] = result.source
        enriched["mapping_confidence"] = result.confidence
        enriched["mapping_status"] = result.status

        if result.source == "annexure_no" or result.status == "REVIEW":
            others = dict(enriched.get("others") or {})
            others.setdefault("original_description", self._description(enriched))
            enriched["others"] = others

        if result.status == "REVIEW":
            enriched["status"] = "REVIEW"

        return enriched

    def map_row(self, row: dict[str, Any]) -> MappingResult:
        docmaster = self.load_docmaster()
        if not docmaster:
            return MappingResult(None, "docmaster_missing", 0.0, "UNMAPPED")

        annexure_no = str(row.get("annexure_no") or "").strip()
        if annexure_no:
            annexure = normalize_annexure_no(annexure_no)
            annexure_match = self.find_doc(doccode=16, docdesc=annexure)
            if annexure_match:
                return MappingResult(annexure_match, "annexure_no", 1.0, "MAPPED")

        text = normalize_text(self._description(row))

        keyword_rules: list[tuple[bool, int, int, float]] = [
            ("vakalatnama" in text, 12, 0, 1.0),
            (
                any(term in text for term in ("memo of misc appeal", "memo of miscellaneous appeal", "memo of appeal")),
                13,
                0,
                0.95,
            ),
            ("list of documents" in text, 90, 0, 0.95),
            ("impugned order" in text, 14, 0, 0.95),
            ("index" in text or "chronology" in text or "chronological" in text, 9, 14, 0.90),
            (text == "affidavit" or text.startswith("affidavit "), 11, 0, 0.95),
            ("stay" in text and "application" in text, 8, 27, 0.85),
            ("interim relief" in text, 8, 38, 0.85),
            ("condonation of delay" in text, 8, 28, 0.85),
        ]

        for matched, doccode, doccode1, confidence in keyword_rules:
            if matched:
                fixed = self.find_doc(doccode=doccode, doccode1=doccode1)
                if fixed:
                    return MappingResult(fixed, "keyword", confidence, "MAPPED")

        exact = self.find_doc(docdesc=text)
        if exact:
            return MappingResult(exact, "docmaster_exact", 1.0, "MAPPED")

        fuzzy = self.find_fuzzy_doc(text)
        if fuzzy:
            return MappingResult(fuzzy[0], "docmaster_fuzzy", fuzzy[1], "MAPPED")

        other = self.find_doc(doccode=10, doccode1=0)
        if other:
            return MappingResult(other, "fallback_other", 0.30, "REVIEW")

        return MappingResult(None, "unmapped", 0.0, "UNMAPPED")

    def find_doc(
        self,
        *,
        doccode: int | None = None,
        doccode1: int | None = None,
        docdesc: str | None = None,
    ) -> DocmasterRow | None:
        norm_docdesc = normalize_text(docdesc) if docdesc is not None else None
        for row in self.load_docmaster():
            if doccode is not None and row.doccode != int(doccode):
                continue
            if doccode1 is not None and row.doccode1 != int(doccode1):
                continue
            if norm_docdesc is not None and row.norm_docdesc != norm_docdesc:
                continue
            return row
        return None

    def find_fuzzy_doc(self, description: str) -> tuple[DocmasterRow, float] | None:
        if not description:
            return None

        best: tuple[DocmasterRow, float] | None = None
        for row in self.load_docmaster():
            score = SequenceMatcher(None, description, row.norm_docdesc).ratio()
            if best is None or score > best[1]:
                best = (row, score)

        if best and best[1] >= 0.85:
            return best[0], round(best[1], 2)
        return None

    def load_docmaster(self) -> list[DocmasterRow]:
        if not self.path.exists():
            return []

        now = time.time()
        mtime = self.path.stat().st_mtime
        if (
            self._cache
            and self._last_mtime == mtime
            and (now - self._last_loaded_at) < settings.MAPPING_REFRESH_SECONDS
        ):
            return self._cache

        raw_rows = self._read_csv(self.path) if self.path.suffix.lower() == ".csv" else self._read_xlsx(self.path)
        rows: list[DocmasterRow] = []

        for raw in raw_rows:
            display = str(raw.get("display") or "").strip().upper()
            if display and display not in {"Y", "E"}:
                continue

            doccode = _to_int(raw.get("doccode"))
            doccode1 = _to_int(raw.get("doccode1"))
            docdesc = str(raw.get("docdesc") or "").strip()
            if doccode is None or doccode1 is None or not docdesc:
                continue

            rows.append(
                DocmasterRow(
                    doccode=doccode,
                    doccode1=doccode1,
                    docdesc=docdesc,
                    display=display,
                    doc_id=_to_int(raw.get("doc_id")),
                    norm_docdesc=normalize_text(docdesc),
                )
            )

        self._cache = rows
        self._last_loaded_at = now
        self._last_mtime = mtime
        return rows

    def _description(self, row: dict[str, Any]) -> str:
        return str(row.get("description") or row.get("description_raw") or row.get("raw_text") or "")

    def _read_csv(self, path: Path) -> list[dict[str, Any]]:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def _read_xlsx(self, path: Path) -> list[dict[str, Any]]:
        with ZipFile(path) as archive:
            shared_strings = self._read_shared_strings(archive)
            sheet_path = self._first_sheet_path(archive)
            root = ET.fromstring(archive.read(sheet_path))
            table: list[list[str]] = []

            for row in root.findall("a:sheetData/a:row", XLSX_NS):
                values: list[str] = []
                last_index = -1
                for cell in row.findall("a:c", XLSX_NS):
                    index = _column_index(cell.attrib["r"])
                    while last_index + 1 < index:
                        values.append("")
                        last_index += 1
                    values.append(self._cell_value(cell, shared_strings))
                    last_index = index
                table.append(values)

        header = [_normalize_header(value) for value in table[0]] if table else []
        rows: list[dict[str, Any]] = []
        for values in table[1:]:
            if not any(str(value).strip() for value in values):
                continue
            rows.append({header[index]: values[index] if index < len(values) else "" for index in range(len(header))})
        return rows

    def _read_shared_strings(self, archive: ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []

        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        return ["".join(text.text or "" for text in node.findall(".//a:t", XLSX_NS)) for node in root.findall("a:si", XLSX_NS)]

    def _first_sheet_path(self, archive: ZipFile) -> str:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        first_sheet = workbook.find("a:sheets/a:sheet", REL_NS)
        if first_sheet is None:
            raise ValueError(f"No sheets found in {self.path}")

        rel_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = relmap[rel_id].lstrip("/")
        return target if target.startswith("xl/") else f"xl/{target}"

    def _cell_value(self, cell: ET.Element, shared_strings: list[str]) -> str:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            return "".join(text.text or "" for text in cell.findall(".//a:t", XLSX_NS))

        value = cell.find("a:v", XLSX_NS)
        raw = "" if value is None else value.text or ""
        if cell_type == "s" and raw:
            return shared_strings[int(raw)]
        return raw


def normalize_text(value: Any) -> str:
    text = str(value or "").lower().strip()
    text = text.replace("-", " ")
    text = re.sub(r"[./_,:;()\[\]{}]+", " ", text)
    text = re.sub(r"\b([a-z])\s+(\d+)\b", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_annexure_no(value: Any) -> str:
    text = normalize_text(value)
    return re.sub(r"\s+", "", text).upper()


def _column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref)
    if not letters:
        return 0
    index = 0
    for char in letters.group(0):
        index = index * 26 + ord(char) - 64
    return index - 1


def _normalize_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _to_int(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
