# `TODO.md` — Project Execution & TDD Phase Checklist

**Project:** NutriVault (Local-First Personal and Family Nutrition Tracker)  
**Execution Standard:** Strict Red $\rightarrow$ Green $\rightarrow$ Refactor. A task is checked `[x]` ONLY when all three stages (`[x] RED`, `[x] GREEN`, `[x] REFACTOR`) are verified and committed.

---

## Phase 1: Environment Setup & Hardware Profiling Engine

- [x] **Task 1.1: Virtual Environment & Core Scaffolding**
  - [x] `RED`: Create minimal test verifying project imports and environment integrity (`tests/test_env.py`).
  - [x] `GREEN`: Initialize `pyproject.toml` with `uv`, configure dependencies (`pytest`, `pytest-mock`, `ruff`).
  - [x] `REFACTOR`: Configure linting and format rules in `pyproject.toml`.

- [x] **Task 1.2: Hardware Probing & Resource Detection**
  - [x] `RED`: Author tests in `tests/test_hardware.py` asserting OS detection, RAM checks, and GPU backend discovery (Metal, CUDA, CPU fallback).
  - [x] `GREEN`: Implement `HardwareProfile` dataclass and probing logic in `src/hardware.py`.
  - [x] `REFACTOR`: Isolate OS-specific platform calls behind clean probe interfaces.

- [x] **Task 1.3: Cascading Model Tier Gating**
  - [x] `RED`: Author tests in `tests/test_hardware.py` asserting strict tier gating (`tier_1_cpu`, `tier_2_mid`, `tier_3_high`) and rejection of oversized model requests (`ERR_HARDWARE_TIER_EXCEEDED`).
  - [x] `GREEN`: Implement `resolve_model_tier()` and `validate_model_selection()` in `src/hardware.py`.
  - [x] `REFACTOR`: Clean up tier hierarchy maps and typing constants.

---

## Phase 2: Database Layer & Relational Schemas

- [x] **Task 2.1: SQLite Initialization & Constraints**
  - [x] `RED`: Author tests in `tests/test_db.py` verifying schema setup, `PRAGMA foreign_keys = ON`, `PRAGMA journal_mode = WAL`, and `CHECK` constraints.
  - [x] `GREEN`: Implement DDL schema execution in `src/db.py` for tables: `profiles`, `target_envelopes`, `dishes`, and `meal_logs`.
  - [x] `REFACTOR`: Organize migration and connection helper patterns into reusable context managers.

- [x] **Task 2.2: Profile & Target Envelope CRUD**
  - [x] `RED`: Author tests in `tests/test_db.py` asserting CRUD operations on `profiles` and active `target_envelopes`.
  - [x] `GREEN`: Implement profile and envelope database access routines in `src/db.py`.
  - [x] `REFACTOR`: Enforce strict typing models for database input payloads.

- [x] **Task 2.3: Clinical Hard Lock & Fitness Advisory Rules**
  - [x] `RED`: Author tests in `tests/test_advisory.py` asserting AI goal blocks on `chronic_condition` profiles (`ERR_CLINICAL_AI_RESTRICTED`) and required advisory wires referencing certified trainers and `search.brave.com/ask` on athletic targets.
  - [x] `GREEN`: Implement domain validation rules and advisory payload generator in `src/advisory.py`.
  - [x] `REFACTOR`: Unify disclaimer strings and error code mappings.

---

## Phase 3: Neuro-Symbolic Nutritional Grounding

- [x] **Task 3.1: Token Normalization & Fuzzy Token Overlap Engine**
  - [x] `RED`: Author tests in `tests/test_grounding.py` testing string normalization, token scoring, and candidate ranking against mock USDA reference rows.
  - [x] `GREEN`: Implement text normalization and matching algorithms in `src/grounding.py`.
  - [x] `REFACTOR`: Optimize scoring loops using cached token lookups.

- [x] **Task 3.2: Deterministic Linear Nutrient Scaling**
  - [x] `RED`: Author tests in `tests/test_grounding.py` asserting exact linear arithmetic: $\text{Nutrient} = \text{USDA}_{100\text{g}} \times (\text{grams} / 100.0)$, verifying no VLM hallucinations.
  - [x] `GREEN`: Implement pure deterministic math calculation engine in `src/grounding.py`.
  - [x] `REFACTOR`: Encapsulate macro and micronutrient aggregations into structured immutable objects.

---

## Phase 4: Ephemeral In-Memory Vision Pipeline

