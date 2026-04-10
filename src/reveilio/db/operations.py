"""High-level database operations for saving and loading analysis results."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from reveilio.db.config import DatabaseConfig, _close_connection, get_db
from reveilio.models import AnalysisResult


def disconnect_db() -> None:
    """Close the active database connection and reset state."""
    from reveilio.db import config as _cfg

    _close_connection()
    _cfg._db_config = None


def export_result(
    result: AnalysisResult | dict[str, Any],
    *,
    job_title: str | None = None,
    analysis_id: str | None = None,
) -> str:
    """Save a single analysis result to the database.

    Returns the ``analysis_id`` assigned to the stored record.
    """
    cfg, conn = get_db()
    record = _prepare_record(result, job_title=job_title, analysis_id=analysis_id)

    if cfg.backend == "mongodb":
        _insert_mongodb(conn, cfg.table_name, record)
    else:
        _insert_sql(conn, cfg, record)

    return record["analysis_id"]


def export_results(
    results: list[AnalysisResult | dict[str, Any]],
    *,
    job_title: str | None = None,
) -> list[str]:
    """Save multiple analysis results to the database.

    Returns a list of ``analysis_id`` values for each stored record.
    """
    ids = []
    for result in results:
        aid = export_result(result, job_title=job_title)
        ids.append(aid)
    return ids


def import_result(analysis_id: str) -> AnalysisResult:
    """Load a single analysis result by its ``analysis_id``.

    Raises :class:`KeyError` if not found.
    """
    cfg, conn = get_db()

    if cfg.backend == "mongodb":
        doc = conn[cfg.table_name].find_one({"analysis_id": analysis_id})
        if doc is None:
            raise KeyError(f"No analysis found with id: {analysis_id!r}")
        return AnalysisResult.model_validate(doc["data"])

    cur = conn.cursor()
    cur.execute(
        f"SELECT data FROM {cfg.table_name} WHERE analysis_id = %s"
        if cfg.backend != "sqlite"
        else f"SELECT data FROM {cfg.table_name} WHERE analysis_id = ?",
        (analysis_id,),
    )
    row = cur.fetchone()
    cur.close()
    if row is None:
        raise KeyError(f"No analysis found with id: {analysis_id!r}")

    data = row["data"] if isinstance(row, dict) else row[0]
    if isinstance(data, str):
        data = json.loads(data)
    return AnalysisResult.model_validate(data)


def import_results(
    *,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "created_at",
    descending: bool = True,
) -> list[AnalysisResult]:
    """Load multiple analysis results from the database.

    Results are ordered by ``order_by`` (default: most recent first).
    """
    cfg, conn = get_db()
    direction = "DESC" if descending else "ASC"

    if cfg.backend == "mongodb":
        sort_dir = -1 if descending else 1
        docs = conn[cfg.table_name].find().sort(order_by, sort_dir).skip(offset).limit(limit)
        return [AnalysisResult.model_validate(doc["data"]) for doc in docs]

    cur = conn.cursor()
    placeholder = "?" if cfg.backend == "sqlite" else "%s"
    cur.execute(
        f"SELECT data FROM {cfg.table_name} ORDER BY {order_by} {direction} "
        f"LIMIT {placeholder} OFFSET {placeholder}",
        (limit, offset),
    )
    rows = cur.fetchall()
    cur.close()

    results = []
    for row in rows:
        data = row["data"] if isinstance(row, dict) else row[0]
        if isinstance(data, str):
            data = json.loads(data)
        results.append(AnalysisResult.model_validate(data))
    return results


def list_analyses(
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List stored analyses (metadata only, without full data payload).

    Returns a list of dicts with: analysis_id, candidate_name, overall_score,
    recommendation, job_title, created_at.
    """
    cfg, conn = get_db()
    fields = [
        "analysis_id",
        "candidate_name",
        "overall_score",
        "confidence_level",
        "recommendation",
        "job_title",
        "created_at",
    ]

    if cfg.backend == "mongodb":
        projection = dict.fromkeys(fields, 1)
        projection["_id"] = 0
        docs = (
            conn[cfg.table_name]
            .find({}, projection)
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        return list(docs)

    cols = ", ".join(fields)
    cur = conn.cursor()
    placeholder = "?" if cfg.backend == "sqlite" else "%s"
    cur.execute(
        f"SELECT {cols} FROM {cfg.table_name} ORDER BY created_at DESC "
        f"LIMIT {placeholder} OFFSET {placeholder}",
        (limit, offset),
    )
    rows = cur.fetchall()
    cur.close()

    result_list = []
    for row in rows:
        if isinstance(row, dict):
            result_list.append({f: row[f] for f in fields})
        else:
            result_list.append(dict(zip(fields, row)))
    return result_list


def query_results(
    *,
    candidate_name: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    recommendation: str | None = None,
    job_title: str | None = None,
    limit: int = 100,
) -> list[AnalysisResult]:
    """Query analysis results with filters.

    All filters are optional and combined with AND logic.
    """
    cfg, conn = get_db()

    if cfg.backend == "mongodb":
        return _query_mongodb(
            conn,
            cfg.table_name,
            candidate_name=candidate_name,
            min_score=min_score,
            max_score=max_score,
            recommendation=recommendation,
            job_title=job_title,
            limit=limit,
        )

    return _query_sql(
        conn,
        cfg,
        candidate_name=candidate_name,
        min_score=min_score,
        max_score=max_score,
        recommendation=recommendation,
        job_title=job_title,
        limit=limit,
    )


def delete_result(analysis_id: str) -> bool:
    """Delete a single analysis by its ``analysis_id``.

    Returns ``True`` if the record was found and deleted, ``False`` otherwise.
    """
    cfg, conn = get_db()

    if cfg.backend == "mongodb":
        result = conn[cfg.table_name].delete_one({"analysis_id": analysis_id})
        return result.deleted_count > 0

    cur = conn.cursor()
    cur.execute(
        f"DELETE FROM {cfg.table_name} WHERE analysis_id = %s"
        if cfg.backend != "sqlite"
        else f"DELETE FROM {cfg.table_name} WHERE analysis_id = ?",
        (analysis_id,),
    )
    affected = cur.rowcount
    cur.close()
    if cfg.backend == "sqlite":
        conn.commit()
    return affected > 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _prepare_record(
    result: AnalysisResult | dict[str, Any],
    *,
    job_title: str | None = None,
    analysis_id: str | None = None,
) -> dict[str, Any]:
    """Convert an AnalysisResult into a flat record dict for storage."""
    data = result.model_dump() if isinstance(result, AnalysisResult) else dict(result)

    candidate_name = None
    if data.get("candidate_data") and isinstance(data["candidate_data"], dict):
        candidate_name = data["candidate_data"].get("name")
    elif isinstance(result, AnalysisResult) and result.candidate_data:
        candidate_name = result.candidate_data.name

    now = datetime.now(timezone.utc).isoformat()

    return {
        "analysis_id": analysis_id or str(uuid.uuid4()),
        "candidate_name": candidate_name,
        "overall_score": float(data.get("overall_score", 0)),
        "confidence_level": data.get("confidence_level", "Medium"),
        "recommendation": data.get("recommendation", "Needs Review"),
        "job_title": job_title,
        "data": data,
        "created_at": now,
        "updated_at": now,
    }


def _insert_sql(conn: Any, cfg: DatabaseConfig, record: dict[str, Any]) -> None:
    """Insert a record into a SQL database (SQLite, PostgreSQL, MySQL)."""
    table = cfg.table_name
    data_value = json.dumps(record["data"], default=str)
    placeholder = "?" if cfg.backend == "sqlite" else "%s"

    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO {table} "
        f"(analysis_id, candidate_name, overall_score, confidence_level, "
        f"recommendation, job_title, data, created_at, updated_at) "
        f"VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, "
        f"{placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})",
        (
            record["analysis_id"],
            record["candidate_name"],
            record["overall_score"],
            record["confidence_level"],
            record["recommendation"],
            record["job_title"],
            data_value,
            record["created_at"],
            record["updated_at"],
        ),
    )
    cur.close()
    if cfg.backend == "sqlite":
        conn.commit()


