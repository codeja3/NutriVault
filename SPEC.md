# Technical Specification (SPEC)

**Project Name:** NutriVault  
**Subtitle:** Local-First Personal and Family Nutrition Tracker  
**Status:** Approved & Locked  
**Version:** 1.4.0  

---

## 1. System Architecture Overview

NutriVault runs as a self-contained local backend service on the user's host workstation (macOS, Linux, Windows, or Docker) and serves an offline-capable, zero-build Progressive Web App (PWA) alongside a REST API (`http://localhost:8080` / `http://nutrivault.local:8080`, default bind `0.0.0.0:8080`).

To provide a true "one-stop shop" experience both at home and when the user is away from their laptop (e.g., at a restaurant or scanning barcodes in a grocery store):
1. **Out-of-the-Box Operation:** On startup, `run_server()` automatically initializes `nutrivault.db` and seeds `usda_foods` with a curated catalog of common USDA Foundation / SR Legacy foods and packaged staple UPC/EAN barcodes (`seed_default_usda_foods`) if the reference table is empty.
2. **Predefined Tier-Matched Small VLMs & Managed Sidecar:** Each hardware tier maps to a predefined, checksum-pinned default VLM (`PREDEFINED_VLM_CATALOG`, defaulting to the 550 MB `SmolVLM-500M-Instruct-Q8_0` for universal CPU/Docker use). In Docker (`docker-compose.yml`), the `nutrivault-vlm` sidecar automatically pulls and serves the predefined model on `:8081` with zero manual file hunting.
3. **Offline-First Mobility ("Snap & Sync Later" + 3-Tier Barcode Resolution):** The embedded Service Worker (`GET /sw.js`) and IndexedDB engine (`offline_foods_cache` and `offline_sync_queue`) allow the mobile PWA to open offline, resolve cached barcodes in $<10\text{ ms}$, queue new barcode scans or restaurant meal photos with their original `logged_at` consumption timestamps, and synchronize via `POST /api/v1/sync/batch` upon reconnecting to the host laptop (via home Wi-Fi or optional Tailscale P2P sidecar).

```
 +-------------------------------------------------------------------------+
 | Mobile / Desktop Client Browser (Installable Offline-First PWA)         |
 |   ├── Service Worker (`GET /sw.js` - Offline Shell & Bootstrap Cache)   |
 |   ├── IndexedDB `offline_foods_cache` (Tier-1 <10ms Offline Barcodes)   |
 |   ├── IndexedDB `offline_sync_queue`  ("Snap & Sync Later" Queue)       |
 |   └── Camera Barcode Scanner (`BarcodeDetector` + Manual UPC Fallback)  |
 +-----------------------------------┬-------------------------------------+
                                     │ LAN Wi-Fi / P2P VPN / Reconnect Sync
                                     ▼
 +-------------------------------------------------------------------------+
 | NutriVault Host Backend Daemon (`ThreadingHTTPServer` + API Lock :8080) |
 |   ├── Embedded PWA & Service Worker Server (`src/ui.py` / Zero-CDN)     |
 |   ├── Hardware Prober & Predefined VLM Catalog (`PREDEFINED_VLM_CATALOG`)|
 |   ├── Ephemeral Buffer Manager (In-memory `BytesIO` / `0x00` Purge)     |
 |   ├── Loopback VLM Client (`127.0.0.1:8081` / SSRF Loopback Guard)      |
 |   ├── Grounding & Barcode Engine (Cached Token Scorer + UPC/EAN Index)  |
 |   ├── Offline Batch Sync Processor (`POST /api/v1/sync/batch`)          |
 |   └── SQLite Storage Engine (WAL mode, Foreign Keys ON)                 |
 |         ├── Auto-Seeded USDA & Barcode Catalog (`seed_default_usda_foods`)|
 |         ├── `usda_reference.db` (Optional External Attached Reference)  |
 |         └── `nutrivault.db`     (Profiles, Envelopes, Ledgers, Dishes)  |
 +-------------------------------------------------------------------------+
```

