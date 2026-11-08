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

- [x] **Task 6.2: Temporal Eating Window Calculation**
  - [x] `RED`: Author tests in `tests/test_analytics.py` asserting calculation of daily feeding intervals ($\Delta t = \text{Timestamp}_{\text{last}} - \text{Timestamp}_{\text{first}}$) and overnight fasts.
  - [x] `GREEN`: Implement chrononutrition time-delta functions in `src/analytics.py`.
  - [x] `REFACTOR`: Standardize timestamp handling to UTC ISO-8601 strings.

---

## Phase 7: Local HTTP / REST API Layer

- [x] **Task 7.1: Core REST Endpoints (Hardware, Profiles, Targets, Advisory)**
  - [x] `RED`: Author offline contract tests in `tests/test_api.py` asserting status codes, payloads, and error codes (`ERR_HARDWARE_TIER_EXCEEDED`, `ERR_CLINICAL_AI_RESTRICTED`) for `/api/v1/hardware`, `/api/v1/profiles`, `/api/v1/profiles/{id}/targets`, and `/api/v1/advisory/fitness-targets`.
  - [x] `GREEN`: Implement REST request router and handlers in `src/api.py`.
  - [x] `REFACTOR`: Standardize JSON serialization and domain exception-to-HTTP status mapping.

- [x] **Task 7.2: Vision Ingestion, Batch Commit & Analytics Endpoints**
  - [x] `RED`: Author offline contract tests in `tests/test_api.py` asserting zero-disk multipart parsing on `/api/v1/meals/parse-image`, fractional batch commits on `/api/v1/meals/commit` (`ERR_INVALID_PORTION_SUM`), and 7-day EMA + eating window responses on `/api/v1/analytics/rolling`.
  - [x] `GREEN`: Wire vision pipeline, grounding engine, batch allocator, and analytics queries into `src/api.py`.
  - [x] `REFACTOR`: Verify end-to-end memory cleanup and response schema conformance.

---

## Phase 8: Security Hardening, Defect Remediation & Production Readiness

- [x] **Task 8.1: Memory Zeroing, SSRF Guard & Error Sanitization**
  - [x] `RED`: Author tests asserting EphemeralImageBuffer memoryview zeroing, VLMClient SSRF loopback validation, and sanitization of HTTP 500 responses.
  - [x] `GREEN`: Implement in-place volatile buffer overwrite, loopback host restriction in VLMClient, and generic 500 error responses in `src/vision_pipeline.py` and `src/api.py`.
  - [x] `REFACTOR`: Clean up buffer release safety and error handling patterns.

- [x] **Task 8.2: Target Validation, Pydantic Request Schemas & Non-Negative Constraints**
  - [x] `RED`: Author tests for athletic advisory acknowledgment enforcement, chronic condition target locks on PUT, non-negative nutrient/portion constraints, and request body validation returning 400.
  - [x] `GREEN`: Implement Pydantic request models in `src/api.py`, DDL schema CHECK constraints in `src/db.py`, and non-negative guards in `src/grounding.py`.
  - [x] `REFACTOR`: Ensure clean mapping of Pydantic validation errors to HTTP 400 responses.

- [x] **Task 8.3: Analytics EMA Windowing, Chrononutrition Gaps & VLM JSON Extraction**
  - [x] `RED`: Author tests asserting rolling EMA selects the most recent N days chronologically, chrononutrition flags non-consecutive day gaps, and clean_vlm_json_output handles nested JSON.
  - [x] `GREEN`: Implement DESC-then-ASC EMA subquery in `src/analytics.py`, calendar-day consecutive check in `calculate_chrononutrition_windows`, and robust bracket bounding in `clean_vlm_json_output`.
  - [x] `REFACTOR`: Verify performance and index utilization on analytical queries.

- [x] **Task 8.4: Atomic Meal Commit & Multipart Form Ingestion**
  - [x] `RED`: Author tests asserting atomic rollback across dishes and meal_logs on failure, and multipart/form-data boundary parsing.
  - [x] `GREEN`: Implement unified transaction in `BatchDishAllocator` / `NutriVaultAPI._handle_commit_meal` and multipart parser in `_handle_parse_image`.
  - [x] `REFACTOR`: Ensure zero disk writes during multipart parsing and clean rollback semantics.

