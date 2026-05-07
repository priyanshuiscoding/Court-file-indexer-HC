from __future__ import annotations

import logging
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HighCourtMySQLService:
    def _connect(self):
        if not settings.HC_MYSQL_HOST:
            raise RuntimeError("HC_MYSQL_HOST is not configured")
        if not settings.HC_MYSQL_USER:
            raise RuntimeError("HC_MYSQL_USER is not configured")
        if not settings.HC_MYSQL_PASSWORD:
            raise RuntimeError("HC_MYSQL_PASSWORD is not configured")

        return pymysql.connect(
            host=settings.HC_MYSQL_HOST,
            port=int(settings.HC_MYSQL_PORT),
            user=settings.HC_MYSQL_USER,
            password=settings.HC_MYSQL_PASSWORD,
            database=settings.HC_MYSQL_DB,
            cursorclass=DictCursor,
            connect_timeout=10,
            read_timeout=30,
            charset="utf8mb4",
        )

    def fetch_pending_rows(self, limit: int) -> list[dict[str, Any]]:
        table = settings.HC_MYSQL_TABLE or "mp_indexing_batch"
        db_name = settings.HC_MYSQL_DB or "Digitization"
        zero_date = "0000-00-00 00:00:00"
        order = "DESC" if str(settings.HC_IMPORT_ORDER).upper() == "DESC" else "ASC"

        query = f"""
            SELECT id, batch_no, fil_no, entry_dt, total_pages
            FROM `{db_name}`.`{table}`
            WHERE branch = %s
              AND completed = %s
              AND indexing_com_date = %s
              AND process_id = %s
              AND clean_fl_pdf_gen_dt != %s
            ORDER BY id {order}
            LIMIT %s
        """
        params = (
            1,
            0,
            zero_date,
            1,
            zero_date,
            limit,
        )

        logger.info("Fetching pending High Court rows limit=%s", limit)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = list(cur.fetchall())

        logger.info("Fetched %s pending High Court rows", len(rows))
        return rows

    def mark_completed(self, *, external_row_id: str | int | None, batch_no: str) -> dict[str, Any]:
        if not settings.HC_MYSQL_MARK_COMPLETE_ENABLED:
            return {
                "ok": False,
                "disabled": True,
                "message": "External MySQL completion update is disabled",
                "rows_affected": 0,
            }

        table = settings.HC_MYSQL_TABLE or "mp_indexing_batch"
        db_name = settings.HC_MYSQL_DB or "Digitization"
        complete_field = settings.HC_MYSQL_COMPLETE_FIELD or "completed"
        date_field = settings.HC_MYSQL_INDEX_DATE_FIELD or "indexing_com_date"
        batch_no = str(batch_no).strip()

        if external_row_id:
            query = f"""
                UPDATE `{db_name}`.`{table}`
                SET `{complete_field}` = 1,
                    `{date_field}` = NOW()
                WHERE `id` = %s
                  AND `batch_no` = %s
                  AND `{complete_field}` = 0
                LIMIT 1
            """
            params = (external_row_id, batch_no)
        else:
            query = f"""
                UPDATE `{db_name}`.`{table}`
                SET `{complete_field}` = 1,
                    `{date_field}` = NOW()
                WHERE `batch_no` = %s
                  AND `{complete_field}` = 0
                LIMIT 1
            """
            params = (batch_no,)

        with self._connect() as conn:
            with conn.cursor() as cur:
                rows = cur.execute(query, params)
            conn.commit()

        return {
            "ok": rows == 1,
            "disabled": False,
            "rows_affected": rows,
            "message": "Marked completed" if rows == 1 else "No matching pending external row updated",
        }

    def ping(self) -> dict[str, Any]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 AS ok")
                    row = cur.fetchone()
            return {"ok": True, "result": row}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
