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
* **Current Status:** 100% contract requirements fulfilled, all security and logic findings remediated, and verified across all 69 offline unit tests.