- [x] **Task 8.5: GroundingEngine Cache, Dual-DB Attachment & HTTP Server CLI**
  - [x] `RED`: Author tests asserting GroundingEngine token cache speedup, database attachment helper in `src/db.py`, and HTTP server entrypoint.
  - [x] `GREEN`: Implement cached token sets in `GroundingEngine`, `attach_usda_reference` helper in `src/db.py`, and `ThreadingHTTPServer` CLI runner in `src/api.py`.
  - [x] `REFACTOR`: Verify `MANUAL.md` compatibility and run full test suite with Ruff lint/format.

---

## Phase 9: Expanded Review — Deep Security, Thread Safety & Robustness

- [x] **Task 9.1: Safe Database Attachment & Schema Shadowing Resolution**
  - [x] `RED`: Author tests verifying rejection of unsafe schema names in `attach_usda_reference`, and query resolution against `usda.usda_foods` when external reference is attached.
  - [x] `GREEN`: Restrict schema identifiers to validated alphanumeric tokens / hardcoded `"usda"`, and update `GroundingEngine` to query `usda.usda_foods` if attached and populated.
  - [x] `REFACTOR`: Preserve full backwards compatibility with unified in-memory reference tables.

- [x] **Task 9.2: Thread-Safe API Lock & Unbounded Payload Guard**
  - [x] `RED`: Author tests asserting concurrent request thread-safety via API lock, rejection of oversized Content-Length before read, and handling of malformed Content-Length headers.
  - [x] `GREEN`: Add `threading.Lock` around SQLite request dispatch in `NutriVaultAPI`, and enforce numeric/max-size checks in `NutriVaultHTTPHandler._dispatch`.
  - [x] `REFACTOR`: Ensure clean HTTP 413 and 400 status codes without handler crashes.

- [x] **Task 9.3: End-to-End Ephemeral Bytearray Zeroing**
  - [x] `RED`: Author test asserting mutable bytearray buffers in `_extract_image_bytes` and `_handle_parse_image` are zeroed in finally blocks.
  - [x] `GREEN`: Implement bytearray conversion and in-place zeroing across multipart extraction and request handling.
  - [x] `REFACTOR`: Ensure zero dangling heap slices on both success and error branches.

- [x] **Task 9.4: IntegrityError to 400 Mapping & Strict Literal Enums**
  - [x] `RED`: Author tests asserting `sqlite3.IntegrityError` returns HTTP 400 instead of HTTP 500, and Pydantic models reject invalid `profile_type` and `meal_type` strings.
  - [x] `GREEN`: Add `Literal` type constraints to `ProfileCreateRequest` and `ProfilePortionAllocationRequest`, and map `sqlite3.IntegrityError` to HTTP 400.
  - [x] `REFACTOR`: Unify database integrity error messaging.

- [x] **Task 9.5: VLM Non-Positive Gram Validation & Automatic Retry Trigger**
  - [x] `RED`: Author tests asserting VLM emitting `estimated_grams <= 0` triggers retry in `VLMClient.parse_meal_image` and raises `VLMInvalidJSONError` on repeated failure.
  - [x] `GREEN`: Validate `grams > 0.0` in `parse_meal_image` loop, raising `VLMInvalidJSONError` when non-positive.
  - [x] `REFACTOR`: Maintain clean retry logging and error boundaries.

- [x] **Task 9.6: Analytics Days Validation & Ingestion Timestamp Parsing**
  - [x] `RED`: Author tests asserting `days < 1` in rolling analytics returns HTTP 400, and malformed ISO-8601 timestamps in meal allocations are rejected upfront.
  - [x] `GREEN`: Validate `days >= 1` in `calculate_rolling_ema` / `handle_request`, and validate `datetime.fromisoformat` on allocation timestamps.
  - [x] `REFACTOR`: Standardize analytics query parameter validation.

- [x] **Task 9.7: BatchDishAllocator Logic Deduplication**
  - [x] `RED`: Verify complete test coverage for `create_dish`, `commit_batch_allocations`, and `commit_meal`.
  - [x] `GREEN`: Extract private `_build_dish`, `_insert_dish`, and `_insert_allocations` helpers to eliminate duplicated SQL and aggregation logic.
  - [x] `REFACTOR`: Format cleanly and run full 100% offline regression check.

---

## Phase 10: Specification Synchronization (v1.1.0) & Pass 3 Remediation

- [x] **Task 10.1: Dual-Schema USDA Resolution (`usda` & `usda_reference`)**
  - [x] `RED`: Author test in `tests/test_grounding.py` asserting `GroundingEngine` resolves `usda_reference.usda_foods` when attached as `usda_reference`.
  - [x] `GREEN`: Update `GroundingEngine._load_cache_if_needed` in `src/grounding.py` to support both `"usda"` and `"usda_reference"`.
  - [x] `REFACTOR`: Keep schema selection strictly static without SQL string formatting.

