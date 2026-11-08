# `MEMORY.md` — Project Memory & Active Decision Log

**Project:** NutriVault  
**Last Updated:** Phase 1 Initialization  

---

## 1. Architectural Decisions & Rationale

* **Unified Python Core & SQLite Stack:**
  * *Decision:* Build the core application entirely in Python 3.11+ using standard library `sqlite3` and `uv`, rejecting a split Go/Python runtime for Phase 1.
  * *Rationale:* Keeps the codebase unified for rapid algorithmic data science and TDD prototyping, avoiding cross-language interface overhead while retaining desktop packagability (via Briefcase/Tauri).
* **Embedded `llama.cpp` over Ollama/vLLM:**
  * *Decision:* Rely on embedded `llama.cpp` (`llama-server`) running over a local loopback socket.
  * *Rationale:* Containerized runtimes (vLLM) break macOS Metal GPU passthrough and require heavy virtualization; external daemons (Ollama) add multi-step user installation friction.
* **Neuro-Symbolic Nutritional Pipeline:**
  * *Decision:* The VLM is strictly an entity and portion extractor. All calorie and nutrient math is deterministically calculated via local USDA tables.
  * *Rationale:* Eliminates arithmetic hallucination inherent to generative language models.
* **Zero-Retention Ephemeral Media:**
  * *Decision:* Images reside strictly in volatile memory (`io.BytesIO`) during parsing and are cleared immediately upon commit or failure.
  * *Rationale:* Guarantees verifiably strict data privacy and eliminates local storage bloat.
* **Tiered Health & Fitness Advisories:**
  * *Decision:* Profiles marked `chronic_condition` have automated AI goal generation strictly locked (`ERR_CLINICAL_AI_RESTRICTED`). Athletic goal generation is permitted but must explicitly bundle a disclaimer citing certified trainers and privacy-preserving endpoints (`search.brave.com/ask`).
  * *Rationale:* Protects user health in clinical conditions where diet correlates directly with clinical outcomes while providing an open, private path for fitness goals.

---

## 2. Technical Contracts & Invariants

* **Tooling Standard:** `uv` is the sole authorized environment manager. All commands must run through `uv run`.
* **Testing Standard:** 100% offline unit execution. External systems (hardware APIs, loopback HTTP inference) must use deterministic mocks.
* **Database State:** SQLite operating in WAL mode (`PRAGMA journal_mode = WAL;`) with foreign keys strictly enforced (`PRAGMA foreign_keys = ON;`). Parameterized queries only.
* **Hardware Tier Boundaries:**
  * `tier_1_cpu`: CPU-only, $<6\text{ GB}$ dedicated VRAM, or $<16\text{ GB}$ RAM $\rightarrow \le 4\text{B}$ quantized models (SmolVLM, MiniCPM-V, Moondream2).
  * `tier_2_mid`: $\ge 6\text{ GB}$ dedicated VRAM or Apple Silicon $\ge 16\text{ GB}$ Unified Memory $\rightarrow 7\text{B}\text{--}9\text{B}$ models (Qwen2.5-VL 7B Q4).
  * `tier_3_high`: $\ge 16\text{ GB}$ dedicated VRAM or Apple Silicon $\ge 32\text{ GB}$ Unified Memory $\rightarrow 14\text{B}+$ models.
* **Single Active Target Envelope Invariant:** Enforced at the SQLite level via partial unique index `idx_single_active_envelope ON target_envelopes(profile_id) WHERE is_active = 1`.
* **Cooked-First USDA Grounding:** Token scoring in `usda_reference.db` applies a $1.5\times$ weight to preparation state tokens (`cooked`, `raw`, `steamed`, etc.) and defaults to `cooked`/`prepared` when unspecified to avoid $3\times$ caloric density errors on grains and legumes.

---

## 3. Current Phase Status