### 1.1 Concurrency & Thread-Safety Contract
* The HTTP daemon (`ThreadingHTTPServer`) serializes all database and state-mutating operations through a per-instance synchronization lock (`threading.Lock`) inside `NutriVaultAPI.handle_request` to prevent cross-thread SQLite transaction interleaving (`OperationalError` or unintended rollbacks).
* Loopback VLM endpoints are strictly validated against `{"127.0.0.1", "localhost", "::1"}` at client initialization to prevent Server-Side Request Forgery (SSRF) and guarantee Zero-WAN isolation.

---

## 2. Hardware Profiling & Predefined Small VLM Catalog (`src/hardware.py`)

Before loading or recommending model weights, the backend inspects host compute resources, enforces an upper tier ceiling, and maps each tier to an exact predefined default VLM so average users never have to choose `.gguf` or `mmproj` files manually.

### 2.1 Hardware Gates, Predefined Default VLM Specs & Tier Catalog

```python
@dataclass(frozen=True)
class PredefinedVLMModel:
    tier: HardwareTier
    name: str
    hf_repo: str
    model_file: str
    mmproj_file: str
    approx_size_mb: int
    sha256_model: str
    sha256_mmproj: str
```

| Tier Name | Hardware Pre-requisites | Predefined Default VLM (`PREDEFINED_VLM_CATALOG`) | HuggingFace Repo (`hf_repo`) & Files (`model_file` / `mmproj_file`) | Approx. Size |
| :--- | :--- | :--- | :--- | :---: |
| **`tier_1_cpu`** | CPU-only, or $<6\text{ GB}$ dedicated VRAM, or $<16\text{ GB}$ RAM | `SmolVLM-500M-Instruct-Q8_0` | `ggml-org/SmolVLM-500M-Instruct-GGUF` (`SmolVLM-500M-Instruct-Q8_0.gguf` + `mmproj-SmolVLM-500M-Instruct-Q8_0.gguf`) | $550\text{ MB}$ |
| **`tier_2_mid`** | Dedicated GPU with $\ge 6\text{ GB}$ VRAM, or Apple Silicon with $\ge 16\text{ GB}$ Unified Memory | `Qwen2.5-VL-3B-Instruct-Q4_K_M` | `ggml-org/Qwen2.5-VL-3B-Instruct-GGUF` (`Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf` + `mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf`) | $2200\text{ MB}$ |
| **`tier_3_high`** | Dedicated GPU with $\ge 16\text{ GB}$ VRAM, or Apple Silicon with $\ge 32\text{ GB}$ Unified Memory | `Qwen2.5-VL-7B-Instruct-Q4_K_M` | `ggml-org/Qwen2.5-VL-7B-Instruct-GGUF` (`Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` + `mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf`) | $5000\text{ MB}$ |

* **Enforcement Rule:** If an API client or config requests a model tier higher than the host's resolved tier ceiling, the system raises an explicit validation error (`ERR_HARDWARE_TIER_EXCEEDED`).
* **Helper Interfaces (`src/hardware.py`):**
  * `get_recommended_models(tier: HardwareTier) -> list[str]`: Returns the curated list of GGUF model filenames for the given tier.
  * `get_default_vlm_spec(tier: HardwareTier) -> PredefinedVLMModel`: Returns the pinned default `PredefinedVLMModel` for the given tier.
  * `build_managed_vlm_command(tier: HardwareTier, port: int = 8081, host: str = "127.0.0.1") -> list[str]`: Returns the zero-manual-download `llama-server` argv list using `--hf-repo <hf_repo> --hf-file <model_file> --port <port> --host <host>`.
  * `detect_local_lan_ip() -> str`: Detects the host machine's local area network IPv4 address (falling back cleanly to `"127.0.0.1"` when disconnected) so the web UI can display the exact phone connection URL (`local_lan_url`).
  * `format_vlm_setup_guide(profile: HardwareProfile | None = None) -> str`: Generates a human-readable setup guide showing detected hardware, resolved tier ceiling, the predefined default model spec (`hf_repo`, `approx_size_mb`), and the one-command `llama-server --hf-repo ...` invocation.

