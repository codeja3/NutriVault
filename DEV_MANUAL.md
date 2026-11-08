# NutriVault Developer Handbook & Architecture Reference 🛠️

**Project:** NutriVault (Local-First Personal & Family Nutrition Tracker)  
**Core Runtime:** Python 3.11+ strictly  
**Toolchain:** `uv`  
**Methodology:** Specification-Driven Development (SDD) & Strict Test-Driven Development (TDD)

---

## 1. Architectural Principles & Non-Negotiable Boundaries

1. **Specification Authority:** All behavior is bounded by `PRD.md` and `SPEC.md`. Never implement uncontracted endpoints or speculative features.
2. **Zero WAN / Fully Hermetic Execution:**
   - 100% offline unit and contract tests. Zero live network calls during automated test suites.
   - All tests execute against in-memory SQLite instances (`:memory:`), mock sockets, or ephemeral buffers.
3. **Strict Test-Driven Development (TDD):** Every feature follows **RED** (write atomic failing test) $\rightarrow$ **GREEN** (minimal code to pass) $\rightarrow$ **REFACTOR** (cleanup with 100% green tests).
4. **Neuro-Symbolic Grounding & Exact Determinism:**
   - Multimodal Vision-Language Models (VLMs) are strictly entity and mass estimators; models are never allowed to compute arithmetic or nutritional values.
   - All calories, macronutrients, and micronutrients are computed deterministically via exact linear scaling against USDA tables:
     $$\text{Nutrient}_{\text{resolved}} = \text{Nutrient}_{\text{USDA}} \times \left( \frac{\text{grams}}{100.0} \right)$$
5. **Ephemeral Volatile Memory Purge (`0x00`):**
   - Uploaded meal photographs are held strictly in RAM (`io.BytesIO`, 15 MB contract ceiling).
   - Images are never written to disk, temporary folders, or swap.
   - Intermediate buffers are zeroed out with `0x00` bytes upon review or error.

---

## 2. Environment & Toolchain Setup

NutriVault exclusively uses `uv` for environment management, dependency resolution, and tool execution.

### Virtual Environment & Dependency Management
```bash
# 1. Clone the repository
git clone https://github.com/codeja3/NutriVault.git
cd NutriVault

# 2. Create isolated virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Synchronize pinned dependencies
uv sync

# 4. Add runtime or dev dependencies
uv add <package>
uv add --dev pytest pytest-mock pytest-asyncio ruff
```

### Running Automated Test Suite
```bash
# Full offline regression suite
uv run pytest

# Run specific test module or keyword pattern
uv run pytest tests/test_api.py -k "barcode or sync_batch"
```

### Formatting & Linting
```bash
# Automated linting and formatting via Ruff
uv run ruff check .
uv run ruff format .
```

---

## 3. Codebase Architecture & Module Map

All source code resides in `src/`, structured as modular, single-responsibility domains:

