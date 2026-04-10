"""Database connection configuration for reveilio.

Users call :func:`connect_db` to set up a database backend. All downstream
DB operations read from the singleton returned by :func:`get_db`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal

DBBackend = Literal["sqlite", "postgresql", "mysql", "mongodb"]


@dataclass
class DatabaseConfig:
    """Connection configuration for a database backend.

    Prefer creating one via :func:`connect_db` rather than instantiating directly.
    """

    backend: DBBackend = "sqlite"

    # Connection parameters
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None

    # SQLite-specific
    filepath: str | None = None

    # Connection string override (takes precedence over individual params)
    connection_string: str | None = None

    # Table / collection name
    table_name: str = "reveilio_analyses"

    # Extra backend-specific options
    options: dict[str, Any] = field(default_factory=dict)

    def get_connection_string(self) -> str:
        """Build a connection string from the individual parameters."""
        if self.connection_string:
            return self.connection_string

        if self.backend == "sqlite":
            return self.filepath or "reveilio.db"

        if self.backend == "postgresql":
            host = self.host or "localhost"
            port = self.port or 5432
            db = self.database or "reveilio"
            user = self.username or "postgres"
            pwd = self.password or ""
            return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

        if self.backend == "mysql":
            host = self.host or "localhost"
            port = self.port or 3306
            db = self.database or "reveilio"
            user = self.username or "root"
            pwd = self.password or ""
            return f"mysql://{user}:{pwd}@{host}:{port}/{db}"

        if self.backend == "mongodb":
            host = self.host or "localhost"
            port = self.port or 27017
            db = self.database or "reveilio"
            user = self.username or ""
            pwd = self.password or ""
            if user and pwd:
                return f"mongodb://{user}:{pwd}@{host}:{port}/{db}"
            return f"mongodb://{host}:{port}/{db}"

        raise ValueError(f"Unsupported backend: {self.backend!r}")


_db_config: DatabaseConfig | None = None
_db_connection: Any = None


def connect_db(
    backend: DBBackend = "sqlite",
    *,
    host: str | None = None,
    port: int | None = None,
    database: str | None = None,
    username: str | None = None,
    password: str | None = None,
    filepath: str | None = None,
    connection_string: str | None = None,
    table_name: str = "reveilio_analyses",
    options: dict[str, Any] | None = None,
) -> DatabaseConfig:
    """Configure and connect to a database backend.

    Any argument left as ``None`` falls back to environment variables:

    * ``REVEILIO_DB_BACKEND`` (sqlite, postgresql, mysql, mongodb)
    * ``REVEILIO_DB_HOST`` / ``REVEILIO_DB_PORT``
    * ``REVEILIO_DB_NAME`` / ``REVEILIO_DB_USER`` / ``REVEILIO_DB_PASSWORD``
    * ``REVEILIO_DB_FILEPATH`` (SQLite only)
    * ``REVEILIO_DB_URL`` (full connection string override)
    * ``REVEILIO_DB_TABLE`` (table/collection name)

    Examples::

        # SQLite (simplest — no server needed)
        reveilio.connect_db("sqlite", filepath="my_analyses.db")

        # PostgreSQL
        reveilio.connect_db(
            "postgresql",
            host="localhost",
            port=5432,
            database="recruitment",
            username="admin",
            password="secret",
        )

        # MySQL
        reveilio.connect_db(
            "mysql",
            host="db.example.com",
            database="hiring",
            username="root",
            password="secret",
        )

        # MongoDB
        reveilio.connect_db(
            "mongodb",
            host="localhost",
            database="reveilio",
        )

        # Connection string override (any backend)
        reveilio.connect_db(
            "postgresql",
            connection_string="postgresql://user:pass@host:5432/mydb",
        )
    """
    global _db_config, _db_connection

    # Close existing connection if any
    if _db_connection is not None:
        _close_connection()

    backend = (backend or os.environ.get("REVEILIO_DB_BACKEND", "sqlite")).lower()  # type: ignore[assignment]
    if backend not in ("sqlite", "postgresql", "mysql", "mongodb"):
        raise ValueError(
            f"Unsupported database backend {backend!r}. "
            "Use one of: sqlite, postgresql, mysql, mongodb."
        )

    _db_config = DatabaseConfig(
        backend=backend,  # type: ignore[arg-type]
        host=host or os.environ.get("REVEILIO_DB_HOST"),
        port=port or _int_or_none(os.environ.get("REVEILIO_DB_PORT")),
        database=database or os.environ.get("REVEILIO_DB_NAME"),
        username=username or os.environ.get("REVEILIO_DB_USER"),
        password=password or os.environ.get("REVEILIO_DB_PASSWORD"),
        filepath=filepath or os.environ.get("REVEILIO_DB_FILEPATH"),
        connection_string=connection_string or os.environ.get("REVEILIO_DB_URL"),
        table_name=table_name or os.environ.get("REVEILIO_DB_TABLE", "reveilio_analyses"),
        options=dict(options) if options else {},
    )

    _db_connection = _open_connection(_db_config)
    return _db_config


def get_db() -> tuple[DatabaseConfig, Any]:
    """Return the active DB config and connection.

    Raises :class:`RuntimeError` if :func:`connect_db` was never called.
    """
    if _db_config is None or _db_connection is None:
        raise RuntimeError("No database configured. Call reveilio.connect_db(backend=...) first.")
    return _db_config, _db_connection


def _int_or_none(val: str | None) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _open_connection(cfg: DatabaseConfig) -> Any:
    """Open a connection to the configured database backend."""
    if cfg.backend == "sqlite":
        return _connect_sqlite(cfg)
    elif cfg.backend == "postgresql":
        return _connect_postgresql(cfg)
    elif cfg.backend == "mysql":
        return _connect_mysql(cfg)
    elif cfg.backend == "mongodb":
        return _connect_mongodb(cfg)
    raise ValueError(f"Unsupported backend: {cfg.backend!r}")


def _close_connection() -> None:
    """Close the active database connection."""
    global _db_connection
    if _db_connection is None:
        return
    try:
        if hasattr(_db_connection, "close"):
            _db_connection.close()
    except Exception:
        pass
    _db_connection = None


def _connect_sqlite(cfg: DatabaseConfig) -> Any:
    import sqlite3

    path = cfg.filepath or cfg.get_connection_string()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_sqlite_table(conn, cfg.table_name)
    return conn


def _connect_postgresql(cfg: DatabaseConfig) -> Any:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        raise ImportError(
            "PostgreSQL support requires psycopg2. "
            "Install it with: pip install reveilio[postgresql]"
        ) from None

    if cfg.connection_string:
        conn = psycopg2.connect(cfg.connection_string)
    else:
        conn = psycopg2.connect(
            host=cfg.host or "localhost",
            port=cfg.port or 5432,
            dbname=cfg.database or "reveilio",
            user=cfg.username or "postgres",
            password=cfg.password or "",
            **cfg.options,
        )
    conn.autocommit = True
    _ensure_sql_table(conn, cfg.table_name, "postgresql")
    return conn


def _connect_mysql(cfg: DatabaseConfig) -> Any:
    try:
        import pymysql
    except ImportError:
        raise ImportError(
            "MySQL support requires PyMySQL. Install it with: pip install reveilio[mysql]"
        ) from None

    if cfg.connection_string:
        # Parse connection string for PyMySQL
        from urllib.parse import urlparse

        parsed = urlparse(cfg.connection_string)
        conn = pymysql.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            database=parsed.path.lstrip("/") or "reveilio",
            user=parsed.username or "root",
            password=parsed.password or "",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            **cfg.options,
        )
    else:
        conn = pymysql.connect(
            host=cfg.host or "localhost",
            port=cfg.port or 3306,
            database=cfg.database or "reveilio",
            user=cfg.username or "root",
            password=cfg.password or "",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            **cfg.options,
        )
    conn.autocommit(True)
    _ensure_sql_table(conn, cfg.table_name, "mysql")
    return conn


def _connect_mongodb(cfg: DatabaseConfig) -> Any:
    try:
        import pymongo
    except ImportError:
        raise ImportError(
            "MongoDB support requires PyMongo. Install it with: pip install reveilio[mongodb]"
        ) from None

    conn_str = cfg.get_connection_string()
    client = pymongo.MongoClient(conn_str, **cfg.options)
    db_name = cfg.database or "reveilio"
    db = client[db_name]
    # Ensure indexes
    collection = db[cfg.table_name]
    collection.create_index("analysis_id", unique=True)
    collection.create_index("candidate_name")
    collection.create_index("overall_score")
    collection.create_index("created_at")
    return db


def _ensure_sqlite_table(conn: Any, table_name: str) -> None:
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id TEXT UNIQUE NOT NULL,
            candidate_name TEXT,
            overall_score REAL,
            confidence_level TEXT,
            recommendation TEXT,
            job_title TEXT,
            data JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_candidate
        ON {table_name}(candidate_name)
    """)
    conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_score
        ON {table_name}(overall_score)
    """)
    conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_recommendation
        ON {table_name}(recommendation)
    """)
    conn.commit()


def _ensure_sql_table(conn: Any, table_name: str, dialect: str) -> None:
    """Create the analysis table for PostgreSQL or MySQL."""
    if dialect == "postgresql":
        json_type = "JSONB"
        auto_id = "SERIAL PRIMARY KEY"
        timestamp_default = "DEFAULT NOW()"
    else:
        json_type = "JSON"
        auto_id = "INT AUTO_INCREMENT PRIMARY KEY"
        timestamp_default = "DEFAULT CURRENT_TIMESTAMP"

    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id {auto_id},
            analysis_id VARCHAR(255) UNIQUE NOT NULL,
            candidate_name VARCHAR(500),
            overall_score FLOAT,
            confidence_level VARCHAR(50),
            recommendation VARCHAR(100),
            job_title VARCHAR(500),
            data {json_type} NOT NULL,
            created_at TIMESTAMP {timestamp_default},
            updated_at TIMESTAMP {timestamp_default}
        )
    """)
    cur.close()