---

## 3. Database Schema (SQLite DDL), Barcode Index & Starter Seed

NutriVault supports both a unified single-file/in-memory SQLite schema and a dual-database deployment:
1. `usda_reference.db`: Static, indexed tables populated from USDA FoodData Central. Attached at runtime via `attach_usda_reference(conn, usda_db_path, schema_name="usda")` using a strict static whitelist (`"usda"` or `"usda_reference"`).
2. `nutrivault.db`: Dynamic user state, household profiles, dietary targets, dishes, meal logs, and local USDA/barcode entries.
3. **Schema Resolution Rule:** When `usda` or `usda_reference` is attached and its `usda_foods` table is populated (while `main.usda_foods` is empty), `GroundingEngine` queries the attached schema (`usda.usda_foods` or `usda_reference.usda_foods`).
4. **Idempotent Schema Migration for `barcode`:** `init_db(conn)` inspects `PRAGMA table_info(usda_foods)` and executes `ALTER TABLE usda_foods ADD COLUMN barcode TEXT` if an existing database file was created prior to v1.3.0, followed by `CREATE INDEX IF NOT EXISTS idx_usda_foods_barcode ON usda_foods (barcode)`.
5. **Out-of-the-Box Starter Seed (`seed_default_usda_foods`):**
   * `seed_default_usda_foods(conn: sqlite3.Connection) -> int` in `src/db.py` checks if `usda_foods` is currently empty (`COUNT(*) == 0`). If empty, it inserts `DEFAULT_USDA_FOODS` ($\ge 25$ staple foods across grains, proteins, vegetables, fruits, dairy, legumes, nuts/seeds, and oils, with pre-assigned standard UPC/EAN `barcode` strings on packaged staples) and returns the number of inserted rows.

### 3.1 Schema: `usda_foods`

```sql
CREATE TABLE IF NOT EXISTS usda_foods (
    fdc_id INTEGER PRIMARY KEY,                -- Official USDA FDC ID or local custom ID
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
    micros_per_100g_json TEXT NOT NULL DEFAULT '{}',
    barcode TEXT                               -- Optional UPC-A / EAN-13 / GTIN barcode string
);

CREATE INDEX IF NOT EXISTS idx_usda_foods_description ON usda_foods (description);
CREATE INDEX IF NOT EXISTS idx_usda_foods_barcode ON usda_foods (barcode);
```

### 3.2 Schema: `nutrivault.db` Core Tables

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
    raw_ingredients_json TEXT NOT NULL,
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
4. **Deterministic `0x00` Memory Purge:** Once the JSON response is parsed or an error is raised, `EphemeralImageBuffer.purge()` acquires the underlying `BytesIO` buffer via a context manager (`with self._stream.getbuffer() as buf:`), overwrites every byte in-place with `0x00` (`buf[:] = b"\x00" * len(buf)`), releases the `memoryview`, truncates (`truncate(0)`), closes the stream (`close()`), and invokes `gc.collect()`.

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
* **Validation Rules:**
  * The parsed JSON must be a non-empty `list` (`len >= 1`).
  * Every element must contain a non-empty string `item_name` and a strictly positive float `estimated_grams > 0.0`.
  * Malformed JSON, empty list `[]`, blank `item_name`, or `estimated_grams <= 0.0` triggers 1 retry (`max_retries = 1`) before raising `VLMInvalidJSONError` (`ERR_VLM_INVALID_JSON`, HTTP 422).
  * Unreachable loopback socket or HTTP transport error raises `VLMUnavailableError` (`ERR_VLM_UNAVAILABLE`, HTTP 503).

---

## 5. Neuro-Symbolic Grounding, Barcode Resolution & Batch Allocation

