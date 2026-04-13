# Contributing

Thank you for considering a contribution to reveilio. This page explains how to report issues, propose changes, and submit pull requests.

## Ways to contribute

- **Report a bug** with a minimal, reproducible example.
- **Suggest a feature** by opening an issue before writing code, so we can agree on scope.
- **Improve documentation**, including typos, clarifications, and new examples.
- **Submit a pull request** for a bug fix, performance improvement, or new provider integration.

## Before you start

1. Search [existing issues and pull requests](https://github.com/roosterhr/reveilio/issues) to avoid duplicating effort.
2. For anything beyond a small fix or typo, open an issue first and wait for maintainer feedback before writing code.
3. Make sure your change fits the project scope: reveilio is a library for LLM-driven resume scoring. Features that require a web server or external scraping service are out of scope.

## Development setup

Step-by-step setup for a new contributor:

1. **Fork and clone** the repository:
   ```bash
   git clone https://github.com/roosterhr/reveilio.git
   cd reveilio
   ```

2. **Create a virtual environment** (Python 3.9 or later):
   ```bash
   python -m venv .venv
   # Linux / macOS
   source .venv/bin/activate
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

3. **Install in editable mode with dev dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run the test suite** to confirm a clean baseline:
   ```bash
   pytest
   ```

## Creating a branch

Use a descriptive branch name that reflects the change. Suggested prefixes:

- `fix/` for bug fixes, e.g. `fix/docx-extraction-empty-paragraphs`
- `feat/` for new features, e.g. `feat/mistral-provider`
- `docs/` for documentation changes, e.g. `docs/configuration-azure-example`
- `refactor/` for internal restructuring with no behavior change

```bash
git checkout -b feat/my-change
```

## Making your change

1. **Keep the change focused.** One pull request should address one concern. Unrelated cleanups belong in separate PRs.
2. **Match the existing style.** Follow the patterns in the surrounding code. Reveilio avoids over-abstraction, so prefer a direct fix to a new helper.
3. **Add or update tests.** Every bug fix should include a regression test. Every new feature should include unit tests that exercise its public surface. Tests live in `tests/` and must not make real LLM calls; mock `json_completion` as the existing tests do.
4. **Update the documentation.** If you add a public function, class, argument, or environment variable, update the relevant HTML pages under `docs/` (Quickstart, Configuration, API reference, or Guides as appropriate).
5. **Do not introduce new runtime dependencies** without discussion. Added dependencies increase the install footprint and attack surface.

## Writing good commits

- Write imperative, present-tense subjects: "Add Mistral provider", not "Added" or "Adds".
- Keep the subject line at 72 characters or fewer.
- Explain *why* in the body, not just what changed.
- Reference related issues with `Fixes #123` or `Refs #123`.

## Running the tests and checks

Before opening a pull request, run the full test suite locally:

```bash
pytest -q
```

All tests must pass. If you add optional dependencies, include the install command in your PR description so reviewers can reproduce your environment.

## Opening a pull request

1. **Push your branch** to your fork:
   ```bash
   git push origin feat/my-change
   ```

2. **Open a pull request** against `main`.

3. **Fill out the PR template** with:
   - A short summary of the change.
   - The motivation or linked issue.
   - Any manual testing performed.
   - Screenshots for documentation or UI changes (if applicable).

4. **Request review** and respond to feedback promptly. Keep the discussion on the PR, not in private channels.

5. **Rebase, do not merge**, if `main` advances while your PR is open:
   ```bash
   git fetch origin
   git rebase origin/main
   git push --force-with-lease
   ```

## Review and merge

- A maintainer will review your PR and may request changes.
- All discussion threads must be resolved before merge.
- The continuous integration suite must be green.
- Pull requests are typically squash-merged to keep the main history linear.

## Reporting security issues

Please do not report security vulnerabilities through public GitHub issues. Instead, email the maintainers privately with a detailed description and, if possible, a proof of concept. You will receive an acknowledgement within a few working days.

## Code of conduct

By participating in this project, you agree to treat other contributors with respect. Be constructive in reviews, assume good intent, and keep discussion focused on the work.

> **Not sure where to start?** Look for issues tagged `good first issue` on GitHub, or open a discussion if you have an idea and are unsure whether it fits the project scope.
