# NutriVault 🥗🔒

> **Local-First Personal and Family Nutrition Tracker**  
> Offline-first mobile PWA, 3-tier grocery barcode scanner, ephemeral in-memory meal photo AI, deterministic USDA grounding, and fractional family batch cooking with zero cloud telemetry.

---

## 🌟 Key Highlights

* **100% Offline & Private:** Zero cloud SDKs, zero ads, zero telemetry. Operates locally on your home computer, private network, or completely offline on your mobile device.
* **Turnkey Mobile PWA ("Snap & Sync Later"):** Installs instantly on iPhone Safari and Android Chrome as a full-screen app. Log meals, scan barcodes, and track nutrition while travelling or at restaurants away from home; your phone queues meals locally with timestamps and automatically syncs when reconnected.
* **3-Tier Grocery Barcode Scanner:**
  * **Tier 1:** Instant (<10 ms) offline phone lookups from local IndexedDB cache.
  * **Tier 2:** Query local home server database.
  * **Tier 3:** 1-tap custom barcode registration for packaged foods from package nutrition labels.
* **Ephemeral In-Memory Photo Lifecycle:** Meal photographs are analyzed strictly in volatile RAM (`io.BytesIO`, 15 MB pre-allocation guard). Images are never saved to disk, caches, or swap, and memory buffers are overwritten with `0x00` and purged immediately upon review or error.
* **Neuro-Symbolic Grounding:** The local Vision-Language Model (VLM) is strictly an entity and portion estimator—never an arithmetic calculator. Nutritional values are deterministically scaled from local USDA tables:
  $$\text{Nutrient}_{\text{resolved}} = \text{Nutrient}_{\text{USDA}} \times \left( \frac{\text{grams}}{100.0} \right)$$
* **Family Batch Cooking Splitter:** Cook a large dish once (casseroles, stews, roasts) and distribute fractional portions across household members atomically in a single click.
* **Clinical & Athletic Safeguards:**
  * Strict lock preventing automated AI goals on chronic condition profiles (`ERR_CLINICAL_AI_RESTRICTED`, HTTP 403).
  * Explicit advisory wire for athletic training targets citing certified trainers and privacy-preserving endpoints (`search.brave.com/ask`).
* **Turnkey Hardware Profiling:** Auto-detects host RAM, VRAM, and GPU backend to recommend pre-packaged small VLMs (`SmolVLM-500M`, `Qwen2.5-VL-3B`, `Qwen2.5-VL-7B`).

---

## 🚀 60-Second Quickstart

Launch the complete application with pre-seeded staple foods and persistent local storage in a single command:

```bash
docker compose up
```

Open **`http://localhost:8080`** in your browser. NutriVault is immediately ready to log meals via instant text search, mobile barcode scanning, or camera photos!

---

## 📚 Role-Separated Guides & Documentation

Choose the guide that matches your needs:

* 👤 **[User Manual (`MANUAL.md`)](MANUAL.md):** Plain-English, jargon-free guide for everyday individuals and families. Covers installing the phone app ("Add to Home Screen"), logging meals, scanning grocery barcodes, using "Snap & Sync Later" at restaurants, and backing up your database.
* 🛠️ **[Developer Manual (`DEV_MANUAL.md`)](DEV_MANUAL.md):** Dedicated technical reference for developers. Covers the `uv` toolchain, TDD workflow, module architecture (`src/`), SQLite schema DDL & dual-DB attachment, `0x00` volatile memory purge guarantees, `curl` REST API reference, and `llama-server` debugging.
* 📋 **[Technical Specification (`SPEC.md`)](SPEC.md):** Complete formal specifications, REST schemas, and error codes.
* 🎯 **[Product Requirements (`PRD.md`)](PRD.md):** Product scope, user personas, and target envelopes.
* 🤖 **[Agent Directives (`AGENTS.md`)](AGENTS.md):** Autonomous developer directives and quality standards.
* 🧠 **[Architecture Memory (`MEMORY.md`)](MEMORY.md):** Decision log and architectural invariants.
* ✅ **[Task Checklist (`TODO.md`)](TODO.md):** Step-by-step TDD implementation checklist.

---

## 💻 Developer Quickstart (`uv`)

```bash
# Clone repository
git clone https://github.com/codeja3/NutriVault.git
cd NutriVault

# Install dependencies and activate virtual environment via uv
uv venv
source .venv/bin/activate
uv sync

# Run the 100% offline hermetic test suite
uv run pytest

# Run automated formatting and linting
uv run ruff check .
uv run ruff format .

# Start the local daemon
uv run python -m src.api
```

---

## 📄 License

Licensed under the MIT License.