The VLM is strictly forbidden from outputting nutritional math. All calculations are executed deterministically against `usda_foods`.

1. **Entity Normalization, Caching & Preparation State Weighting:**
   * `GroundingEngine` caches tokenized USDA entries in memory (`CachedFoodEntry`, including optional `barcode: str | None`) on first query (with explicit `invalidate_cache()` support).
   * Normalized token-overlap ($0.7$ weight) and sequence similarity ($0.3$ weight) scores are computed against `usda_foods.description`, with a $1.5\times$ multiplier for state tokens (`cooked`, `steamed`, `roasted`, `boiled`, `fried`, `raw`, `prepared`, `baked`).
2. **Exact Barcode Lookup, Registration & Offline Catalog Export (`src/grounding.py`):**
   * **Barcode Normalization (`normalize_barcode(code: str) -> str`):** Strips whitespace; validates that `code` is 4 to 32 ASCII alphanumeric/digit characters (`[A-Za-z0-9_-]{4,32}`), otherwise raises `ValueError`.
   * **`lookup_barcode(barcode: str, grams: float = 100.0) -> GroundedFoodCandidate | None`:** Searches the cached `usda_foods` entries for an exact normalized `barcode` match and scales nutrients linearly to `grams` (must be $> 0.0$). Returns `None` if no match exists.
   * **`register_barcode(...) -> GroundedFoodCandidate`:** Inserts a new row (or updates an existing row with the same `barcode`) in `main.usda_foods`, invalidates the in-memory `GroundingEngine` cache, and returns the scaled `GroundedFoodCandidate` for `100.0` grams.
   * **`export_offline_catalog() -> list[dict[str, Any]]`:** Returns all cached `usda_foods` entries with `fdc_id`, `description`, `food_category`, `preparation_state`, `barcode`, `calories_per_100g`, `protein_g_per_100g`, `carbs_g_per_100g`, `fat_g_per_100g`, `fiber_g_per_100g`, and `micros_per_100g` for client IndexedDB synchronization.
3. **Deterministic Linear Scaling & Rounding Precision:**
   $$\text{Nutrient}_{\text{actual}} = \text{Nutrient}_{\text{USDA per 100g}} \times \left( \frac{\text{grams}}{100.0} \right)$$
   * **Precision Standard:** Grams, calories, and macronutrients (`protein_g`, `carbs_g`, `fat_g`, `fiber_g`) are rounded to **2 decimal places** (`round(val, 2)`). Micronutrients (`micros`) are rounded to **3 decimal places** (`round(val, 3)`).
4. **Atomic Batch Dish & Multi-Profile Allocation (`BatchDishAllocator.commit_meal`):**
   * Fractional allocations across family members must each satisfy $0.0 < \text{fraction} \le 1.0$ and their sum must satisfy $0.0 < \sum \text{fraction} \le 1.0$, otherwise `InvalidPortionSumError` (`ERR_INVALID_PORTION_SUM`, HTTP 400) is raised.
   * Dish creation (`dishes`) and all member journal entries (`meal_logs`) execute inside a single atomic SQLite transaction.

---

## 6. Advisory & Recommendation Contract

* **Clinical Hard Lock:** Any profile where `profile_type == 'chronic_condition'` blocks automated AI target generation on both `POST /api/v1/advisory/fitness-targets` and `PUT /api/v1/profiles/{id}/targets` (when `is_ai_generated == true`) with HTTP 403 (`ERR_CLINICAL_AI_RESTRICTED`) and presents the mandatory notice:
  > *"Nutritional goals for chronic conditions must be established in consultation with a qualified physician or registered dietitian. NutriVault does not provide clinical diagnoses or therapeutic prescriptions."*
* **Athletic & Fitness Recommendations:** For `profile_type == 'athletic'`, target estimations generated via local prompts must include the advisory wire:
  > *"Local model fitness baselines are heuristic estimates. For rigorous training regimens or metabolic adjustments, consult a certified fitness trainer or cross-reference using privacy-preserving frontier endpoints (e.g., search.brave.com/ask)."*
  * Committing AI-generated targets (`is_ai_generated: true`) on an `athletic` profile requires explicit `acknowledged: true` (otherwise HTTP 400).

