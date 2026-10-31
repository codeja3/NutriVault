# Technical Specification (SPEC)

**Project Name:** NutriVault  
**Subtitle:** Local-First Personal and Family Nutrition Tracker  
**Status:** Approved & Locked  
**Version:** 1.0.0  

---

## 1. System Architecture Overview

NutriVault runs as a self-contained local backend service on the user's host workstation (macOS, Linux, or Windows) and serves an installable Progressive Web App (PWA) across the local area network via mDNS (`http://nutrivault.local:8080`).

To eliminate manual user setup, external daemons, and heavy container runtimes, inference is executed via an embedded `llama.cpp` (`llama-server`) child process or direct C-bindings communicating strictly over a local loopback socket.

```
 +-----------------------------------------------------------------------+
 | Local Area Network (mDNS: nutrivault.local:8080)                      |
 |                                                                       |
 |  [ Client PWA (Mobile / Tablet / Desktop) ]                           |
 |         │                                                             |
 |         │ Multipart Image Upload / REST API (JSON)                    |
 |         ▼                                                             |
 |  [ NutriVault Host Backend Daemon ]                                   |
 |    ├── Hardware Prober & Tier Gate (RAM, VRAM, Metal/CUDA/CPU)        |
 |    ├── Ephemeral Buffer Manager (In-memory BytesIO / Zero-Disk)       |
 |    ├── Embedded Inference Runner (llama.cpp / loopback REST)          |
 |    ├── Grounding Engine (USDA Token Overlap & Levenshtein Scorer)     |
 |    └── SQLite Storage Engine (WAL mode, Foreign Keys ON)              |
 |          ├── usda_reference.db (Static Read-Only Reference)           |
 |          └── nutrivault.db     (Profiles, Envelopes, Ledgers, Dishes) |
 +-----------------------------------------------------------------------+
```

---

## 2. Hardware Profiling & Cascading Model Selection Engine

Before loading or downloading model weights, the backend inspects host compute resources and enforces an upper tier ceiling to eliminate system thrashing and high latency on CPU-only machines.

### 2.1 Hardware Gates & Model Tiers

| Tier Name | Hardware Pre-requisites | Parameter Ceiling & Quantization | Target Vision Models |
| :--- | :--- | :--- | :--- |
| **`tier_1_cpu`** | CPU-only, or $<6\text{ GB}$ dedicated VRAM, or $<16\text{ GB}$ RAM | $\le 4\text{B}$ parameters, Q4 quantization | SmolVLM-500M/2B, MiniCPM-V 2.6 Q4, Moondream2 |
| **`tier_2_mid`** | Dedicated GPU with $\ge 6\text{ GB}$ VRAM, or Apple Silicon with $\ge 16\text{ GB}$ Unified Memory | $7\text{B}\text{--}9\text{B}$ parameters, Q4/Q8 quantization | Qwen2.5-VL 7B Q4, Gemma 4 VL 4B/8B |
| **`tier_3_high`** | Dedicated GPU with $\ge 16\text{ GB}$ VRAM, or Apple Silicon with $\ge 32\text{ GB}$ Unified Memory | $14\text{B}+$ parameters | Qwen2.5-VL 14B/72B Q4, Gemma 4 VL 26B/31B |

* **Enforcement Rule:** If an API client or config requests a model tier higher than the host's resolved tier ceiling, the system raises an explicit validation error (`ERR_HARDWARE_TIER_EXCEEDED`) and defaults to the safe tier.

---

## 3. Database Schema (SQLite DDL)

NutriVault maintains two separate databases:
1. `usda_reference.db`: Static, indexed tables populated from USDA FoodData Central (Foundation Foods and SR Legacy).
2. `nutrivault.db`: Dynamic user state, household profiles, dietary targets, dishes, and event logs.

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
    calories_target INTEGER NOT NULL,
    protein_g_target REAL NOT NULL,
    carbs_g_target REAL NOT NULL,
    fat_g_target REAL NOT NULL,
    fiber_g_target REAL NOT NULL,
    -- Micronutrients stored as JSON map: {"nutrient_id_or_code": target_float}
    micronutrients_json TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Batches / Dishes Table (Cook-Once Shared Items)