- [x] **Task 4.1: Volatile Memory Stream Management**
  - [x] `RED`: Author tests in `tests/test_vision_pipeline.py` asserting multipart image data remains strictly in `io.BytesIO` buffers with zero disk file leakage.
  - [x] `GREEN`: Implement in-memory stream receiver and memory buffer cleaner in `src/vision_pipeline.py`.
  - [x] `REFACTOR`: Ensure deterministic garbage collection/buffer clearing on both success and error branches.

- [x] **Task 4.2: Inference Client & Strict JSON Output Contract**
  - [x] `RED`: Author tests in `tests/test_vision_pipeline.py` asserting mocked loopback `/v1/chat/completions` parsing into `[{"item_name": str, "estimated_grams": float}]` and retry handling on malformed JSON.
  - [x] `GREEN`: Implement HTTP client wrapper communicating with local loopback `llama.cpp` instance in `src/vision_pipeline.py`.
  - [x] `REFACTOR`: Standardize timeout configurations and error state packaging.

---

## Phase 5: Family Batch Portion Allocator

- [x] **Task 5.1: Fractional Portion Validation & Dish Ledger**
  - [x] `RED`: Author tests in `tests/test_batch_allocator.py` asserting validation on batch dish splitting ($\sum \text{fraction} \le 1.0$) and rejection of invalid sums (`ERR_INVALID_PORTION_SUM`).
  - [x] `GREEN`: Implement dish persistence and fractional allocation calculation in `src/batch_allocator.py`.
  - [x] `REFACTOR`: Optimize atomic transaction blocks writing simultaneously to `dishes` and `meal_logs`.

- [x] **Task 5.2: Atomic Multi-Profile Journal Logging**
  - [x] `RED`: Author tests in `tests/test_batch_allocator.py` verifying atomic rollback if any individual profile ledger insertion fails during a split.
  - [x] `GREEN`: Implement transactional commit handling in `src/batch_allocator.py`.
  - [x] `REFACTOR`: Clean up relational queries and index utilization.

---

## Phase 6: Tabular Analytics Layer

- [x] **Task 6.1: Windowed Moving Averages (7-Day Rolling EMA)**
  - [x] `RED`: Author tests in `tests/test_analytics.py` asserting correct calculation of 7-day rolling calories, macros, and delta against active targets using historical fixtures.
  - [x] `GREEN`: Implement windowed SQL / analytical queries in `src/analytics.py`.
  - [x] `REFACTOR`: Ensure query plan uses `idx_meal_logs_profile_time` effectively.

- [ ] **Task 6.2: Temporal Eating Window Calculation**
  - [ ] `RED`: Author tests in `tests/test_analytics.py` asserting calculation of daily feeding intervals ($\Delta t = \text{Timestamp}_{\text{last}} - \text{Timestamp}_{\text{first}}$) and overnight fasts.
  - [ ] `GREEN`: Implement chrononutrition time-delta functions in `src/analytics.py`.
  - [ ] `REFACTOR`: Standardize timestamp handling to UTC ISO-8601 strings.

---

## Phase 7: Local HTTP / REST API Layer

- [ ] **Task 7.1: Core REST Endpoints (Hardware, Profiles, Targets, Advisory)**
  - [ ] `RED`: Author offline contract tests in `tests/test_api.py` asserting status codes, payloads, and error codes (`ERR_HARDWARE_TIER_EXCEEDED`, `ERR_CLINICAL_AI_RESTRICTED`) for `/api/v1/hardware`, `/api/v1/profiles`, `/api/v1/profiles/{id}/targets`, and `/api/v1/advisory/fitness-targets`.
  - [ ] `GREEN`: Implement REST request router and handlers in `src/api.py`.
  - [ ] `REFACTOR`: Standardize JSON serialization and domain exception-to-HTTP status mapping.

- [ ] **Task 7.2: Vision Ingestion, Batch Commit & Analytics Endpoints**
  - [ ] `RED`: Author offline contract tests in `tests/test_api.py` asserting zero-disk multipart parsing on `/api/v1/meals/parse-image`, fractional batch commits on `/api/v1/meals/commit` (`ERR_INVALID_PORTION_SUM`), and 7-day EMA + eating window responses on `/api/v1/analytics/rolling`.
  - [ ] `GREEN`: Wire vision pipeline, grounding engine, batch allocator, and analytics queries into `src/api.py`.
  - [ ] `REFACTOR`: Verify end-to-end memory cleanup and response schema conformance.