---

## 7. Web UI, Service Worker & REST API Interface Specification

| Endpoint | Method | Success Status | Content-Type / Payload | Response Body | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `/` | `GET` | `200` | None | `text/html; charset=utf-8` | Serves the built-in offline-capable Progressive Web App (PWA) UI. |
| `/manifest.json` | `GET` | `200` | None | `application/manifest+json` | Serves the PWA web manifest for home-screen installation. |
| `/sw.js` | `GET` | `200` | None | `application/javascript; charset=utf-8` | Serves the offline Service Worker caching the app shell and bootstrap state. |
| `/api/v1/hardware` | `GET` | `200` | None | `HardwareStatusResponse` | Returns compute specs, active tier ceiling, `recommended_models`, `default_vlm`, `managed_vlm_command`, and `local_lan_url`. |
| `/api/v1/profiles` | `GET` | `200` | None | `Array<Profile>` | Lists all household profiles ordered by `created_at ASC`. |
| `/api/v1/profiles` | `POST` | `201` | `ProfileCreateRequest` | `Profile` | Creates a household profile. |
| `/api/v1/profiles/{id}/targets` | `PUT` | `200` | `TargetEnvelopeRequest` | `TargetEnvelope` | Atomically updates active targets; enforces clinical & athletic safeguards. |
| `/api/v1/advisory/fitness-targets` | `POST` | `200` | `FitnessAdvisoryRequest` | `AthleticAdvisoryResponse` | Generates heuristic athletic macro targets with private frontier advisory. |
| `/api/v1/foods/search` | `GET` | `200` | `?q={query}&grams=100&limit=10` | `FoodSearchResponse` | Searches USDA foods and deterministically scales nutrients to `grams`. |
| `/api/v1/foods/catalog` | `GET` | `200` | None | `OfflineCatalogResponse` | Exports local `usda_foods` reference rows (with barcodes) for client IndexedDB offline caching. |
| `/api/v1/foods/barcode/{code}` | `GET` | `200` | `?grams=100` | `BarcodeLookupResponse` | Resolves an exact UPC/EAN barcode from `usda_foods` and scales nutrients to `grams`. |
| `/api/v1/foods/barcode/{code}` | `PUT` | `200` | `BarcodeRegisterRequest` | `BarcodeLookupResponse` | Registers or updates a custom/store barcode in `usda_foods` for Tier-1 offline reuse. |
| `/api/v1/meals/parse-image` | `POST` | `200` | `multipart/form-data` (`image`) | `ParsedMealDraft` | In-memory VLM inference + USDA deterministic mapping + `0x00` purge. |
| `/api/v1/meals/commit` | `POST` | `201` | `MealCommitRequest` | `MealCommitResult` | Atomically commits dish and 1..N profile meal logs with portion fractions. |
| `/api/v1/sync/batch` | `POST` | `200` | `OfflineSyncBatchRequest` | `OfflineSyncBatchResponse` | Flushes offline-queued meals and deferred barcode scans preserving original `logged_at` timestamps. |
| `/api/v1/analytics/rolling` | `GET` | `200` | `?profile_id={id}&days=7` | `RollingAnalyticsResponse` | Computes $N$-day EMA for calories, macros, target deltas, and eating/fasting windows. |

