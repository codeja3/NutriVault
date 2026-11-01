# Technical Specification (SPEC)

**Project Name:** NutriVault  
**Subtitle:** Local-First Personal and Family Nutrition Tracker  
**Status:** Approved & Locked  
**Version:** 1.1.0  

---

## 1. System Architecture Overview

NutriVault runs as a self-contained local backend service on the user's host workstation (macOS, Linux, or Windows) and serves an installable Progressive Web App (PWA) and REST API across the local area network via mDNS (`http://nutrivault.local:8080`, default bind `0.0.0.0:8080`).

To eliminate manual user setup, external daemons, and heavy container runtimes, multimodal vision inference is executed via an embedded `llama.cpp` (`llama-server`) child/sidecar process communicating strictly over a dedicated local loopback socket (`http://127.0.0.1:8081/v1/chat/completions`, configurable via `NUTRIVAULT_VLM_URL`).

```
 +-----------------------------------------------------------------------+
 | Local Area Network (mDNS: nutrivault.local:8080)                      |
 |                                                                       |
 |  [ Client PWA / REST Consumer (Mobile / Tablet / Desktop) ]           |
 |         │                                                             |
 |         │ Multipart Image Upload / REST API (JSON) (:8080)            |
 |         ▼                                                             |
 |  [ NutriVault Host Backend Daemon (ThreadingHTTPServer + API Lock) ]  |
 |    ├── Hardware Prober & Tier Gate (RAM, VRAM, Metal/CUDA/CPU)        |
 |    ├── Ephemeral Buffer Manager (In-memory BytesIO / 0x00 Purge)      |
 |    ├── Loopback VLM Client (127.0.0.1:8081 / SSRF Loopback Guard)     |
 |    ├── Grounding Engine (Cached USDA Token & Levenshtein Scorer)      |
 |    └── SQLite Storage Engine (WAL mode, Foreign Keys ON)              |
 |          ├── usda_reference.db (Attached as `usda` or `usda_reference`)|
 |          └── nutrivault.db     (Profiles, Envelopes, Ledgers, Dishes) |
 +-----------------------------------------------------------------------+
```

### 1.1 Concurrency & Thread-Safety Contract
* The HTTP daemon (`ThreadingHTTPServer`) serializes all database and state-mutating operations through a per-instance synchronization lock (`threading.Lock`) inside `NutriVaultAPI.handle_request` to prevent cross-thread SQLite transaction interleaving (`OperationalError` or unintended rollbacks).
* Loopback VLM endpoints are strictly validated against `{"127.0.0.1", "localhost", "::1"}` at client initialization to prevent Server-Side Request Forgery (SSRF) and guarantee Zero-WAN isolation.

---

## 2. Hardware Profiling & Cascading Model Selection Engine

Before loading or downloading model weights, the backend inspects host compute resources and enforces an upper tier ceiling to eliminate system thrashing and high latency on CPU-only machines.

### 2.1 Hardware Gates & Model Tiers

| Tier Name | Hardware Pre-requisites | Parameter Ceiling & Quantization | Target Vision Models |
| :--- | :--- | :--- | :--- |
| **`tier_1_cpu`** | CPU-only, or $<6\text{ GB}$ dedicated VRAM, or $<16\text{ GB}$ RAM | $\le 4\text{B}$ parameters, Q4 quantization | SmolVLM-500M/2B, MiniCPM-V 2.6 Q4, Moondream2 |
| **`tier_2_mid`** | Dedicated GPU with $\ge 6\text{ GB}$ VRAM, or Apple Silicon with $\ge 16\text{ GB}$ Unified Memory | $7\text{B}\text{--}9\text{B}$ parameters, Q4/Q8 quantization | Qwen2.5-VL 7B Q4, Gemma 4 VL 4B/8B |
| **`tier_3_high`** | Dedicated GPU with $\ge 16\text{ GB}$ VRAM, or Apple Silicon with $\ge 32\text{ GB}$ Unified Memory | $14\text{B}+$ parameters | Qwen2.5-VL 14B/72B Q4, Gemma 4 VL 26B/31B |

