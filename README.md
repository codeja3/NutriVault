# NutriVault 🥗🔒

> **Local-First Personal and Family Nutrition Tracker**  
> Ephemeral in-memory multimodal vision, deterministic USDA grounding, and fractional batch cooking allocations with zero cloud telemetry.

---

## 🌟 Key Highlights

* **100% Offline & Private:** Zero cloud SDKs, zero telemetry, zero analytics. Runs entirely on your local machine over your home LAN (`http://nutrivault.local:8080`).
* **Ephemeral In-Memory Media Lifecycle:** Meal photographs are held strictly in volatile RAM (`io.BytesIO`, 15 MB pre-allocation guard). Raw food photos are never written to disk, caches, or swap, and all underlying memory buffers are deterministically overwritten with `0x00` bytes and purged immediately upon review or error.
* **Neuro-Symbolic Grounding:** The local Vision-Language Model (VLM) is strictly an entity and portion estimator—never an arithmetic calculator. Nutritional values are deterministically scaled from local USDA FoodData Central reference tables with in-memory token caching.
* **Family Batch Cooking Workflows:** Log a large cooked dish once (casserole, stew, stir-fry) and distribute fractional portion percentages ($\le 100\%$) across multiple household members atomically in a single SQLite transaction.
* **Clinical Safeguards & Advisory Wires:**
  * Hard lock preventing automated AI target generation or AI target envelope commits on chronic condition profiles (`ERR_CLINICAL_AI_RESTRICTED`, HTTP 403).
  * Mandatory advisory wire and explicit client acknowledgment (`acknowledged: true`) for athletic AI targets, recommending verification with certified trainers and privacy-preserving frontier endpoints (`search.brave.com/ask`).
* **Dynamic Hardware Profiling:** Auto-detects host RAM, VRAM, and Apple Silicon/CUDA acceleration to gate allowable model tiers (`tier_1_cpu`, `tier_2_mid`, `tier_3_high`).

---

## 🛠️ Tech Stack & Requirements

* **Python Runtime:** Python 3.11+ strictly.
* **Package & Environment Manager:** [`uv`](https://github.com/astral-sh/uv).
* **Storage Engine:** Standard library `sqlite3` operating in WAL (`Write-Ahead Logging`) mode with foreign keys enabled and thread-safe request serialization.
* **Local Inference:** Embedded `llama.cpp` (`llama-server`) running over a dedicated local loopback socket (`http://127.0.0.1:8081/v1/chat/completions`) with strict SSRF loopback validation.

---

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have either `docker` or `uv` installed:
```bash
# Option A: Install uv for local execution (macOS / Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Option A: Turnkey Docker Container (60-Second Onboarding)

Launch the complete application with pre-seeded USDA foods and persistent local storage in a single command:
```bash
docker compose up
```
Open **`http://localhost:8080`** in your browser. NutriVault is immediately ready to log meals via the instant USDA search bar—no local model downloads required!

### 3. Option B: Local Python Development

```bash
git clone https://github.com/codeja3/NutriVault.git
cd NutriVault

# Create virtual environment and install dependencies via uv
uv venv
source .venv/bin/activate
uv sync

# Starts the NutriVault server on 0.0.0.0:8080 (auto-seeds default USDA catalog)
uv run python -m src.api
```
Open **`http://localhost:8080`** in any desktop or mobile browser.

### 4. Optional: Local Vision Model Setup Guide

To enable ephemeral food photo analysis with local inference:
```bash
uv run python -m src.api --vlm-guide
```
This inspects your machine's CPU/RAM/VRAM/Metal/CUDA capabilities, resolves your allowable model tier (`tier_1_cpu`, `tier_2_mid`, `tier_3_high`), and prints the exact `llama-server` loopback command.

### 5. Run the Test Suite

NutriVault features a 100% offline, hermetic test suite executing against in-memory SQLite fixtures:

```bash
uv run pytest
```

### 6. Code Quality & Linting

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