### 7.1 Request & Query Payload Contracts
* **`GET /api/v1/foods/barcode/{code}?grams=100`:**
  * `code`: validated via `normalize_barcode(code)` (`[A-Za-z0-9_-]{4,32}`). Invalid format returns HTTP 400.
  * `grams`: `float > 0.0` (defaults to `100.0`; non-numeric or $\le 0.0$ returns HTTP 400).
  * If found, returns `200 OK`:
    ```json
    {
      "barcode": "0030000010204",
      "fdc_id": 1003,
      "description": "Oats, rolled, old-fashioned, dry",
      "food_category": "Cereal Grains and Pasta",
      "preparation_state": "raw",
      "nutrients": {
        "grams": 100.0,
        "calories": 379.0,
        "protein_g": 13.15,
        "carbs_g": 67.7,
        "fat_g": 6.52,
        "fiber_g": 10.1,
        "micronutrients": {"iron_mg": 4.25, "magnesium_mg": 138.0}
      }
    }
    ```
  * If not found, raises `BarcodeNotFoundError` (`ERR_BARCODE_NOT_FOUND`, HTTP 404).
* **`PUT /api/v1/foods/barcode/{code}` (`BarcodeRegisterRequest`):**
  * `description`: non-empty string (`min_length=1`, stripped)
  * `calories_per_100g`, `protein_g_per_100g`, `carbs_g_per_100g`, `fat_g_per_100g`, `fiber_g_per_100g`: `float >= 0.0`
  * `micros_per_100g`: `dict[str, float] = {}` (all values $\ge 0.0$)
  * `food_category`: `str = "Packaged Foods"`
  * `preparation_state`: `Literal["cooked", "raw", "prepared", "unknown"] = "prepared"`
* **`POST /api/v1/sync/batch` (`OfflineSyncBatchRequest`):**
  * `queued_meals`: `list[MealCommitRequest] = []` — Pre-resolved meals logged offline (using cached USDA/barcode items) with their original `logged_at` timestamps inside `allocations`.
  * `queued_barcodes`: `list[QueuedBarcodeItemRequest] = []` — Deferred barcode scans captured while the phone was offline and the barcode was not in IndexedDB:
    * `barcode`: non-empty string (`min_length=4`)
    * `grams`: `float > 0.0`
    * `dish_name`: `str | None = None`
    * `allocations`: non-empty list (`min_length=1`) of `ProfilePortionAllocationRequest` (preserving original `logged_at` timestamp and `meal_type`).
  * **Processing & Response Schema (`OfflineSyncBatchResponse`):**
    * Commits each item in `queued_meals`.
    * For each item in `queued_barcodes`, attempts `lookup_barcode(item.barcode, item.grams)`. If resolved, commits the dish and allocations with the original `logged_at` timestamp; if unrecognized, appends `{ "barcode": item.barcode, "grams": item.grams, "allocations": [...] }` to `unresolved_barcodes` so the user can map it via Tier 3 (`PUT /api/v1/foods/barcode/{code}`) without losing any other queued items in the batch.
    ```json
    {
      "synced_meals_count": 2,
      "meal_log_ids": ["uuid-1", "uuid-2"],
      "unresolved_barcodes": [
        {
          "barcode": "9999999999999",
          "grams": 120.0,
          "allocations": [{"profile_id": "prof-1", "fraction": 1.0, "meal_type": "snack", "logged_at": "2026-11-08T14:30:00"}]
        }
      ]
    }
    ```

### 7.2 Rolling Analytics & Chrononutrition Specification
* **Window Parameter (`days`):** Must be an integer $\ge 1$ (defaults to `7`). Values $< 1$ or non-integers raise `ValueError` (HTTP 400).
* **Rolling EMA Calculation:** Aggregates daily totals (`GROUP BY DATE(logged_at)`) for the **most recent $N$ logged days** (`ORDER BY meal_date DESC LIMIT ?`), re-orders them chronologically (`ORDER BY meal_date ASC`), and computes the exponential moving average with smoothing factor $k = \frac{2}{\text{len(series)} + 1}$.
* **Target Adherence Deltas:** When an active `TargetEnvelope` exists for `profile_id`, `target_deltas[metric] = round(metric_ema - target_metric, 2)`.
* **Chrononutrition Windows (`calculate_chrononutrition_windows`):**
  * Selects daily `MIN(logged_at)` (`first_meal_time`) and `MAX(logged_at)` (`last_meal_time`) for `profile_id` (bounded to the most recent `days` logged dates).
  * `eating_window_hours = round((last_dt - first_dt).total_seconds() / 3600.0, 2)`.
  * `overnight_fast_hours`: Computed **only** when the previous logged day and current logged day are strictly consecutive calendar days (`(first_dt.date() - prev_last_dt.date()).days == 1`) and `first_dt > prev_last_dt`; otherwise `None`.