- [x] **Task 10.2: Loopback Port Separation (`:8081`), VLM Non-Empty Validation & Buffer Context Management**
  - [x] `RED`: Author tests in `tests/test_vision_pipeline.py` asserting default port `8081` (`http://127.0.0.1:8081/v1/chat/completions`), retry on empty array `[]` or blank `item_name`, and `bytearray` support in `EphemeralImageBuffer.from_bytes`.
  - [x] `GREEN`: Update `VLMClient` and `EphemeralImageBuffer` in `src/vision_pipeline.py` (using context-managed `with self._stream.getbuffer() as buf:`).
  - [x] `REFACTOR`: Synchronize `MANUAL.md` and `SPEC.md` with `:8081` loopback inference port.

- [x] **Task 10.3: Consistent 3-Decimal Micronutrient Precision in Batch Dishes**
  - [x] `RED`: Author test in `tests/test_batch_allocator.py` asserting trace micronutrient sums retain 3-decimal precision.
  - [x] `GREEN`: Update `BatchDishAllocator._build_dish` in `src/batch_allocator.py` to round `total_micros` to 3 decimal places.
  - [x] `REFACTOR`: Verify precision parity across `grounding.py` and `batch_allocator.py`.

- [x] **Task 10.4: Window-Bounded Chrononutrition Intervals (`days`)**
  - [x] `RED`: Author tests in `tests/test_analytics.py` and `tests/test_api.py` asserting `calculate_chrononutrition_windows` bounds results to the most recent `days` logged dates.
  - [x] `GREEN`: Add optional `days: int | None = None` parameter to `calculate_chrononutrition_windows` in `src/analytics.py` and pass `days=days` in `NutriVaultAPI._handle_get_analytics`.
  - [x] `REFACTOR`: Ensure chronological `ASC` ordering on bounded window subquery.

- [x] **Task 10.5: Non-Empty Request String/List Validation & Multipart Slice Zeroing**
  - [x] `RED`: Author tests in `tests/test_api.py` asserting empty/whitespace names or empty ingredient lists return HTTP 400.
  - [x] `GREEN`: Enforce `ConfigDict(str_strip_whitespace=True)` and `Field(min_length=1)` on Pydantic request models and zero intermediate `bytearray` slices in `_extract_image_bytearray`.
  - [x] `REFACTOR`: Run full 91-test offline regression suite and `ruff check` / `ruff format`.

---

## Phase 11: User-Friendly Onboarding, Built-In Web UI (PWA) & Turnkey Deployment

- [x] **Task 11.1: Curated USDA Starter Seed & Hardware Model Recommendations**
  - [x] `RED`: Author tests in `tests/test_db.py` and `tests/test_hardware.py` asserting `seed_default_usda_foods(conn)` idempotently seeds staple USDA foods when `usda_foods` is empty, `init_db(conn, seed_defaults=True)` triggers seeding, and `get_recommended_models(tier)` / `format_vlm_setup_guide(profile)` return tier-appropriate GGUF recommendations and `llama-server` commands.
  - [x] `GREEN`: Implement `DEFAULT_USDA_FOODS` and `seed_default_usda_foods()` in `src/db.py`, and implement `TIER_RECOMMENDED_MODELS`, `get_recommended_models()`, and `format_vlm_setup_guide()` in `src/hardware.py`.
  - [x] `REFACTOR`: Ensure all existing unit tests remain unaffected when `init_db(conn)` is called with default `seed_defaults=False`, while `run_server()` auto-seeds on startup.

- [x] **Task 11.2: Direct USDA Food Search & Scaling Endpoint (`GET /api/v1/foods/search`)**
  - [x] `RED`: Author tests in `tests/test_api.py` asserting `GET /api/v1/foods/search?q=brown+rice&grams=150&limit=5` returns ranked USDA items with deterministically scaled `NutrientProfile`, `GET /api/v1/hardware` includes `recommended_models`, and missing/blank `q` or invalid `grams`/`limit` return HTTP 400.
  - [x] `GREEN`: Implement `_handle_search_foods()` and update `_handle_get_hardware()` in `src/api.py`.
  - [x] `REFACTOR`: Validate query parameter bounds and verify `< 50 ms` cached search execution.

