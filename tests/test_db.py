"""Tests for the database storage feature (SQLite backend — no external server needed)."""

from __future__ import annotations

import os

import pytest

import reveilio
from reveilio.models import AnalysisResult, ResumeData


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary SQLite database and connect to it."""
    db_path = str(tmp_path / "test.db")
    reveilio.connect_db("sqlite", filepath=db_path)
    yield db_path
    reveilio.disconnect_db()


@pytest.fixture()
def sample_result() -> AnalysisResult:
    """A minimal AnalysisResult for testing."""
    return AnalysisResult(
        overall_score=85.5,
        confidence_level="High",
        recommendation="Shortlist",
        ai_summary="Strong candidate with relevant experience.",
        strengths=["Python", "System design"],
        weaknesses=["No cloud experience"],
        candidate_data=ResumeData(
            name="Jane Doe",
            email="jane@example.com",
            skills=["Python", "Django", "PostgreSQL"],
            total_experience=5.0,
            filename="jane_doe_resume.pdf",
        ),
    )


@pytest.fixture()
def sample_results() -> list[AnalysisResult]:
    """Multiple AnalysisResults for batch testing."""
    return [
        AnalysisResult(
            overall_score=90,
            recommendation="Shortlist",
            confidence_level="High",
            candidate_data=ResumeData(name="Alice Smith", skills=["Go", "Kubernetes"]),
        ),
        AnalysisResult(
            overall_score=65,
            recommendation="Needs Review",
            confidence_level="Medium",
            candidate_data=ResumeData(name="Bob Jones", skills=["JavaScript"]),
        ),
        AnalysisResult(
            overall_score=40,
            recommendation="Not Suitable",
            confidence_level="Low",
            candidate_data=ResumeData(name="Charlie Brown", skills=["Excel"]),
        ),
    ]


class TestConnectDb:
    def test_connect_sqlite_creates_file(self, tmp_path):
        db_path = str(tmp_path / "new.db")
        reveilio.connect_db("sqlite", filepath=db_path)
        assert os.path.exists(db_path)
        reveilio.disconnect_db()

    def test_connect_sqlite_default_filepath(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        reveilio.connect_db("sqlite")
        assert os.path.exists(tmp_path / "reveilio.db")
        reveilio.disconnect_db()

    def test_connect_invalid_backend_raises(self):
        with pytest.raises(ValueError, match="Unsupported database backend"):
            reveilio.connect_db("redis")

    def test_get_db_without_connect_raises(self):
        reveilio.disconnect_db()
        with pytest.raises(RuntimeError, match="No database configured"):
            reveilio.get_db()

    def test_reconnect_closes_old_connection(self, tmp_path):
        db1 = str(tmp_path / "db1.db")
        db2 = str(tmp_path / "db2.db")
        reveilio.connect_db("sqlite", filepath=db1)
        reveilio.connect_db("sqlite", filepath=db2)
        # Should work fine — old connection closed, new one active
        cfg, conn = reveilio.get_db()
        assert cfg.filepath == db2
        reveilio.disconnect_db()


class TestExportImport:
    def test_export_and_import_single(self, tmp_db, sample_result):
        aid = reveilio.export_result(sample_result, job_title="Backend Engineer")
        assert isinstance(aid, str)
        assert len(aid) > 0

        loaded = reveilio.import_result(aid)
        assert loaded.overall_score == 85.5
        assert loaded.recommendation == "Shortlist"
        assert loaded.candidate_data.name == "Jane Doe"
        assert loaded.candidate_data.skills == ["Python", "Django", "PostgreSQL"]

    def test_export_with_custom_id(self, tmp_db, sample_result):
        aid = reveilio.export_result(sample_result, analysis_id="custom-001")
        assert aid == "custom-001"

        loaded = reveilio.import_result("custom-001")
        assert loaded.overall_score == 85.5

    def test_import_nonexistent_raises(self, tmp_db):
        with pytest.raises(KeyError, match="No analysis found"):
            reveilio.import_result("nonexistent-id")

    def test_export_batch(self, tmp_db, sample_results):
        ids = reveilio.export_results(sample_results, job_title="SRE")
        assert len(ids) == 3

        loaded = reveilio.import_results(limit=10)
        assert len(loaded) == 3

    def test_export_dict_input(self, tmp_db, sample_result):
        data = sample_result.model_dump()
        aid = reveilio.export_result(data)
        loaded = reveilio.import_result(aid)
        assert loaded.overall_score == 85.5

    def test_import_with_pagination(self, tmp_db, sample_results):
        reveilio.export_results(sample_results)

        page1 = reveilio.import_results(limit=2, offset=0)
        page2 = reveilio.import_results(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 1

    def test_import_order_by_score(self, tmp_db, sample_results):
        reveilio.export_results(sample_results)

        desc = reveilio.import_results(order_by="overall_score", descending=True)
        scores = [r.overall_score for r in desc]
        assert scores == sorted(scores, reverse=True)


class TestListAnalyses:
    def test_list_returns_metadata(self, tmp_db, sample_result):
        reveilio.export_result(sample_result, job_title="Engineer")

        entries = reveilio.list_analyses()
        assert len(entries) == 1
        entry = entries[0]
        assert entry["candidate_name"] == "Jane Doe"
        assert entry["overall_score"] == 85.5
        assert entry["recommendation"] == "Shortlist"
        assert entry["job_title"] == "Engineer"
        assert "analysis_id" in entry

    def test_list_pagination(self, tmp_db, sample_results):
        reveilio.export_results(sample_results)
        page = reveilio.list_analyses(limit=2, offset=0)
        assert len(page) == 2


class TestQueryResults:
    def test_query_by_min_score(self, tmp_db, sample_results):
        reveilio.export_results(sample_results)

        top = reveilio.query_results(min_score=70)
        assert len(top) == 1
        assert top[0].overall_score == 90

    def test_query_by_recommendation(self, tmp_db, sample_results):
        reveilio.export_results(sample_results)

        shortlisted = reveilio.query_results(recommendation="Shortlist")
        assert len(shortlisted) == 1
        assert shortlisted[0].candidate_data.name == "Alice Smith"

    def test_query_by_candidate_name(self, tmp_db, sample_results):
        reveilio.export_results(sample_results)

        matches = reveilio.query_results(candidate_name="Bob")
        assert len(matches) == 1
        assert matches[0].candidate_data.name == "Bob Jones"

    def test_query_by_job_title(self, tmp_db, sample_results):
        reveilio.export_results(sample_results, job_title="DevOps Engineer")

        matches = reveilio.query_results(job_title="DevOps")
        assert len(matches) == 3

    def test_query_score_range(self, tmp_db, sample_results):
        reveilio.export_results(sample_results)

        mid = reveilio.query_results(min_score=50, max_score=80)
        assert len(mid) == 1
        assert mid[0].overall_score == 65

    def test_query_combined_filters(self, tmp_db, sample_results):
        reveilio.export_results(sample_results, job_title="Backend")

        matches = reveilio.query_results(
            min_score=60,
            recommendation="Shortlist",
            job_title="Backend",
        )
        assert len(matches) == 1
        assert matches[0].candidate_data.name == "Alice Smith"

    def test_query_no_matches(self, tmp_db, sample_results):
        reveilio.export_results(sample_results)
        matches = reveilio.query_results(min_score=99)
        assert matches == []


class TestDeleteResult:
    def test_delete_existing(self, tmp_db, sample_result):
        aid = reveilio.export_result(sample_result)
        assert reveilio.delete_result(aid) is True

        with pytest.raises(KeyError):
            reveilio.import_result(aid)

    def test_delete_nonexistent(self, tmp_db):
        assert reveilio.delete_result("no-such-id") is False


class TestDatabaseConfig:
    def test_sqlite_connection_string(self):
        from reveilio.db.config import DatabaseConfig

        cfg = DatabaseConfig(backend="sqlite", filepath="test.db")
        assert cfg.get_connection_string() == "test.db"

    def test_postgresql_connection_string(self):
        from reveilio.db.config import DatabaseConfig

        cfg = DatabaseConfig(
            backend="postgresql",
            host="myhost",
            port=5433,
            database="mydb",
            username="user",
            password="pass",
        )
        assert cfg.get_connection_string() == "postgresql://user:pass@myhost:5433/mydb"

    def test_mysql_connection_string(self):
        from reveilio.db.config import DatabaseConfig

        cfg = DatabaseConfig(
            backend="mysql",
            host="dbhost",
            port=3307,
            database="hiring",
            username="root",
            password="secret",
        )
        assert cfg.get_connection_string() == "mysql://root:secret@dbhost:3307/hiring"

    def test_mongodb_connection_string_with_auth(self):
        from reveilio.db.config import DatabaseConfig

        cfg = DatabaseConfig(
            backend="mongodb",
            host="mongohost",
            port=27018,
            database="mydb",
            username="admin",
            password="pwd",
        )
        assert cfg.get_connection_string() == "mongodb://admin:pwd@mongohost:27018/mydb"

    def test_mongodb_connection_string_without_auth(self):
        from reveilio.db.config import DatabaseConfig

        cfg = DatabaseConfig(backend="mongodb", host="localhost", database="mydb")
        assert cfg.get_connection_string() == "mongodb://localhost:27017/mydb"

    def test_connection_string_override(self):
        from reveilio.db.config import DatabaseConfig

        cfg = DatabaseConfig(
            backend="postgresql",
            connection_string="postgresql://custom@host/db",
            host="ignored",
        )
        assert cfg.get_connection_string() == "postgresql://custom@host/db"

    def test_env_var_fallbacks(self, tmp_path, monkeypatch):
        monkeypatch.setenv("REVEILIO_DB_HOST", "env-host")
        monkeypatch.setenv("REVEILIO_DB_PORT", "9999")
        monkeypatch.setenv("REVEILIO_DB_NAME", "env-db")

        db_path = str(tmp_path / "env_test.db")
        cfg = reveilio.connect_db("sqlite", filepath=db_path)
        # SQLite ignores host/port/name, but they should be stored
        assert cfg.host == "env-host"
        assert cfg.port == 9999
        assert cfg.database == "env-db"
        reveilio.disconnect_db()

    def test_custom_table_name(self, tmp_path):
        db_path = str(tmp_path / "custom_table.db")
        cfg = reveilio.connect_db("sqlite", filepath=db_path, table_name="my_table")
        assert cfg.table_name == "my_table"

        result = AnalysisResult(overall_score=50, candidate_data=ResumeData(name="Test"))
        aid = reveilio.export_result(result)
        loaded = reveilio.import_result(aid)
        assert loaded.overall_score == 50
        reveilio.disconnect_db()