def _insert_mongodb(conn: Any, table_name: str, record: dict[str, Any]) -> None:
    """Insert a record into MongoDB."""
    conn[table_name].insert_one(record)


def _query_sql(
    conn: Any,
    cfg: DatabaseConfig,
    *,
    candidate_name: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    recommendation: str | None = None,
    job_title: str | None = None,
    limit: int = 100,
) -> list[AnalysisResult]:
    """Query a SQL database with filters."""
    placeholder = "?" if cfg.backend == "sqlite" else "%s"
    conditions: list[str] = []
    params: list[Any] = []

    if candidate_name:
        conditions.append(f"candidate_name LIKE {placeholder}")
        params.append(f"%{candidate_name}%")
    if min_score is not None:
        conditions.append(f"overall_score >= {placeholder}")
        params.append(min_score)
    if max_score is not None:
        conditions.append(f"overall_score <= {placeholder}")
        params.append(max_score)
    if recommendation:
        conditions.append(f"recommendation = {placeholder}")
        params.append(recommendation)
    if job_title:
        conditions.append(f"job_title LIKE {placeholder}")
        params.append(f"%{job_title}%")

    where = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)

    cur = conn.cursor()
    cur.execute(
        f"SELECT data FROM {cfg.table_name} WHERE {where} "
        f"ORDER BY overall_score DESC LIMIT {placeholder}",
        tuple(params),
    )
    rows = cur.fetchall()
    cur.close()

    results = []
    for row in rows:
        data = row["data"] if isinstance(row, dict) else row[0]
        if isinstance(data, str):
            data = json.loads(data)
        results.append(AnalysisResult.model_validate(data))
    return results


def _query_mongodb(
    db: Any,
    table_name: str,
    *,
    candidate_name: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    recommendation: str | None = None,
    job_title: str | None = None,
    limit: int = 100,
) -> list[AnalysisResult]:
    """Query MongoDB with filters."""
    query: dict[str, Any] = {}

    if candidate_name:
        query["candidate_name"] = {"$regex": candidate_name, "$options": "i"}
    if min_score is not None or max_score is not None:
        score_filter: dict[str, float] = {}
        if min_score is not None:
            score_filter["$gte"] = min_score
        if max_score is not None:
            score_filter["$lte"] = max_score
        query["overall_score"] = score_filter
    if recommendation:
        query["recommendation"] = recommendation
    if job_title:
        query["job_title"] = {"$regex": job_title, "$options": "i"}

    docs = db[table_name].find(query).sort("overall_score", -1).limit(limit)
    return [AnalysisResult.model_validate(doc["data"]) for doc in docs]