* **Enforcement Rule:** If an API client or config requests a model tier higher than the host's resolved tier ceiling, the system raises an explicit validation error (`ERR_HARDWARE_TIER_EXCEEDED`).

---

## 3. Database Schema (SQLite DDL) & Dual-Database Attachment

NutriVault supports both a unified in-memory/single-file SQLite schema (for hermetic testing and standalone use) and a dual-database deployment:
1. `usda_reference.db`: Static, indexed tables populated from USDA FoodData Central (Foundation Foods and SR Legacy). Attached at runtime via `attach_usda_reference(conn, usda_db_path, schema_name="usda")` using a strict static whitelist (`"usda"` or `"usda_reference"`) with zero dynamic SQL string interpolation.
2. `nutrivault.db`: Dynamic user state, household profiles, dietary targets, dishes, and event logs.
3. **Schema Resolution Rule:** When `usda` or `usda_reference` is attached and its `usda_foods` table is populated (while `main.usda_foods` is empty), `GroundingEngine` queries the attached schema (`usda.usda_foods` or `usda_reference.usda_foods`), preventing an empty `main.usda_foods` table from shadowing the external reference database.

### 3.1 Schema: `usda_reference.db`

```sql
CREATE TABLE IF NOT EXISTS usda_foods (
    fdc_id INTEGER PRIMARY KEY,                -- Official USDA FoodData Central ID
    description TEXT NOT NULL,                 -- e.g., 'Rice, brown, long-grain, cooked'
    food_category TEXT,                        -- e.g., 'Cereal Grains and Pasta'
    preparation_state TEXT NOT NULL DEFAULT 'unknown' CHECK (
        preparation_state IN ('cooked', 'raw', 'prepared', 'unknown')
    ),
    calories_per_100g REAL NOT NULL CHECK (calories_per_100g >= 0.0),
    protein_g_per_100g REAL NOT NULL CHECK (protein_g_per_100g >= 0.0),
    carbs_g_per_100g REAL NOT NULL CHECK (carbs_g_per_100g >= 0.0),
    fat_g_per_100g REAL NOT NULL CHECK (fat_g_per_100g >= 0.0),
    fiber_g_per_100g REAL NOT NULL CHECK (fiber_g_per_100g >= 0.0),
    -- Micronutrients per 100g stored as JSON map: {"iron_mg": 0.5, "potassium_mg": 86.0, ...}
    micros_per_100g_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_usda_foods_description ON usda_foods (description);
```

### 3.2 Schema: `nutrivault.db`

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- 1. Profiles Table
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,                       -- UUIDv4
    name TEXT NOT NULL,
    birth_date DATE,
    profile_type TEXT NOT NULL CHECK (
        profile_type IN ('standard', 'athletic', 'chronic_condition')
    ),
    condition_notes TEXT,                      -- e.g., 'Crohn's Disease (Remission)', 'Lupus'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Target Envelopes Table