### 7.3 Built-In Offline-First Progressive Web App & Service Worker (`src/ui.py`)
* Served at `GET /` (`text/html; charset=utf-8`), `GET /manifest.json` (`application/manifest+json`), and `GET /sw.js` (`application/javascript; charset=utf-8`).
* **Zero External Network Calls:** All HTML, CSS, ES6 JavaScript, and Service Worker logic are embedded directly in `src/ui.py`; zero external CDN URLs are referenced.
* **Offline-First Capabilities (`GET /sw.js` & IndexedDB):**
  1. **Service Worker (`GET_PWA_SERVICE_WORKER()`):** Caches `/`, `/manifest.json`, `/api/v1/profiles`, and `/api/v1/foods/catalog` using a network-first-with-cache-fallback strategy for GET API routes and cache-first/network-update for shell assets so the app opens on a phone even when completely away from the host laptop.
  2. **IndexedDB (`nutrivault_offline_db`):**
     * `offline_foods_cache`: Synced automatically from `GET /api/v1/foods/catalog` whenever the host is reachable. Enables offline text search and Tier-1 ($<10\text{ ms}$) offline barcode lookups.
     * `offline_sync_queue`: Stores offline meal commits, deferred barcode scans (`queued_barcodes`), and queued restaurant meal photos (with original `logged_at` ISO-8601 timestamps).
  3. **Connectivity Status & 1-Tap Sync Banner:** Displays live connection state (`Online — Connected to Host` vs `Offline Mode — Snap & Sync Later Active`), shows the count of pending offline queue items, automatically flushes the queue via `POST /api/v1/sync/batch` (and `POST /api/v1/meals/parse-image` for queued photos) when reconnected, and surfaces a 1-tap **"Register Custom Barcode"** modal for any `unresolved_barcodes`.
  4. **In-Browser Camera Barcode Scanner:** Uses `window.BarcodeDetector` (`ean_13`, `ean_8`, `upc_a`, `upc_e`, `code_128`) with live `<video>` stream scanning plus an instant manual barcode input field fallback.

---

## 8. Error Codes & HTTP State Responses

* **`ERR_HARDWARE_TIER_EXCEEDED` (HTTP 400):** Selected model tier exceeds host RAM/VRAM capacity.
* **`ERR_INVALID_PORTION_SUM` (HTTP 400):** Fractional allocations across family members are empty, contain an element $\le 0.0$ or $> 1.0$, or sum to $\le 0.0$ or $> 1.0$.
* **Validation / Schema / Integrity Error (HTTP 400):** Malformed JSON, Pydantic `ValidationError`, invalid query parameters (`days < 1`, missing `profile_id`, invalid `q`/`grams`/`limit`, malformed `barcode`), unacknowledged athletic AI target envelope, or `sqlite3.IntegrityError`.
* **`ERR_CLINICAL_AI_RESTRICTED` (HTTP 403):** AI advisory generation or AI-generated target envelope commit requested for a profile with `profile_type == 'chronic_condition'`.
* **`ERR_BARCODE_NOT_FOUND` (HTTP 404):** Scanned or queried barcode does not exist in `usda_foods.barcode`.
* **Resource / Route Not Found (HTTP 404):** Unknown endpoint path/method or non-existent `profile_id` (`KeyError`).
* **`ERR_IMAGE_PAYLOAD_TOO_LARGE` (HTTP 413):** Uploaded image `Content-Length` or buffer size exceeds the 15 MB volatile memory ceiling.
* **`ERR_VLM_INVALID_JSON` (HTTP 422):** Local VLM emitted non-conformant JSON, empty candidate list, blank `item_name`, or `estimated_grams <= 0.0` across initial attempt and 1 retry.
* **Internal Server Error (HTTP 500):** Unexpected runtime failure; returns sanitized `{"error": "Internal server error."}` without leaking stack traces or internal state.
* **`ERR_VLM_UNAVAILABLE` (HTTP 503):** Loopback inference engine (`127.0.0.1:8081`) failed to connect, timed out, or returned an HTTP transport error.

