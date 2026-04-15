<p align="center">
  <img src="https://raw.githubusercontent.com/roosterhr/reveilio/main/docs/assets/logo.png" alt="Reveilio logo" width="120" />
</p>

<h1 align="center">reveilio</h1>

<p align="center">
  AI-powered resume and job-description matching and scoring.
</p>

<p align="center">
  <a href="https://pypi.org/project/reveilio/"><img src="https://img.shields.io/pypi/v/reveilio.svg" alt="PyPI" /></a>
  <a href="https://github.com/roosterhr/reveilio/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/roosterhr/reveilio/ci.yml?branch=main&label=tests" alt="Tests" /></a>
  <a href="https://github.com/roosterhr/reveilio/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python" /></a>
</p>

Reveilio takes a **job description** (file or free text) and one or many
**resumes** (PDF, DOCX, DOC, TXT, or free text) and returns a detailed,
weighted match score together with structured candidate data. It supports
Gemini, OpenAI, Azure OpenAI, and a local Ollama model.

## Install

```bash
pip install reveilio
```

## Quickstart

```python
import reveilio

# 1. Configure your LLM provider once
reveilio.configure(provider="gemini", api_key="AIza...")
# or: provider="openai", api_key="sk-..."
# or: provider="azure", api_key="...", azure_endpoint="https://...", azure_deployment="gpt-4o"
# or: provider="ollama", base_url="http://localhost:11434", model="llama3.2"

# 2. Build a JD from a file or free text
jd = reveilio.JobDescription.from_file("jd.pdf")
# jd = reveilio.JobDescription.from_text("We're hiring a Senior Python engineer...")

# 3a. Analyze a single resume
result = reveilio.analyze_resume("resumes/alice.pdf", jd)
print(result.overall_score, result.recommendation)

# 3b. Or an entire folder of resumes, sorted and ranked by score
results = reveilio.analyze_folder("resumes/", jd)
for r in results:
    print(r.rank, r.candidate_data.name, r.overall_score)

# 4. Export a PDF report
reveilio.save_report_pdf(result, "alice_report.pdf")
reveilio.save_batch_report_pdf(results, "batch_ranking.pdf")
```

## Run with Docker (Streamlit UI)

Prefer a UI over writing Python? Clone the repo and run:

```bash
docker compose up --build
```

Then open `http://localhost:8501` in your browser. The Streamlit UI exposes
every reveilio feature — LLM provider configuration, JD parsing, single or
batch resume scoring, database storage, and PDF report downloads.

The Docker image and the PyPI wheel are independent distribution channels.
`pip install reveilio` is unaffected by the UI — Streamlit is not a runtime
dependency of the library. See [docs/docker.html](docs/docker.html) for
details, persistence, and connecting to external databases.

## Supported inputs

- **JD**: `.pdf`, `.docx`, `.doc`, `.txt`, or a plain Python string.
- **Resume**: `.pdf`, `.docx`, `.doc`, `.txt`, or a plain Python string.

You can manage multiple JDs simultaneously by keeping multiple
`JobDescription` instances around. Each instance is independent.

## Supported LLM providers

| Provider      | `configure()` call                                                        |
|---------------|---------------------------------------------------------------------------|
| Gemini        | `configure(provider="gemini", api_key="AIza...")`                         |
| OpenAI        | `configure(provider="openai", api_key="sk-...", model="gpt-4o-mini")`     |
| Azure OpenAI  | `configure(provider="azure", api_key=..., azure_endpoint=..., azure_deployment=...)` |
| Ollama (self) | `configure(provider="ollama", base_url="http://localhost:11434", model="llama3.2")` |

Environment variable fallbacks: `GEMINI_API_KEY`, `OPENAI_API_KEY`,
`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`,
and `OLLAMA_BASE_URL`.

## Documentation

Full documentation lives in the `docs/` directory. Open `docs/index.html`
in a browser for the complete guide, including configuration, API
reference, guides, architecture, and contributing instructions.

## Contributing

Contributions are welcome. The full contributing guide is in
`docs/contributing.html`. The short version:

### 1. Fork and clone

```bash
git clone https://github.com/roosterhr/reveilio.git
cd reveilio
```

### 2. Create a virtual environment and install dev dependencies

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```

### 3. Create a feature branch

Use a descriptive prefix: `fix/`, `feat/`, `docs/`, or `refactor/`.

```bash
git checkout -b feat/my-change
```

### 4. Make your change

- Keep pull requests focused. One PR should address one concern.
- Match the existing code style. Reveilio avoids over-abstraction.
- Add or update tests for every bug fix and feature. Tests must not
  make real LLM calls; mock `json_completion` as the existing suite does.
- Update the relevant docs pages under `docs/` when public behavior changes.
- Do not add new runtime dependencies without prior discussion.

### 5. Lint and test locally

Reveilio uses [ruff](https://docs.astral.sh/ruff/) for linting and
formatting, and `pytest` for tests. Both must be green before you open
a pull request.

```bash
ruff check src tests
ruff format --check src tests
pytest -q
```

To auto-fix lint issues and format the code:

```bash
ruff check src tests --fix
ruff format src tests
```

### 6. Commit

Write imperative, present-tense commit subjects at 72 characters or fewer,
and explain the *why* in the body. Reference related issues with
`Fixes #123` or `Refs #123`.

### 7. Open a pull request

Push your branch to your fork and open a pull request against `main`.
Fill out the PR template with a summary, motivation, and notes on any
manual testing. Respond to review feedback promptly, and rebase (do not
merge) onto `main` if it advances while your PR is open:

```bash
git fetch origin
git rebase origin/main
git push --force-with-lease
```

### Reporting security issues

Please do not report security vulnerabilities through public GitHub
issues. Email the maintainers privately with a detailed description.

## License

MIT