- [x] **Task 11.3: Built-In Zero-Build Progressive Web App (`GET /` & `GET /manifest.json`)**
  - [x] `RED`: Author tests in `tests/test_api.py` asserting `GET /` returns `200 OK` with `text/html; charset=utf-8` containing the interactive NutriVault PWA UI (with zero external CDN URLs) and `GET /manifest.json` returns `200 OK` with `application/manifest+json`.
  - [x] `GREEN`: Create `src/ui.py` housing the self-contained HTML5/CSS3/ES6 PWA and manifest, and wire `GET /` and `GET /manifest.json` into `NutriVaultAPI` and `NutriVaultHTTPHandler` in `src/api.py`.
  - [x] `REFACTOR`: Verify all core workflows (profile switcher, clinical/athletic advisory banners, USDA instant search, photo upload, family batch portion sliders, and 7-day EMA dashboard) are wired cleanly in the UI.

- [x] **Task 11.4: Turnkey Docker Compose & CLI VLM Setup Guide (`--vlm-guide`)**
  - [x] `RED`: Author tests in `tests/test_env.py` and `tests/test_api.py` asserting `Dockerfile` and `docker-compose.yml` exist with valid port `8080` and `/app/data` volume configuration, and `python -m src.api --vlm-guide` outputs the hardware-matched setup guide and exits with code `0`.
  - [x] `GREEN`: Create `Dockerfile`, `.dockerignore`, and `docker-compose.yml` in repository root, and add `--vlm-guide` CLI handling in `src/api.py`.
  - [x] `REFACTOR`: Ensure container runs as non-root user and persists SQLite WAL files cleanly.

- [x] **Task 11.5: Documentation & End-to-End Onboarding Synchronization**
  - [x] `RED`: Review `README.md`, `MANUAL.md`, and `MEMORY.md` against `PRD.md` v1.2.0 and `SPEC.md` v1.2.0.
  - [x] `GREEN`: Update `README.md` and `MANUAL.md` with 60-second browser UI quickstart, `docker compose up` instructions, `GET /api/v1/foods/search` documentation, and `--vlm-guide` usage; log Phase 11 in `MEMORY.md`.
  - [x] `REFACTOR`: Run full offline pytest suite and `ruff check` / `ruff format`.

---

## Phase 12: One-Stop-Shop Predefined VLM Catalog, Offline-First "Snap & Sync Later" PWA & 3-Tier Barcode Scanner

- [x] **Task 12.1: Predefined Tier-Matched VLM Catalog & Zero-Download-Hunt Command Builder**
  - [x] `RED`: Author tests in `tests/test_hardware.py` asserting `PredefinedVLMModel`, `PREDEFINED_VLM_CATALOG` (mapping `tier_1_cpu` $\rightarrow$ `SmolVLM-500M-Instruct-Q8_0`, `tier_2_mid` $\rightarrow$ `Qwen2.5-VL-3B-Instruct-Q4_K_M`, `tier_3_high` $\rightarrow$ `Qwen2.5-VL-7B-Instruct-Q4_K_M`), `get_default_vlm_spec(tier)`, and `build_managed_vlm_command(tier)` emitting `llama-server --hf-repo ... --hf-file ...`.
  - [x] `GREEN`: Implement `PredefinedVLMModel`, `PREDEFINED_VLM_CATALOG`, `get_default_vlm_spec()`, and `build_managed_vlm_command()` in `src/hardware.py`, and expose `default_vlm` and `managed_vlm_command` in `GET /api/v1/hardware` (`src/api.py`).
  - [x] `REFACTOR`: Update `format_vlm_setup_guide()` to include the predefined `--hf-repo` command and approximate download size.

- [x] **Task 12.2: SQLite `barcode` Schema Migration, Seeded Staple Barcodes & Grounding Barcode Engine**
  - [x] `RED`: Author tests in `tests/test_db.py` and `tests/test_grounding.py` asserting idempotent `usda_foods.barcode` column creation/migration, `idx_usda_foods_barcode` index, seeded UPC/EAN barcodes in `DEFAULT_USDA_FOODS`, `normalize_barcode()`, `lookup_barcode()`, `register_barcode()`, and `export_offline_catalog()`.
  - [x] `GREEN`: Update `src/db.py` (`usda_foods` DDL, idempotent `ALTER TABLE` check in `init_db`, barcodes in `DEFAULT_USDA_FOODS`) and `src/grounding.py` (`normalize_barcode`, `lookup_barcode`, `register_barcode`, `export_offline_catalog`, and `BarcodeNotFoundError`).
  - [x] `REFACTOR`: Ensure `GroundingEngine` cache invalidates cleanly on `register_barcode()` and supports attached `usda`/`usda_reference` schemas.