CREATE TABLE IF NOT EXISTS dishes (
    id TEXT PRIMARY KEY,                       -- UUIDv4
    name TEXT NOT NULL,
    total_estimated_grams REAL NOT NULL,
    total_calories REAL NOT NULL,
    total_protein_g REAL NOT NULL,
    total_carbs_g REAL NOT NULL,
    total_fat_g REAL NOT NULL,
    total_fiber_g REAL NOT NULL,
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
    calories REAL NOT NULL,
    protein_g REAL NOT NULL,
    carbs_g REAL NOT NULL,
    fat_g REAL NOT NULL,
    fiber_g REAL NOT NULL,
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
1. The client browser uploads the photo as `multipart/form-data`.
2. The server reads the stream chunks directly into a bounded in-memory byte buffer (`io.BytesIO`, max 15 MB) and **never** uses `SpooledTemporaryFile` or disk-backed temp files. **No image bytes are written to disk, caches, or swap.**
3. The image is base64-encoded in RAM and sent over the local loopback interface to the embedded `llama.cpp` instance (`POST /v1/chat/completions`) with structured JSON output enforcement and deterministic markdown code-fence stripping before parsing.
4. Once the JSON response is parsed or an error is raised, the in-memory buffer is overwritten/cleared (`buffer.seek(0); buffer.truncate(0); buffer.close()`) and collected by the runtime garbage collector.

### 4.2 Prompting & JSON Output Contract
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
* **Expected Response Schema:**
  ```json
  [
    {"item_name": "steamed edamame", "estimated_grams": 150.0},
    {"item_name": "cooked brown rice", "estimated_grams": 200.0},
    {"item_name": "tahini dressing", "estimated_grams": 30.0}
  ]
  ```

---

## 5. Neuro-Symbolic Grounding & Arithmetic Engine

The VLM is strictly forbidden from outputting nutritional math. All calculations are executed deterministically against `usda_reference.db`.

1. **Entity Normalization & Preparation State Weighting:** Strip punctuation, lowercase tokens, and compute normalized token-overlap and Levenshtein scores against `usda_foods.description` in `usda_reference.db`. State tokens (`cooked`, `steamed`, `roasted`, `boiled`, `fried`, `raw`) receive a $1.5\times$ scoring weight, and queries without an explicit raw/dry qualifier prefer `preparation_state IN ('cooked', 'prepared')` to prevent raw-vs-cooked caloric density mismatches.
2. **Deterministic Scaling:**
   $$\text{Nutrient}_{\text{actual}} = \text{Nutrient}_{\text{USDA per 100g}} \times \left( \frac{\text{estimated\_grams}}{100.0} \right)$$
3. **Interactive Confirmation Payload:** The server returns candidate items, USDA matches, and calculated nutrients to the client. The user can adjust portion weights, swap USDA candidates, add missing items, or delete misidentified items before committing to the database.

---

## 6. Advisory & Recommendation Contract

* **Clinical Hard Lock:** Any profile where `profile_type == 'chronic_condition'` blocks automated AI target generation with HTTP 403 (`ERR_CLINICAL_AI_RESTRICTED`) and presents the mandatory notice:
  > *"Nutritional goals for chronic conditions must be established in consultation with a qualified physician or registered dietitian. NutriVault does not provide clinical diagnoses or therapeutic prescriptions."*
* **Athletic & Fitness Recommendations:** For `profile_type == 'athletic'`, target estimations generated via local prompts must include the following advisory wire:
  > *"Local model fitness baselines are heuristic estimates. For rigorous training regimens or metabolic adjustments, consult a certified fitness trainer or cross-reference using privacy-preserving frontier endpoints (e.g., search.brave.com/ask)."*
  * Requires explicit boolean client acknowledgment (`acknowledged: true`) to commit targets.

---

## 7. REST API Interface Specification

| Endpoint | Method | Request Payload | Response Body | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/hardware` | `GET` | None | `HardwareStatusResponse` | Returns detected compute specs and active model tier ceiling. |
| `/api/v1/profiles` | `GET` | None | `Array<Profile>` | Lists all active household profiles. |
| `/api/v1/profiles` | `POST` | `ProfileCreateRequest` | `Profile` | Creates profile with baseline target envelope. |
| `/api/v1/profiles/{id}/targets` | `PUT` | `TargetEnvelopeRequest` | `TargetEnvelope` | Updates targets; validates condition restrictions. |
| `/api/v1/advisory/fitness-targets` | `POST` | `FitnessAdvisoryRequest` | `FitnessAdvisoryResponse` | Generates heuristic athletic macro targets with private frontier advisory. |
| `/api/v1/meals/parse-image` | `POST` | `multipart/form-data` (`image`) | `ParsedMealDraft` | In-memory VLM inference + USDA deterministic mapping. |
| `/api/v1/meals/commit` | `POST` | `MealCommitRequest` | `MealCommitResult` | Commits meal entries across 1..N profiles with portion fractions. |
| `/api/v1/analytics/rolling` | `GET` | `?profile_id={id}&days=7` | `RollingAnalyticsResponse` | Computes 7-day EMA for calories, macros, target deltas, and daily eating/fasting windows. |

---

## 8. Error Codes & State Responses

* **`ERR_HARDWARE_TIER_EXCEEDED` (HTTP 400):** Selected model tier exceeds host RAM/VRAM capacity.
* **`ERR_VLM_UNAVAILABLE` (HTTP 503):** Internal inference engine runner failed to bind or model weight file missing.
* **`ERR_VLM_INVALID_JSON` (HTTP 422):** Model emitted non-conformant JSON; retried once before falling back to manual entry.
* **`ERR_CLINICAL_AI_RESTRICTED` (HTTP 403):** AI advisory requested for a profile with a declared chronic condition.
* **`ERR_INVALID_PORTION_SUM` (HTTP 400):** Fractional allocations across family members sum to $\le 0.0$ or $> 1.0$.