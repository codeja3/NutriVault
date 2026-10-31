# `AGENTS.md` — Project Standards & Autonomous Agent Directives

**Project:** NutriVault (Local-First Personal and Family Nutrition Tracker)  
**Architecture:** Unified Python 3.11+ Core & SQLite  
**Tooling Engine:** `uv`  
**Methodology:** Specification-Driven Development (SDD) & Strict Test-Driven Development (TDD)

---

## 1. Non-Negotiable Core Directives

1. **Specification Authority:** All implementation work is strictly bounded by `PRD.md` and `SPEC.md`.
   - Never implement uncontracted endpoints, schemas, parameters, or speculative abstractions.
   - If a missing requirement or architectural discrepancy is uncovered, halt coding, update the contract documents (`PRD.md` / `SPEC.md`), and resume from the updated specification.
2. **Strict Test-Driven Development (TDD):** Every feature, bug fix, or refactor follows the immutable **Red $\rightarrow$ Green $\rightarrow$ Refactor** sequence:
   - **RED:** Write an atomic test in `tests/` asserting the contract behavior, error boundaries, or return schemas. Execute `uv run pytest <test_file>` and verify the test fails for the expected reason (e.g., missing interface, assertion error).
   - **GREEN:** Write the minimal implementation in `src/` to make the test pass cleanly. Do not anticipate future requirements or write speculative features.
   - **REFACTOR:** Clean up code, remove duplication, and optimize data structures while ensuring 100% of the test suite remains green.
3. **Checklist Synchronization (`TODO.md`):** Keep `TODO.md` updated atomically. Never mark a task complete until its dedicated unit test passes without warnings.

---

## 2. Environment, Dependency & Toolchain Management

* **Python Runtime:** Python 3.11+ strictly.
* **Package Manager:** `uv` is the sole authorized package and environment manager.
  - Create virtual environment: `uv venv`
  - Activate virtual environment: `source .venv/bin/activate` (or platform equivalent)
  - Add runtime dependencies: `uv add <package>`
  - Add test/lint dependencies: `uv add --dev pytest pytest-mock pytest-asyncio ruff`
  - Run commands in environment: `uv run pytest` or `uv run ruff check .`
  - *Hard Rule:* Never use system Python, global `pip`, or unpinned global virtual environments.
* **Hermetic Sandbox Execution:**
  - Runtime caches (`.pytest_cache`, `__pycache__`) and local test artifacts must remain strictly scoped within the repository root or system temporary memory.
  - Zero modifications to system paths outside the project workspace.
* **Code Formatting & Linting:**
  - Automated formatting and linting via Ruff:
    ```bash
    uv run ruff check .
    uv run ruff format .
    ```

---

## 3. Testing Conventions & Hermetic Fixtures

* **Test Framework:** Standard `pytest`.
* **Zero WAN / Fully Hermetic Execution:**
  - All automated unit and contract tests **must execute completely offline**.
  - Zero live network requests, zero cloud API calls, and zero background daemon dependencies during test runs.
  - Mock external interaction layers (local inference sockets via `llama.cpp`, operating system hardware probing, network sockets) using deterministic fixtures via `pytest-mock`.
* **In-Memory SQLite Fixtures:**
  - All database unit tests must use in-memory SQLite instances to ensure speed and isolation:
    ```python
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    ```
  - Verify schema constraints, foreign key cascades, and check constraints explicitly in test assertions.
* **Ephemeral Memory Validation (Zero Disk Leakage):**
  - Tests validating image ingestion and candidate extraction must verify that images reside strictly in volatile memory (`io.BytesIO`) and leave zero lingering files in temp directories or persistent storage.

---

## 4. Coding Standards & Architectural Boundaries

* **Type Safety & Data Modeling:**
  - Standard Python 3.11+ type hints (`list[T]`, `dict[K, V]`, `X | None`).
  - Use `dataclasses` (with `frozen=True` where immutability is desired) or Pydantic models for request/response contract validation.
* **Database Access:**
  - Use standard library `sqlite3` exclusively with parameterized queries.
  - *Strict Ban:* Zero raw string interpolation, f-strings, or formatting in SQL statements to guarantee protection against SQL injection vulnerabilities.
* **Neuro-Symbolic Grounding & Math:**
  - The language/vision model is strictly an entity and portion extractor. It is never allowed to calculate calories, macronutrients, or micronutrients.
  - All nutritional calculations are computed deterministically via exact linear scaling against USDA tables:
    $$\text{Nutrient}_{\text{resolved}} = \text{Nutrient}_{\text{USDA}} \times \left( \frac{\text{grams}}{100.0} \right)$$
* **Advisory & Clinical Safeguards:**
  - Any request to generate automated AI nutritional goals for a profile with `profile_type == 'chronic_condition'` must raise an explicit domain error (`ClinicalAdvisoryViolationError` / HTTP 403).
  - Athletic goal prompts must always include the mandatory advisory wire citing certified trainers and privacy-preserving endpoints (`search.brave.com/ask`).

---

## 5. Standard Autonomous Agent Workflow

When executing tasks:

1. **Synchronize Context:** Inspect `PRD.md`, `SPEC.md`, `TODO.md`, and recent git status to establish the exact current phase.
2. **Verify Baseline:** Run `uv run pytest` to ensure all existing tests pass before touching code.
3. **Execute Next Task (RED):** Author the targeted unit test in `tests/test_*.py`. Run `uv run pytest <test_file>` to witness the expected failure.
4. **Implement Solution (GREEN):** Author the minimal Python code under `src/` to satisfy test assertions.
5. **Full Regression Check:** Run `uv run pytest` across the entire test suite.
6. **Lint & Clean:** Run `uv run ruff check .` and format cleanly.
7. **Update Checklist:** Mark the completed task in `TODO.md` and log key architectural decisions in `MEMORY.md`.