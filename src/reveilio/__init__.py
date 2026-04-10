"""Reveilio: LLM-powered resume and job-description matching.

Quickstart:

    import reveilio

    reveilio.configure(provider="gemini", api_key="AIza...")

    jd = reveilio.JobDescription.from_file("jd.pdf")   # or .from_text(...)
    result = reveilio.analyze_resume("resume.pdf", jd)
    results = reveilio.analyze_folder("./resumes", jd)

    # Download analysis as a PDF report
    reveilio.save_report_pdf(result, "report.pdf")

    # Save to database
    reveilio.connect_db("sqlite", filepath="analyses.db")
    reveilio.export_result(result, job_title="Backend Engineer")
    reveilio.export_results(results, job_title="Backend Engineer")

    # Load from database
    loaded = reveilio.import_results(limit=10)
    top = reveilio.query_results(min_score=80, recommendation="Shortlist")
"""

from reveilio.api import (
    analyze_folder,
    analyze_resume,
    save_batch_report_pdf,
    save_report_pdf,
    score,
)
from reveilio.config import ReveilioConfig, configure, get_config
from reveilio.db import (
    DatabaseConfig,
    connect_db,
    delete_result,
    disconnect_db,
    export_result,
    export_results,
    get_db,
    import_result,
    import_results,
    list_analyses,
    query_results,
)
from reveilio.models import AnalysisResult, DetailedScores, ResumeData
from reveilio.parsing.job_description import JobDescription
from reveilio.parsing.resume import Resume

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # LLM configuration
    "configure",
    "get_config",
    "ReveilioConfig",
    # Parsing
    "JobDescription",
    "Resume",
    # Analysis
    "analyze_resume",
    "analyze_folder",
    "score",
    # Reports
    "save_report_pdf",
    "save_batch_report_pdf",
    # Models
    "AnalysisResult",
    "DetailedScores",
    "ResumeData",
    # Database
    "DatabaseConfig",
    "connect_db",
    "get_db",
    "disconnect_db",
    "export_result",
    "export_results",
    "import_result",
    "import_results",
    "list_analyses",
    "query_results",
    "delete_result",
]