* **[`src/hardware.py`](file:///Users/yannis/Projects/NutriVault/src/hardware.py):** Hardware probing (RAM, VRAM, Apple Silicon / CUDA / CPU), model tier resolution (`tier_1_cpu`, `tier_2_mid`, `tier_3_high`), predefined VLM catalog (`PredefinedVLMModel`), and zero-download-hunt command generator (`build_managed_vlm_command`).
* **[`src/vision_pipeline.py`](file:///Users/yannis/Projects/NutriVault/src/vision_pipeline.py):** Volatile RAM memory management (`EphemeralImageBuffer`, 15 MB ceiling, `0x00` zeroing context manager) and SSRF-hardened loopback client (`VLMClient` connecting to `:8081`).
* **[`src/grounding.py`](file:///Users/yannis/Projects/NutriVault/src/grounding.py):** Token normalization, token overlap & Levenshtein string matching, cooked-first state weighting, deterministic linear nutrient scaling, barcode lookups, and offline catalog export.
* **[`src/batch_allocator.py`](file:///Users/yannis/Projects/NutriVault/src/batch_allocator.py):** Fractional family portion allocator ($\sum \text{fraction} \le 1.0$), atomic dish logging, and consistent 3-decimal micronutrient precision.
* **[`src/analytics.py`](file:///Users/yannis/Projects/NutriVault/src/analytics.py):** Window-bounded rolling Exponential Moving Average (EMA) and chrononutrition feeding intervals (eating windows and consecutive overnight fast hours).
* **[`src/advisory.py`](file:///Users/yannis/Projects/NutriVault/src/advisory.py):** Clinical safeguard gating (blocking AI target envelopes on `chronic_condition` profiles) and athletic target heuristic generation with mandatory disclaimer wires.
* **[`src/db.py`](file:///Users/yannis/Projects/NutriVault/src/db.py):** SQLite connection management, parameterized DDL schemas, legacy barcode migration, staple USDA food seeding, and profile CRUD repository.
* **[`src/api.py`](file:///Users/yannis/Projects/NutriVault/src/api.py):** Thread-safe HTTP request dispatcher, Pydantic contract validation, REST endpoints, and CLI launcher.
* **[`src/ui.py`](file:///Users/yannis/Projects/NutriVault/src/ui.py):** Built-in zero-build Progressive Web App (HTML5/CSS3/ES6), Service Worker (`/sw.js`), IndexedDB offline cache, and in-browser camera barcode scanner (`BarcodeDetector`).

---

## 4. SQLite Schema & Dual-DB Attachment

### Parametric DDL (`src/db.py`)
```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Household Profiles
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    profile_type TEXT NOT NULL CHECK (profile_type IN ('standard', 'athletic', 'chronic_condition')),
    birth_date TEXT,
    condition_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Target Nutrition Envelopes
CREATE TABLE IF NOT EXISTS target_envelopes (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    calories_target REAL NOT NULL CHECK (calories_target >= 0.0),
    protein_g_target REAL NOT NULL CHECK (protein_g_target >= 0.0),
    carbs_g_target REAL NOT NULL CHECK (carbs_g_target >= 0.0),
    fat_g_target REAL NOT NULL CHECK (fat_g_target >= 0.0),
    fiber_g_target REAL NOT NULL CHECK (fiber_g_target >= 0.0),
    micronutrients_json TEXT NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shared Family Dishes
CREATE TABLE IF NOT EXISTS dishes (
    id TEXT PRIMARY KEY,
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

-- Immutable Meal Journal
CREATE TABLE IF NOT EXISTS meal_logs (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    dish_id TEXT REFERENCES dishes(id) ON DELETE SET NULL,
    meal_type TEXT NOT NULL CHECK (
        meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'pre_workout', 'post_workout')
    ),
    portion_fraction REAL NOT NULL DEFAULT 1.0 CHECK (
        portion_fraction > 0.0 AND portion_fraction <= 1.0
    ),
    calories REAL NOT NULL CHECK (calories >= 0.0),
    protein_g REAL NOT NULL CHECK (protein_g >= 0.0),
    carbs_g REAL NOT NULL CHECK (carbs_g >= 0.0),
    fat_g REAL NOT NULL CHECK (fat_g >= 0.0),
    fiber_g REAL NOT NULL CHECK (fiber_g >= 0.0),
    micronutrients_json TEXT NOT NULL DEFAULT '{}',
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- USDA Food & Barcode Catalog
CREATE TABLE IF NOT EXISTS usda_foods (
    fdc_id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    food_category TEXT,
    preparation_state TEXT DEFAULT 'prepared',
    barcode TEXT,
    calories_per_100g REAL NOT NULL,
    protein_g_per_100g REAL NOT NULL,
    carbs_g_per_100g REAL NOT NULL,
    fat_g_per_100g REAL NOT NULL,
    fiber_g_per_100g REAL NOT NULL,
    micros_per_100g_json TEXT,
    created_at TEXT DEFAULT (datetime('now', 'utc'))
);

CREATE INDEX IF NOT EXISTS idx_usda_foods_barcode ON usda_foods (barcode);
```

### Dual-Database Attachment
To keep personal user logs separate from heavy read-only reference data (e.g., full USDA FoodData Central distributions), NutriVault supports dynamic schema attachment:
```python
conn.execute("ATTACH DATABASE 'data/usda_reference.db' AS usda_reference;")
```
The `GroundingEngine` dynamically probes attached schemas via `PRAGMA database_list` and table schemas via `PRAGMA table_info(usda_foods)`.

---

## 5. REST API Developer Reference & `curl` Examples

### 1. Hardware Inspection (`GET /api/v1/hardware`)
```bash
curl -s http://localhost:8080/api/v1/hardware | jq
```

### 2. Full Offline Catalog Export (`GET /api/v1/foods/catalog`)
```bash
curl -s http://localhost:8080/api/v1/foods/catalog | jq '.items[0]'
```

### 3. Barcode Lookup with Portion Scaling (`GET /api/v1/foods/barcode/{code}`)
```bash
# Quaker Oats (0030000010204) scaled to 200 grams
curl -s "http://localhost:8080/api/v1/foods/barcode/0030000010204?grams=200" | jq
```

### 4. Custom Barcode Registration (`PUT /api/v1/foods/barcode/{code}`)
```bash
curl -s -X PUT http://localhost:8080/api/v1/foods/barcode/078742351896 \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Nonfat Greek Yogurt",
    "calories_per_100g": 59.0,
    "protein_g_per_100g": 10.0,
    "carbs_g_per_100g": 3.6,
    "fat_g_per_100g": 0.4,
    "fiber_g_per_100g": 0.0,
    "micros_per_100g": {"calcium_mg": 110.0}
  }' | jq
```

### 5. Offline Batch Synchronization (`POST /api/v1/sync/batch`)
```bash
curl -s -X POST http://localhost:8080/api/v1/sync/batch \
  -H "Content-Type: application/json" \
  -d '{
    "queued_meals": [
      {
        "dish_name": "Offline Oatmeal",
        "ingredients": [
          {
            "item_name": "Rolled Oats",
            "fdc_id": 2001,
            "grams": 80.0,
            "calories": 303.2,
            "protein_g": 10.5,
            "carbs_g": 54.2,
            "fat_g": 5.2,
            "fiber_g": 8.0,
            "micros": {}
          }
        ],
        "allocations": [
          {
            "profile_id": "profile-uuid-here",
            "fraction": 1.0,
            "meal_type": "breakfast",
            "logged_at": "2026-11-08T08:30:00"
          }
        ]
      }
    ],
    "queued_barcodes": [
      {
        "barcode": "0030000010204",
        "grams": 100.0,
        "dish_name": "Scanned Oatmeal",
        "allocations": [
          {
            "profile_id": "profile-uuid-here",
            "fraction": 1.0,
            "meal_type": "snack",
            "logged_at": "2026-11-08T15:00:00"
          }
        ]
      }
    ]
  }' | jq
```

### 6. Ephemeral Image Analysis (`POST /api/v1/meals/parse-image`)
```bash
# Upload image directly as multipart form data
curl -s -X POST http://localhost:8080/api/v1/meals/parse-image \
  -F "image=@meal.jpg" | jq
```

---

## 6. Local VLM Inference Debugging (`llama-server`)

To run vision extraction independently without Docker Compose:

```bash
# Tier 1 (CPU / low memory): SmolVLM-500M (~550 MB)
llama-server \
  --hf-repo ggml-org/SmolVLM-500M-Instruct-GGUF \
  --hf-file SmolVLM-500M-Instruct-Q8_0.gguf \
  --port 8081 \
  --host 127.0.0.1

# Tier 2 (GPU >= 6GB / Mac >= 16GB): Qwen2.5-VL-3B (~2200 MB)
llama-server \
  --hf-repo ggml-org/Qwen2.5-VL-3B-Instruct-GGUF \
  --hf-file Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf \
  --port 8081 \
  --host 127.0.0.1
```
