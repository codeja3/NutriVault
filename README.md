# NutriVault 🥗🔒

> **Local-First Personal and Family Nutrition Tracker**  
> Ephemeral in-memory multimodal vision, deterministic USDA grounding, and fractional batch cooking allocations with zero cloud telemetry.

---

## 🌟 Key Highlights

* **100% Offline & Private:** Zero cloud SDKs, zero telemetry, zero analytics. Runs entirely on your local machine over your home LAN (`http://nutrivault.local:8080`).
* **Ephemeral In-Memory Media Lifecycle:** Meal photographs are held strictly in volatile RAM (`io.BytesIO`). Raw food photos are never written to disk, caches, or swap and are purged immediately upon review or cancellation.
* **Neuro-Symbolic Grounding:** The local Vision-Language Model (VLM) is strictly an entity and portion estimator—never an arithmetic calculator. Nutritional values are deterministically scaled from local USDA FoodData Central reference tables.
* **Family Batch Cooking Workflows:** Log a large cooked dish once (casserole, stew, stir-fry) and distribute fractional portion percentages ($\le 100\%$) across multiple household members with divergent fitness, athletic, or health goals.
* **Clinical Safeguards & Advisory Wires:**
  * Hard lock preventing automated AI target generation on chronic condition profiles (`ERR_CLINICAL_AI_RESTRICTED`).
  * Advisory wire for athletic targets recommending verification with certified trainers and privacy-preserving frontier endpoints (`search.brave.com/ask`).
* **Dynamic Hardware Profiling:** Auto-detects host RAM, VRAM, and Apple Silicon/CUDA acceleration to gate allowable model tiers (`tier_1_cpu`, `tier_2_mid`, `tier_3_high`).

---

## 🛠️ Tech Stack & Requirements

* **Python Runtime:** Python 3.11+ strictly.
* **Package & Environment Manager:** [`uv`](https://github.com/astral-sh/uv).
* **Storage Engine:** Standard library `sqlite3` operating in WAL (`Write-Ahead Logging`) mode with foreign keys enabled.
* **Local Inference:** Embedded `llama.cpp` (`llama-server`) running over a local loopback socket.

---

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have `uv` installed:
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone & Setup Environment

```bash
git clone https://github.com/your-username/NutriVault.git
cd NutriVault

# Create virtual environment and install dependencies via uv
uv venv
source .venv/bin/activate
uv sync
```

### 3. Run the Test Suite

NutriVault features a 100% offline, hermetic test suite executing against in-memory SQLite fixtures:

```bash
uv run pytest
```

### 4. Code Quality & Linting

```bash
uv run ruff check .
uv run ruff format --check .
```

---

## 📖 Documentation & Architecture

* **[MANUAL.md](MANUAL.md):** User guide covering installation, starting the local daemon, family profiles, meal logging, and analytics.
* **[SPEC.md](SPEC.md):** Complete technical specifications, REST API schemas, and SQLite DDL.
* **[PRD.md](PRD.md):** Product requirements, user personas, and non-functional requirements.
* **[AGENTS.md](AGENTS.md):** Project standards, autonomous agent directives, and development rules.
* **[MEMORY.md](MEMORY.md):** Architectural decision log and invariants.
* **[TODO.md](TODO.md):** Completed TDD task checklist.

---

## 📄 License

Open-source under the MIT License.