* **Active Phase:** Phase 3 (Neuro-Symbolic Nutritional Grounding).
* **Active Phase:** All Phases Complete (1.1 through 7.2).
* **Completed Tasks:**
  * Task 1.1: Virtual environment initialized with `uv`, `pyproject.toml` created with strict Python 3.11+ configuration, `pytest`, `pytest-mock`, `pytest-asyncio`, and `ruff` installed, `src/__init__.py` exposing version 1.0.0.
  * Task 1.2: Hardware probing implemented in `src/hardware.py` (`HardwareProfile`, `AcceleratorType`, OS, RAM, Apple Silicon, CUDA, and CPU fallback detection) with 100% offline unit test coverage in `tests/test_hardware.py`.
  * Task 1.3: Cascading model tier gating implemented in `src/hardware.py` (`HardwareTier`, `resolve_model_tier`, `validate_model_selection`, `HardwareTierExceededError` with `ERR_HARDWARE_TIER_EXCEEDED`).
  * Task 2.1: SQLite initialization and DDL constraints implemented in `src/db.py` (`PRAGMA foreign_keys = ON`, `WAL` mode, partial unique index `idx_single_active_envelope`, cascade deletes, CHECK constraints for `profile_type` and `portion_fraction`) with 100% offline unit test coverage in `tests/test_db.py`.
  * Task 2.2: Profile & target envelope repository implemented in `src/db.py` (`Profile`, `TargetEnvelope`, `ProfileRepository` with atomic active envelope replacement and zero string formatting) with 100% offline unit test coverage in `tests/test_db.py`.
  * Task 2.3: Clinical advisory safeguards implemented in `src/advisory.py` (`ClinicalAdvisoryViolationError` with `ERR_CLINICAL_AI_RESTRICTED`, mandatory clinical disclaimer for chronic conditions, heuristic athletic target generation bundled with privacy-preserving advisory wire citing certified trainers and `search.brave.com/ask`) with 100% offline unit test coverage in `tests/test_advisory.py`.
  * Task 3.1: Token normalization, fuzzy token overlap, and cooked-first state-weighted grounding engine implemented in `src/grounding.py` (`normalize_food_text`, `GroundingMatch`, `GroundingEngine`) with 100% offline unit test coverage in `tests/test_grounding.py`.
  * Task 3.2: Deterministic linear nutrient scaling implemented in `src/grounding.py` (`NutrientProfile`, `ResolvedFoodItem`, `calculate_linear_nutrients`, `resolve_food_item`) with 100% offline unit test coverage in `tests/test_grounding.py`.
  * Task 4.1: Volatile memory stream manager and zero-disk purge lifecycle implemented in `src/vision_pipeline.py` (`EphemeralImageBuffer`, `ImagePayloadTooLargeError`, bounded 15MB ram ceiling) with 100% offline unit test coverage in `tests/test_vision_pipeline.py`.
  * Task 4.2: Inference client and strict JSON output parsing implemented in `src/vision_pipeline.py` (`VLMClient`, `ExtractedCandidateItem`, `clean_vlm_json_output`, `VLMInvalidJSONError`, `VLMUnavailableError`, 1-retry handling) with 100% offline unit test coverage in `tests/test_vision_pipeline.py`.
  * Task 5.1: Batch dish ledger and fractional portion validation implemented in `src/batch_allocator.py` (`BatchDish`, `DishIngredient`, `ProfilePortionAllocation`, `BatchDishAllocator`, `InvalidPortionSumError` with `ERR_INVALID_PORTION_SUM`) with 100% offline unit test coverage in `tests/test_batch_allocator.py`.
  * Task 5.2: Atomic multi-profile journal logging with full transaction rollback protection implemented in `src/batch_allocator.py` (`commit_batch_allocations`) with 100% offline unit test coverage in `tests/test_batch_allocator.py`.
  * Task 6.1: Windowed moving averages and target adherence deltas implemented in `src/analytics.py` (`RollingEMAResult`, `AnalyticsEngine.calculate_rolling_ema`) with 100% offline unit test coverage in `tests/test_analytics.py`.
  * Task 6.2: Chrononutrition temporal eating window and overnight fasting intervals implemented in `src/analytics.py` (`DailyFeedingInterval`, `calculate_chrononutrition_windows`) with 100% offline unit test coverage in `tests/test_analytics.py`.
  * Task 7.1: Core REST API endpoints implemented in `src/api.py` (`NutriVaultAPI` handling `/api/v1/hardware`, `/api/v1/profiles`, `/api/v1/profiles/{id}/targets`, and `/api/v1/advisory/fitness-targets` with exception mapping) with 100% offline unit test coverage in `tests/test_api.py`.
  * Task 7.2: End-to-end vision parsing, batch commits, and rolling analytics REST endpoints wired into `src/api.py` (`/api/v1/meals/parse-image`, `/api/v1/meals/commit`, `/api/v1/analytics/rolling`) with 100% offline unit test coverage in `tests/test_api.py`.
  * Task 8.1: Security & privacy hardening implemented (`EphemeralImageBuffer.purge()` in-place `0x00` buffer overwrite, `VLMClient` loopback SSRF guard, generic HTTP 500 error sanitization).
  * Task 8.2: Target validation, Pydantic request models (`ProfileCreateRequest`, `TargetEnvelopeRequest`, `FitnessAdvisoryRequest`, `MealCommitRequest`), non-negative DDL CHECK constraints on `target_envelopes`, `dishes`, and `meal_logs`, and non-negative portion weight enforcement.
  * Task 8.3: Analytics rolling 7-day EMA subquery windowing (selecting most recent 7 days chronologically), consecutive-day overnight fast validation in chrononutrition windows, and robust bracket matching in `clean_vlm_json_output`.
  * Task 8.4: Atomic multi-table batch meal persistence (`BatchDishAllocator.commit_meal`) preventing orphaned `dishes`, and in-memory multipart boundary decoding in `NutriVaultAPI._handle_parse_image`.
  * Task 8.5: `GroundingEngine` in-memory token caching (`CachedFoodEntry`), dual-database schema attachment (`attach_usda_reference`), and `ThreadingHTTPServer` daemon runner in `src/api.py` honoring `MANUAL.md`.
  * Task 9.1: Safe database attachment rejecting dynamic f-strings in `attach_usda_reference`, and schema shadowing resolution in `GroundingEngine` (querying `usda.usda_foods` when external reference is attached and main reference is empty).
  * Task 9.2: Thread-safe API lock (`threading.Lock` in `NutriVaultAPI`) protecting SQLite connection across concurrent HTTP requests, and Content-Length guards rejecting malformed headers (HTTP 400) or payloads > 15 MB (HTTP 413) prior to reading payload bytes.
  * Task 9.3: End-to-end ephemeral bytearray memory zeroing across multipart extraction and request handling in `src/api.py`.
  * Task 9.4: Mapping `sqlite3.IntegrityError` to HTTP 400 Bad Request, and enforcing strict `Literal` enums on `ProfileCreateRequest.profile_type` and `ProfilePortionAllocationRequest.meal_type`.
  * Task 9.5: VLM candidate validation requiring `estimated_grams > 0.0`, triggering automated retry and raising `VLMInvalidJSONError` on repeated failure.
  * Task 9.6: Rolling analytics query validation rejecting `days < 1` with HTTP 400, and upfront ISO-8601 validation for allocation timestamps (`logged_at`).
  * Task 9.7: Refactoring and deduplicating dish building, insertion, and allocation loops in `BatchDishAllocator` (`_build_dish`, `_insert_dish`, `_insert_allocations`).
  * Task 10.1–10.5: Updated `SPEC.md` to v1.1.0 and remediated all Pass 3 findings: dual-schema USDA resolution (`usda` and `usda_reference`), dedicated loopback VLM port `8081` (`http://127.0.0.1:8081/v1/chat/completions`) preventing `:8080` daemon collision, context-managed `getbuffer()` in `EphemeralImageBuffer`, VLM retry on empty candidate array `[]` or blank `item_name`, 3-decimal micronutrient precision in `BatchDishAllocator._build_dish`, `days`-bounded `calculate_chrononutrition_windows`, and non-empty string/list Pydantic constraints (`min_length=1` with `str_strip_whitespace=True`).
  * Task 11.1–11.5: Transitioned NutriVault to full user-friendly operation (`PRD.md` v1.2.0 & `SPEC.md` v1.2.0):
    * Implemented curated starter catalog (`DEFAULT_USDA_FOODS`, 30 staple foods) in `src/db.py` seeded idempotently on startup (`seed_default_usda_foods`).
    * Implemented hardware-tailored model recommendations (`get_recommended_models`) and CLI guide generator (`format_vlm_setup_guide`) in `src/hardware.py`.
    * Implemented instant USDA search and deterministic linear scaling endpoint (`GET /api/v1/foods/search`) in `src/api.py`.
    * Implemented zero-build Progressive Web App (`src/ui.py`) serving responsive HTML5/CSS3/ES6 interface at `GET /` and web manifest at `GET /manifest.json` with zero external CDN dependencies.
    * Implemented turnkey containerization (`Dockerfile`, `docker-compose.yml`, `.dockerignore`) with non-root user and persistent `/app/data` volume.
    * Added `--vlm-guide` CLI flag in `src/api.py` for automated hardware probing and `llama-server` guidance.
