# NutriVault User & Operator Manual 📖

Welcome to **NutriVault**, your local-first, privacy-respecting nutrition tracker. This manual explains how to install, configure, operate, and query NutriVault on your home workstation or server.

---

## Table of Contents

1. [Hardware Requirements & Model Tiers](#1-hardware-requirements--model-tiers)
2. [Installation & Setup](#2-installation--setup)
3. [Running the Backend Service](#3-running-the-backend-service)
4. [Using the Application](#4-using-the-application)
   - [Managing Household Profiles](#41-managing-household-profiles)
   - [Setting Nutrition Target Envelopes](#42-setting-nutrition-target-envelopes)
   - [Logging a Meal via Ephemeral Photo](#43-logging-a-meal-via-ephemeral-photo)
   - [Batch Cooking & Fractional Family Splitting](#44-batch-cooking--fractional-family-splitting)
   - [Viewing Rolling Analytics & Fasting Windows](#45-viewing-rolling-analytics--fasting-windows)
5. [Clinical & Athletic Advisory Guidelines](#5-clinical--athletic-advisory-guidelines)
6. [Database Backup & Maintenance](#6-database-backup--maintenance)
7. [REST API Reference Summary](#7-rest-api-reference-summary)

---

## 1. Hardware Requirements & Model Tiers

NutriVault automatically probes your host compute specs on launch to prevent out-of-memory crashes:

| Tier | Hardware Prerequisites | Allowable Vision Models | Example Hardware |
| :--- | :--- | :--- | :--- |
| **`tier_1_cpu`** | CPU-only, $<6\text{ GB}$ dedicated VRAM, or $<16\text{ GB}$ RAM | $\le 4\text{B}$ quantized models | Older PCs, Intel/M1 8GB Macs, budget laptops (SmolVLM, Moondream2) |
| **`tier_2_mid`** | Dedicated GPU $\ge 6\text{ GB}$ VRAM, or Apple Silicon $\ge 16\text{ GB}$ RAM | $7\text{B}\text{--}9\text{B}$ models (Q4) | RTX 3060/4060, M1/M2/M3 Pro 16GB (Qwen2.5-VL 7B Q4) |
| **`tier_3_high`** | Dedicated GPU $\ge 16\text{ GB}$ VRAM, or Apple Silicon $\ge 32\text{ GB}$ RAM | $14\text{B}+$ models | RTX 3090/4090, Apple Silicon 32GB+ (Qwen2.5-VL 14B/72B) |

---

## 2. Installation & Setup

### Prerequisites
* **Operating System:** macOS, Linux, or Windows (WSL2 recommended).
* **Python:** 3.11 or newer.
* **Package Tool:** `uv` is required.

### Setup Instructions

```bash
# 1. Clone repository
git clone https://github.com/your-username/NutriVault.git
cd NutriVault

# 2. Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Synchronize project dependencies
uv sync

# 4. Verify test suite
uv run pytest
```

---

## 3. Running the Backend Service

### Option A: Local Python API Service
NutriVault exposes a high-performance REST API and local router:

```bash
uv run python -m src.api
```

### Option B: Local Inference Engine (`llama-server`)
If you want to run multimodal vision extraction locally, launch `llama-server` on loopback:

```bash
# Example for Tier 2 mid-spec (e.g. Qwen2.5-VL 7B):
./llama-server -m ./models/qwen2.5-vl-7b-instruct-q4_k_m.gguf \
  --mmproj ./models/qwen2.5-vl-7b-mmproj-f16.gguf \
  --port 8080 --host 127.0.0.1
```

NutriVault automatically points to `http://127.0.0.1:8080/v1/chat/completions` to extract food entities and portions.

---

## 4. Using the Application

### 4.1 Managing Household Profiles

NutriVault is designed for households with diverse nutritional demands:

* **Standard Profile:** Everyday balanced wellness and maintenance.
* **Athletic Profile:** Marathon runners, lifters, cyclists with body composition goals.
* **Chronic Condition Profile:** Crohn's disease, Lupus, CKD, or metabolic restrictions where diet directly affects medical outcomes.

#### Creating a Profile (via API / Web Interface)
```bash
curl -X POST http://localhost:8080/api/v1/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alex",
    "profile_type": "athletic",
    "birth_date": "1992-06-15",
    "condition_notes": "Marathon training"
  }'
```

---

### 4.2 Setting Nutrition Target Envelopes

Set active daily targets for calories, macros, and micronutrients:

```bash
curl -X PUT http://localhost:8080/api/v1/profiles/{profile_id}/targets \
  -H "Content-Type: application/json" \
  -d '{
    "calories_target": 2400,
    "protein_g_target": 160.0,
    "carbs_g_target": 280.0,
    "fat_g_target": 70.0,
    "fiber_g_target": 35.0,
    "micronutrients": {"iron_mg": 18.0, "calcium_mg": 1000.0}
  }'
```

*Note: Previous target envelopes are preserved as inactive history, ensuring accurate longitudinal analytics.*

---

### 4.3 Logging a Meal via Ephemeral Photo

1. Open the mobile or desktop web interface over your local LAN.
2. Snap or upload a photo of your meal.
3. The image is parsed in **volatile RAM (`io.BytesIO`)** with **zero disk writes**.
4. The local VLM extracts the items and estimates portion grams:
   ```json
   [
     {"item_name": "steamed brown rice", "estimated_grams": 200.0},
     {"item_name": "grilled chicken breast", "estimated_grams": 150.0}
   ]
   ```
5. NutriVault matches candidate food items to the static **USDA FoodData Central** reference table and calculates exact linear nutrients.
6. The user confirms, tweaks portion sizes, or adds ingredients, then taps **"Commit"**.
7. The image bytes are **purged immediately from memory**.

---

### 4.4 Batch Cooking & Fractional Family Splitting

One of NutriVault's unique features is handling **cook-once shared dishes**:

1. **Cook:** The household cook prepares a large batch of pasta or casserole.
2. **Log Dish:** The dish is logged once (`dishes` table) with total ingredient weights.
3. **Allocate Fractions:** The cook distributes portions using interactive sliders:
   * Parent A: `40%` (`0.4`)
   * Parent B: `40%` (`0.4`)
   * Child: `20%` (`0.2`)
4. **Commit:** NutriVault calculates individual calories and macros for each member and logs distinct records to their journals atomically.
5. **Leftover Support:** Total portions can sum to less than 1.0 (e.g., `0.7` consumed, leaving `0.3` for next day leftovers).

---

### 4.5 Viewing Rolling Analytics & Fasting Windows

NutriVault provides rolling analytics and chrononutrition metrics without sending data to third parties:

```bash
curl "http://localhost:8080/api/v1/analytics/rolling?profile_id={profile_id}&days=7"
```

**Response includes:**
* **7-Day Rolling Exponential Moving Averages (EMA):** Smooths daily caloric and macronutrient fluctuations.
* **Target Adherence Deltas:** Exact differences between EMA and your active target envelope ($\Delta = \text{EMA} - \text{Target}$).
* **Daily Feeding Windows:** Time elapsed from first meal to last meal each day.
* **Overnight Fasting Intervals:** Exact fasting hours between yesterday's dinner and today's breakfast.

---

## 5. Clinical & Athletic Advisory Guidelines

NutriVault incorporates strict ethical and safety guardrails:

### Clinical Hard Lock (`ERR_CLINICAL_AI_RESTRICTED`)
* Any profile tagged with `profile_type == 'chronic_condition'` **strictly blocks** automated AI goal generation.
* The system enforces this mandatory clinical notice:
  > *"Nutritional goals for chronic conditions must be established in consultation with a qualified physician or registered dietitian. NutriVault does not provide clinical diagnoses or therapeutic prescriptions."*

### Athletic Advisory Wire
* Fitness and body-composition targets generated via local AI prompts must bundle the following advisory wire:
  > *"Local model fitness baselines are heuristic estimates. For rigorous training regimens or metabolic adjustments, consult a certified fitness trainer or cross-reference using privacy-preserving frontier endpoints (e.g., search.brave.com/ask)."*
* Requires explicit user acknowledgment before applying targets.

---

## 6. Database Backup & Maintenance

NutriVault stores all user data in standard, unencrypted SQLite database files with WAL mode enabled:

* **`data/nutrivault.db`:** User profiles, target envelopes, shared dishes, and meal journals.
* **`data/usda_reference.db`:** Static read-only USDA reference table.

### Creating a Safe Backup
To create a live, consistent snapshot while the daemon is running:
```bash
sqlite3 data/nutrivault.db ".backup data/nutrivault_backup.db"
```

---

## 7. REST API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/hardware` | Returns detected compute specs and active tier ceiling. |
| `GET` | `/api/v1/profiles` | Lists all active household profiles. |
| `POST` | `/api/v1/profiles` | Creates a new profile. |
| `PUT` | `/api/v1/profiles/{id}/targets` | Sets active target envelope (atomically deactivating old). |
| `POST` | `/api/v1/advisory/fitness-targets` | Generates athletic targets with advisory wire (or 403 on clinical). |
| `POST` | `/api/v1/meals/parse-image` | Multipart in-memory VLM image parsing and USDA grounding. |
| `POST` | `/api/v1/meals/commit` | Persists shared dish and logs fractional portions to family members. |
| `GET` | `/api/v1/analytics/rolling` | Computes 7-day EMA, target deltas, and feeding/fasting intervals. |