---

## 9. Double-Click Desktop Launchers, Containerization & Role-Separated Documentation Specification

1. **Double-Click Desktop Launchers (`Start_NutriVault.command` & `Start_NutriVault.bat`) & `--open-browser` CLI Flag:**
   * `Start_NutriVault.command` (macOS Finder double-clickable executable script) and `Start_NutriVault.bat` (Windows Explorer double-clickable batch script) allow non-technical users to launch NutriVault by double-clicking an icon in their unzipped folder without opening a terminal or typing commands.
   * Each script automatically switches its working directory to the script's own folder, prefers `docker compose up` if Docker Desktop is running or seamlessly bootstraps/runs `uv run python -m src.api --open-browser`, and automatically opens `http://localhost:8080` in the user's default web browser.
   * `python -m src.api --open-browser` (and `run_server(..., open_browser: bool = False)`) spawns a short background timer that invokes `webbrowser.open(f"http://localhost:{port}")` once the HTTP server binds.
   * The web UI header displays `#phone-wifi-link` populated from `GET /api/v1/hardware` (`local_lan_url`, e.g., `http://192.168.1.x:8080`) so the user can copy-paste or type the exact address into their phone browser without searching system network settings.
2. **One-Stop `docker-compose.yml` with Preconfigured VLM Sidecar & Optional P2P Tunnel:**
   * `nutrivault` service (`8080:8080`, `./data:/app/data`).
   * `nutrivault-vlm` sidecar service (`ghcr.io/ggerganov/llama.cpp:server`) preconfigured to serve the default `SmolVLM-500M-Instruct-Q8_0` (`--hf-repo ggml-org/SmolVLM-500M-Instruct-GGUF --hf-file SmolVLM-500M-Instruct-Q8_0.gguf --port 8081 --host 0.0.0.0`) with cached `./models:/root/.cache/llama.cpp` volume persistence so camera AI works out-of-the-box on `docker compose up`.
   * Optional `nutrivault-remote` (`tailscale/tailscale`) service under `--profile remote` for live encrypted P2P access away from home.
3. **Role-Separated Documentation (`README.md`, `MANUAL.md`, `DEV_MANUAL.md`):**
   * `README.md`: High-level overview, 1-click download & double-click quickstart, offline "Snap & Sync Later" and barcode overview, and links to `MANUAL.md` (for users) and `DEV_MANUAL.md` (for developers).
   * `MANUAL.md`: Strictly end-user focused. Zero terminal requirements, zero `uv`/`git` jargon. Walks a complete beginner through: (1) Clicking the direct ZIP download link and unzipping it in `Downloads`, (2) Double-clicking `Start_NutriVault.command` (Mac) or `Start_NutriVault.bat` (Windows) so the browser opens automatically, (3) Reading the **`Phone Wi-Fi Link`** badge at the top of the NutriVault screen to install the phone app ("Add to Home Screen"), and (4) Using instant search, meal photos, family batch splitting, 3-tier grocery barcode scanning, and "Snap & Sync Later" travel mode.
   * `DEV_MANUAL.md`: Dedicated developer handbook covering `uv` toolchain setup, `git` workflow, TDD (`Red -> Green -> Refactor`), module architecture (`src/`), SQLite schemas & dual-DB attachment, neuro-symbolic grounding math, `0x00` volatile memory guarantees, `curl` REST API reference, and custom `llama-server` debugging.