CREATE TABLE IF NOT EXISTS target_envelopes (
    id TEXT PRIMARY KEY,                       -- UUIDv4
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    calories_target INTEGER NOT NULL CHECK (calories_target >= 0),
    protein_g_target REAL NOT NULL CHECK (protein_g_target >= 0.0),
    carbs_g_target REAL NOT NULL CHECK (carbs_g_target >= 0.0),
    fat_g_target REAL NOT NULL CHECK (fat_g_target >= 0.0),
    fiber_g_target REAL NOT NULL CHECK (fiber_g_target >= 0.0),
    -- Micronutrients stored as JSON map: {"nutrient_id_or_code": target_float}
    micronutrients_json TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Batches / Dishes Table (Cook-Once Shared Items)
CREATE TABLE IF NOT EXISTS dishes (
    id TEXT PRIMARY KEY,                       -- UUIDv4
    name TEXT NOT NULL,
    total_estimated_grams REAL NOT NULL CHECK (total_estimated_grams >= 0.0),
    total_calories REAL NOT NULL CHECK (total_calories >= 0.0),
    total_protein_g REAL NOT NULL CHECK (total_protein_g >= 0.0),
    total_carbs_g REAL NOT NULL CHECK (total_carbs_g >= 0.0),
    total_fat_g REAL NOT NULL CHECK (total_fat_g >= 0.0),
    total_fiber_g REAL NOT NULL CHECK (total_fiber_g >= 0.0),
    total_micros_json TEXT NOT NULL DEFAULT '{}',
    raw_ingredients_json TEXT NOT NULL,        -- Array of detected & matched ingredients
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Immutable Meal Event Journal
CREATE TABLE IF NOT EXISTS meal_logs (
    id TEXT PRIMARY KEY,                       -- UUIDv4
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    dish_id TEXT REFERENCES dishes(id) ON DELETE SET NULL,
    meal_type TEXT NOT NULL CHECK (
        meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'pre_workout', 'post_workout')
    ),
    portion_fraction REAL NOT NULL DEFAULT 1.0 CHECK (portion_fraction > 0.0 AND portion_fraction <= 1.0),
    calories REAL NOT NULL CHECK (calories >= 0.0),
    protein_g REAL NOT NULL CHECK (protein_g >= 0.0),
    carbs_g REAL NOT NULL CHECK (carbs_g >= 0.0),
    fat_g REAL NOT NULL CHECK (fat_g >= 0.0),
    fiber_g REAL NOT NULL CHECK (fiber_g >= 0.0),
    micros_json TEXT NOT NULL DEFAULT '{}',
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for Temporal Queries, Foreign Keys, and Single Active Envelope Invariant
CREATE INDEX IF NOT EXISTS idx_meal_logs_profile_time ON meal_logs (profile_id, logged_at);
CREATE INDEX IF NOT EXISTS idx_target_envelopes_profile ON target_envelopes (profile_id, is_active);
CREATE UNIQUE INDEX IF NOT EXISTS idx_single_active_envelope ON target_envelopes (profile_id) WHERE is_active = 1;
```

---

## 4. Ephemeral In-Memory Vision Pipeline & VLM Contract

### 4.1 Zero-Retention Memory Guarantee
1. **Pre-Allocation Boundary Check:** The HTTP layer inspects `Content-Length` before reading the request socket. Negative or non-numeric `Content-Length` headers are rejected with HTTP 400. Any payload exceeding `MAX_IMAGE_SIZE_BYTES` ($15\text{ MB} = 15,728,640\text{ bytes}$) is immediately rejected with HTTP 413 (`ERR_IMAGE_PAYLOAD_TOO_LARGE`) prior to reading the body into RAM.
2. **Multipart Extraction in Mutable Memory:** The client uploads the photo as `multipart/form-data` (or raw binary). The server extracts the binary image payload using mutable `bytearray` buffers and wraps it in `EphemeralImageBuffer` (`io.BytesIO`, max 15 MB), **never** touching `SpooledTemporaryFile`, disk files, or swap. Any intermediate `bytearray` buffers created during multipart boundary splitting are deterministically zeroed (`ba[:] = b"\x00" * len(ba)`) in `finally` blocks.
3. **Loopback Inference Dispatch:** The image is base64-encoded in RAM and sent over the local loopback interface to the embedded `llama.cpp` instance (`POST http://127.0.0.1:8081/v1/chat/completions`) with deterministic markdown code-fence stripping and outermost `[...]` JSON array extraction.
4. **Deterministic `0x00` Memory Purge:** Once the JSON response is parsed or an error is raised, `EphemeralImageBuffer.purge()` acquires the underlying `BytesIO` buffer via a context manager (`with self._stream.getbuffer() as buf:`), overwrites every byte in-place with `0x00` (`buf[:] = b"\x00" * len(buf)`), releases the `memoryview`, truncates (`truncate(0)`), closes the stream (`close()`), and invokes `gc.collect()`. All `getbuffer()` accesses (including `.size`) must use context management so no exported `memoryview` lock lingers.

### 4.2 Prompting & JSON Output Validation Contract
* **System Prompt:**
  ```text
  You are an ephemeral nutritional extraction engine.
  Examine the meal photograph. Identify each distinct edible component and estimate its mass in grams.
  Respond ONLY with a valid JSON array adhering strictly to this schema:
  [
    {"item_name": "plain descriptive food item", "estimated_grams": float}
  ]
  Never calculate calories, never emit markdown code fences, and never include commentary.
  ```
* **Expected Response Schema & Validation Rules:**
  ```json
  [
    {"item_name": "steamed edamame", "estimated_grams": 150.0},
    {"item_name": "cooked brown rice", "estimated_grams": 200.0},
    {"item_name": "tahini dressing", "estimated_grams": 30.0}
  ]
  ```
  * The parsed JSON must be a non-empty `list` (`len >= 1`).
  * Every element must contain a non-empty string `item_name` (`len(item_name.strip()) > 0`) and a strictly positive float `estimated_grams > 0.0`.
  * If the VLM emits malformed JSON, an empty list `[]`, a blank `item_name`, or `estimated_grams <= 0.0`, `VLMClient` retries once (`max_retries = 1`) before raising `VLMInvalidJSONError` (`ERR_VLM_INVALID_JSON`, HTTP 422).
  * If the loopback socket is unreachable or returns an HTTP transport error, `VLMClient` immediately raises `VLMUnavailableError` (`ERR_VLM_UNAVAILABLE`, HTTP 503).

---

## 5. Neuro-Symbolic Grounding, Batch Allocation & Arithmetic Engine

The VLM is strictly forbidden from outputting nutritional math. All calculations are executed deterministically against the USDA reference table.

1. **Entity Normalization, Caching & Preparation State Weighting:**
   * `GroundingEngine` caches tokenized USDA entries in memory (`CachedFoodEntry`) on first query (with explicit `invalidate_cache()` support).
   * Punctuation is stripped and tokens are lowercased. Normalized token-overlap ($0.7$ weight) and sequence similarity ($0.3$ weight) scores are computed against `usda_foods.description`.
   * State tokens (`cooked`, `steamed`, `roasted`, `boiled`, `fried`, `raw`, `prepared`, `baked`) receive a $1.5\times$ scoring multiplier, and queries without an explicit `raw` qualifier prefer `preparation_state` in prepared/cooked states to prevent raw-vs-cooked caloric density mismatches.
2. **Deterministic Linear Scaling & Rounding Precision:**
   $$\text{Nutrient}_{\text{actual}} = \text{Nutrient}_{\text{USDA per 100g}} \times \left( \frac{\text{estimated\_grams}}{100.0} \right)$$
   * `grams` must be $\ge 0.0$ (raises `ValueError` if negative).
   * **Precision Standard:** Grams, calories, and macronutrients (`protein_g`, `carbs_g`, `fat_g`, `fiber_g`) are rounded to **2 decimal places** (`round(val, 2)`). Micronutrients (`micros`) are rounded to **3 decimal places** (`round(val, 3)`) consistently across single-item scaling, batch dish aggregation, and fractional profile allocation.
3. **Atomic Batch Dish & Multi-Profile Allocation (`BatchDishAllocator.commit_meal`):**
   * Fractional allocations across family members must each satisfy $0.0 < \text{fraction} \le 1.0$ and their sum must satisfy $0.0 < \sum \text{fraction} \le 1.0$, otherwise `InvalidPortionSumError` (`ERR_INVALID_PORTION_SUM`, HTTP 400) is raised.
   * Dish creation (`dishes`) and all member journal entries (`meal_logs`) execute inside a single atomic SQLite transaction; any validation or constraint failure triggers a full `conn.rollback()`.

---

## 6. Advisory & Recommendation Contract

* **Clinical Hard Lock:** Any profile where `profile_type == 'chronic_condition'` blocks automated AI target generation on both `POST /api/v1/advisory/fitness-targets` and `PUT /api/v1/profiles/{id}/targets` (when `is_ai_generated == true`) with HTTP 403 (`ERR_CLINICAL_AI_RESTRICTED`) and presents the mandatory notice:
  > *"Nutritional goals for chronic conditions must be established in consultation with a qualified physician or registered dietitian. NutriVault does not provide clinical diagnoses or therapeutic prescriptions."*
* **Athletic & Fitness Recommendations:** For `profile_type == 'athletic'`, target estimations generated via local prompts must include the following advisory wire:
  > *"Local model fitness baselines are heuristic estimates. For rigorous training regimens or metabolic adjustments, consult a certified fitness trainer or cross-reference using privacy-preserving frontier endpoints (e.g., search.brave.com/ask)."*
  * Committing AI-generated targets (`is_ai_generated: true`) on an `athletic` profile via `PUT /api/v1/profiles/{id}/targets` requires explicit boolean client acknowledgment (`acknowledged: true`), otherwise HTTP 400 is returned.

---

## 7. REST API Interface & Schema Specification

| Endpoint | Method | Success Status | Request Payload | Response Body | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `/api/v1/hardware` | `GET` | `200` | None | `HardwareStatusResponse` | Returns detected compute specs and active model tier ceiling. |
| `/api/v1/profiles` | `GET` | `200` | None | `Array<Profile>` | Lists all household profiles ordered by `created_at ASC`. |
| `/api/v1/profiles` | `POST` | `201` | `ProfileCreateRequest` | `Profile` | Creates a household profile. |
| `/api/v1/profiles/{id}/targets` | `PUT` | `200` | `TargetEnvelopeRequest` | `TargetEnvelope` | Atomically updates active targets; enforces clinical & athletic safeguards. |
| `/api/v1/advisory/fitness-targets` | `POST` | `200` | `FitnessAdvisoryRequest` | `AthleticAdvisoryResponse` | Generates heuristic athletic macro targets with private frontier advisory. |
| `/api/v1/meals/parse-image` | `POST` | `200` | `multipart/form-data` (`image`) | `ParsedMealDraft` | In-memory VLM inference + USDA deterministic mapping + `0x00` purge. |
| `/api/v1/meals/commit` | `POST` | `201` | `MealCommitRequest` | `MealCommitResult` | Atomically commits dish and 1..N profile meal logs with portion fractions. |
| `/api/v1/analytics/rolling` | `GET` | `200` | `?profile_id={id}&days=7` | `RollingAnalyticsResponse` | Computes $N$-day EMA for calories, macros, target deltas, and eating/fasting windows. |

### 7.1 Request Payload Contracts (Pydantic Validation)
* **`ProfileCreateRequest`:**
  * `name`: non-empty string (`min_length=1`, stripped)
  * `profile_type`: `Literal["standard", "athletic", "chronic_condition"]`
  * `birth_date`: `str | None = None`
  * `condition_notes`: `str | None = None`
* **`TargetEnvelopeRequest`:**
  * `calories_target`: `int >= 0`
  * `protein_g_target`, `carbs_g_target`, `fat_g_target`, `fiber_g_target`: `float >= 0.0`
  * `micronutrients`: `dict[str, float] | None = None`
  * `is_ai_generated`: `bool = False`
  * `acknowledged`: `bool = False`
* **`FitnessAdvisoryRequest`:**
  * `profile_id`: non-empty string (`min_length=1`)
  * `athletic_goal`: `str = "general"`
  * `weight_kg`: `float > 0.0`
* **`MealCommitRequest`:**
  * `dish_name`: non-empty string (`min_length=1`, stripped)
  * `ingredients`: non-empty list (`min_length=1`) of `DishIngredientRequest` (`item_name` non-empty, `fdc_id: int`, `grams >= 0.0`, `calories >= 0.0`, `protein_g >= 0.0`, `carbs_g >= 0.0`, `fat_g >= 0.0`, `fiber_g >= 0.0`, `micros: dict[str, float]`)
  * `allocations`: non-empty list (`min_length=1`) of `ProfilePortionAllocationRequest` (`profile_id` non-empty, `fraction: float`, `meal_type: Literal["breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"] = "dinner"`, `logged_at: str | None = None` validated via `datetime.fromisoformat`)

### 7.2 Rolling Analytics & Chrononutrition Specification
* **Window Parameter (`days`):** Must be an integer $\ge 1$ (defaults to `7`). Values $< 1$ or non-integers raise `ValueError` (HTTP 400).
* **Rolling EMA Calculation:** Aggregates daily totals (`GROUP BY DATE(logged_at)`) for the **most recent $N$ logged days** (`ORDER BY meal_date DESC LIMIT ?`), re-orders them chronologically (`ORDER BY meal_date ASC`), and computes the exponential moving average with smoothing factor $k = \frac{2}{\text{len(series)} + 1}$.
* **Target Adherence Deltas:** When an active `TargetEnvelope` exists for `profile_id`, `target_deltas[metric] = round(metric_ema - target_metric, 2)`.
* **Chrononutrition Windows (`calculate_chrononutrition_windows`):**
  * Selects daily `MIN(logged_at)` (`first_meal_time`) and `MAX(logged_at)` (`last_meal_time`) for `profile_id` (bounded to the most recent `days` logged dates when `days` is provided, ordered chronologically `ASC`).
  * `eating_window_hours = round((last_dt - first_dt).total_seconds() / 3600.0, 2)`.
  * `overnight_fast_hours`: Computed **only** when the previous logged day and current logged day are strictly consecutive calendar days (`(first_dt.date() - prev_last_dt.date()).days == 1`) and `first_dt > prev_last_dt`; otherwise `None`.

---

## 8. Error Codes & HTTP State Responses

* **`ERR_HARDWARE_TIER_EXCEEDED` (HTTP 400):** Selected model tier exceeds host RAM/VRAM capacity.
* **`ERR_INVALID_PORTION_SUM` (HTTP 400):** Fractional allocations across family members are empty, contain an element $\le 0.0$ or $> 1.0$, or sum to $\le 0.0$ or $> 1.0$.
* **Validation / Schema / Integrity Error (HTTP 400):** Malformed JSON, Pydantic `ValidationError`, invalid query parameters (`days < 1`, missing `profile_id`), unacknowledged athletic AI target envelope, or `sqlite3.IntegrityError` (e.g., foreign key or `CHECK` constraint violation).
* **`ERR_CLINICAL_AI_RESTRICTED` (HTTP 403):** AI advisory generation or AI-generated target envelope commit requested for a profile with `profile_type == 'chronic_condition'`.
* **Resource / Route Not Found (HTTP 404):** Unknown endpoint path/method or non-existent `profile_id` (`KeyError`).
* **`ERR_IMAGE_PAYLOAD_TOO_LARGE` (HTTP 413):** Uploaded image `Content-Length` or buffer size exceeds the 15 MB volatile memory ceiling.
* **`ERR_VLM_INVALID_JSON` (HTTP 422):** Local VLM emitted non-conformant JSON, empty candidate list, blank `item_name`, or `estimated_grams <= 0.0` across initial attempt and 1 retry.
* **Internal Server Error (HTTP 500):** Unexpected runtime failure; returns sanitized `{"error": "Internal server error."}` without leaking stack traces or internal state.
* **`ERR_VLM_UNAVAILABLE` (HTTP 503):** Loopback inference engine (`127.0.0.1:8081`) failed to connect, timed out, or returned an HTTP transport error.