- [x] **Task 12.3: Barcode Lookup, Custom Barcode Registration & Offline Batch Sync API Endpoints**
  - [x] `RED`: Author offline contract tests in `tests/test_api.py` asserting:
    - `GET /api/v1/foods/catalog` returns the full local food & barcode catalog for client IndexedDB caching.
    - `GET /api/v1/foods/barcode/{code}?grams=150` returns scaled nutrients (`200 OK`), `404 ERR_BARCODE_NOT_FOUND` on unknown barcode, and `400` on invalid barcode/grams.
    - `PUT /api/v1/foods/barcode/{code}` registers/updates a custom barcode in `usda_foods` (`200 OK`) and makes subsequent `GET /api/v1/foods/barcode/{code}` hits succeed immediately.
    - `POST /api/v1/sync/batch` processes offline-queued meals (`queued_meals`) and deferred offline barcode scans (`queued_barcodes`) preserving original `logged_at` timestamps, while returning any unrecognized barcodes in `unresolved_barcodes` without failing valid items in the batch.
  - [x] `GREEN`: Implement Pydantic models (`BarcodeRegisterRequest`, `QueuedBarcodeItemRequest`, `OfflineSyncBatchRequest`) and route handlers (`_handle_get_catalog`, `_handle_get_barcode`, `_handle_put_barcode`, `_handle_sync_batch`) in `src/api.py`.
  - [x] `REFACTOR`: Verify thread-safe locking and clean HTTP error mapping across all new routes.

- [ ] **Task 12.4: Offline-First PWA Service Worker (`GET /sw.js`), IndexedDB Queue & In-Browser Camera Barcode Scanner (`src/ui.py`)**
  - [ ] `RED`: Author tests in `tests/test_api.py` asserting `GET /sw.js` returns `200 OK` with `application/javascript; charset=utf-8` (and zero external URLs), and `GET /` includes the offline IndexedDB queue (`nutrivault_offline_db`), Service Worker registration, "Snap & Sync Later" offline queue controls, and in-browser `BarcodeDetector` scanner + Tier-3 custom barcode registration UI.
  - [ ] `GREEN`: Implement `GET_PWA_SERVICE_WORKER()` and update `GET_PWA_HTML()` in `src/ui.py`, and wire `GET /sw.js` in `src/api.py`.
  - [ ] `REFACTOR`: Ensure strict DOM XSS escaping (`escapeHtml`) and zero external CDN references across `src/ui.py`.

- [ ] **Task 12.5: Turnkey One-Stop `docker-compose.yml` with Preconfigured `SmolVLM-500M` Sidecar & Optional P2P Remote Profile**
  - [ ] `RED`: Author tests in `tests/test_env.py` asserting `docker-compose.yml` defines the `nutrivault-vlm` service preconfigured with `SmolVLM-500M-Instruct-Q8_0` and the optional `remote` profile for away-from-home P2P access.
  - [ ] `GREEN`: Update `docker-compose.yml` with the preconfigured `nutrivault-vlm` sidecar (`--hf-repo ggml-org/SmolVLM-500M-Instruct-GGUF`) and optional `nutrivault-remote` Tailscale sidecar profile.
  - [ ] `REFACTOR`: Verify environment variable wiring (`NUTRIVAULT_VLM_URL`) and volume mounts.

- [ ] **Task 12.6: Role-Separated Documentation Overhaul (`README.md`, `MANUAL.md` for Average Users, `DEV_MANUAL.md` for Developers)**
  - [ ] `RED`: Audit `README.md` and `MANUAL.md` to identify all developer-only instructions (`uv`, `git` cloning/branching, pytest, SQLite DDL, raw `curl` payloads) that belong in `DEV_MANUAL.md`.
  - [ ] `GREEN`: Create `DEV_MANUAL.md` with complete technical/developer documentation, rewrite `MANUAL.md` as a jargon-free end-user manual (covering 1-click launch, phone PWA installation, offline "Snap & Sync Later" restaurant/travel mode, and 3-tier grocery barcode scanning), and update `README.md` and `MEMORY.md`.
  - [ ] `REFACTOR`: Run full offline `uv run pytest` and `uv run ruff check .` / `uv run ruff format --check .` to verify 100% green status.