* **Current Status:** 100% contract requirements fulfilled, `PRD.md` v1.3.0 and `SPEC.md` v1.3.0 locked, Phase 12 complete, and verified across all 120 offline unit tests with clean Ruff lint and format.
  * Task 12.1–12.6: Completed Phase 12 (One-Stop-Shop Predefined VLM Catalog, Offline-First "Snap & Sync Later" PWA & 3-Tier Barcode Scanner):
    * **Task 12.1:** Implemented `PredefinedVLMModel` catalog (`SmolVLM-500M-Instruct-Q8_0` for CPU, `Qwen2.5-VL-3B-Instruct-Q4_K_M` for mid-tier, `Qwen2.5-VL-7B-Instruct-Q4_K_M` for high-tier), `build_managed_vlm_command()`, and exposed in `GET /api/v1/hardware`.
    * **Task 12.2:** Added `barcode` column and index to `usda_foods`, auto-migrated legacy databases in `init_db()`, seeded staple barcodes in `DEFAULT_USDA_FOODS`, and implemented `normalize_barcode()`, `lookup_barcode()`, `register_barcode()`, and `export_offline_catalog()` in `src/grounding.py`.
    * **Task 12.3:** Implemented `GET /api/v1/foods/catalog`, `GET /api/v1/foods/barcode/{code}`, `PUT /api/v1/foods/barcode/{code}`, and `POST /api/v1/sync/batch` in `src/api.py` with `BarcodeNotFoundError` (HTTP 404), portion scaling, and atomic preservation of client `logged_at` timestamps.
    * **Task 12.4:** Implemented offline-first PWA Service Worker (`GET /sw.js`), IndexedDB (`nutrivault_offline_db` caching `offline_foods_cache` and `offline_sync_queue`), live connection banner, camera barcode scanner (`window.BarcodeDetector`), and 1-tap custom barcode modal in `src/ui.py`.
    * **Task 12.5:** Preconfigured turnkey `SmolVLM-500M` sidecar (`ghcr.io/ggerganov/llama.cpp:server`) and optional P2P remote profile in `docker-compose.yml`.
    * **Task 12.6:** Conducted role-separated documentation overhaul: created comprehensive `DEV_MANUAL.md` for developers, rewritten `MANUAL.md` as a 100% jargon-free user guide, and updated `README.md` and `MEMORY.md`.
