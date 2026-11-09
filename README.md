# NutriVault 🥗🔒

> **Local-First Personal and Family Nutrition Tracker**  
> Double-click desktop launch, offline-first mobile PWA ("Snap & Sync Later"), 3-tier grocery barcode scanner, ephemeral in-memory meal photo AI (`0x00` purge), deterministic USDA grounding, and fractional family batch cooking with zero cloud telemetry.

---

## 🌟 Key Highlights

* **True Double-Click Start (Zero Terminal Needed):** Download the ZIP, unzip it, and launch **`Start_NutriVault.command`** (Mac), **`Start_NutriVault.bat`** (Windows), or **`Start_NutriVault.sh`** (Linux). Your browser opens automatically to `http://localhost:8080` and displays your exact **`📱 Phone Wi-Fi Link`** right at the top of the screen.
* **100% Offline & Private:** Zero cloud SDKs, zero ads, zero telemetry. Operates locally on your home computer, private network, or completely offline on your mobile device.
* **Turnkey Mobile PWA ("Snap & Sync Later"):** Installs in seconds on iPhone Safari and Android Chrome via *"Add to Home Screen"*. Log meals, snap restaurant photos, and scan barcodes while travelling away from your computer; your phone queues items locally with their original timestamps and automatically syncs when reconnected.
* **3-Tier Grocery Barcode Scanner:**
  * **Tier 1:** Instant (<10 ms) offline phone lookups from local IndexedDB cache.
  * **Tier 2:** Live home server lookup (or deferred offline barcode queue when away from home).
  * **Tier 3:** 1-tap custom barcode registration from package nutrition labels—cached permanently for future offline scans.
* **Ephemeral In-Memory Photo Lifecycle:** Meal photographs are analyzed strictly in volatile RAM (`io.BytesIO`, 15 MB pre-allocation guard). Images are never saved to server disk or swap, and memory buffers are overwritten with `0x00` and purged immediately upon review or error.
* **Neuro-Symbolic Grounding:** The local Vision-Language Model (VLM) is strictly an entity and portion estimator—never an arithmetic calculator. Nutritional values are deterministically scaled from local USDA tables:
  $$\text{Nutrient}_{\text{resolved}} = \text{Nutrient}_{\text{USDA}} \times \left( \frac{\text{grams}}{100.0} \right)$$
* **Family Batch Cooking Splitter:** Cook a shared dish once (casseroles, stews, roasts) and distribute fractional portions across household members atomically in a single click.
* **Clinical & Athletic Safeguards:**
  * Strict lock preventing automated AI goals on chronic condition profiles (`ERR_CLINICAL_AI_RESTRICTED`, HTTP 403).
  * Explicit advisory wire for athletic training targets citing certified trainers and privacy-preserving endpoints (`search.brave.com/ask`).
* **Predefined Small VLMs:** Ships with a hardware-matched catalog (`SmolVLM-500M-Instruct-Q8_0` ~550 MB default, `Qwen2.5-VL-3B`, `Qwen2.5-VL-7B`) so you never have to hunt for `.gguf` files manually.

---

## 🚀 60-Second Quickstart (For Everyday Users)

1. **Download:** Click **[Download NutriVault (.zip)](https://github.com/codeja3/NutriVault/archive/refs/heads/main.zip)** and unzip the folder in your `Downloads`.
2. **Double-Click to Start:**
   * **Mac:** Double-click **`Start_NutriVault.command`** inside the unzipped folder.
   * **Windows:** Double-click **`Start_NutriVault.bat`** inside the unzipped folder.
   * **Linux:** Right-click **`Start_NutriVault.sh`** and select **"Run as a Program"** (or double-click it).
3. **Start Logging:** Your web browser opens **`http://localhost:8080`** automatically, and displays your **`📱 Phone Wi-Fi Link`** at the top of the screen so you can add NutriVault to your phone's home screen!

*(Prefer Docker? Simply run `docker compose up` inside the folder to launch NutriVault + the preconfigured `SmolVLM-500M` Camera AI sidecar simultaneously.)*

---

## 📚 Role-Separated Guides & Documentation

Choose the guide that matches your needs:

* 👤 **[User Manual (`MANUAL.md`)](MANUAL.md):** Step-by-step, jargon-free guide for everyday individuals and families. Covers downloading the ZIP, double-clicking to start on Mac/Windows, adding the app to your phone via the on-screen `📱 Phone Wi-Fi Link`, scanning grocery barcodes, and using "Snap & Sync Later" at restaurants.
* 🛠️ **[Developer Manual (`DEV_MANUAL.md`)](DEV_MANUAL.md):** Dedicated technical reference for developers. Covers the `uv` toolchain, TDD workflow, module architecture (`src/`), SQLite schema DDL & dual-DB attachment, `0x00` volatile memory purge guarantees, `curl` REST API reference, and `llama-server` debugging.
* 📋 **[Technical Specification (`SPEC.md`)](SPEC.md):** Complete formal specifications, REST schemas, and error codes.
* 🎯 **[Product Requirements (`PRD.md`)](PRD.md):** Product scope, user personas, and target envelopes.
* 🤖 **[Agent Directives (`AGENTS.md`)](AGENTS.md):** Autonomous developer directives and quality standards.
* 🧠 **[Architecture Memory (`MEMORY.md`)](MEMORY.md):** Decision log and architectural invariants.
* ✅ **[Task Checklist (`TODO.md`)](TODO.md):** Step-by-step TDD implementation checklist.

---

## 📄 License

Licensed under the MIT License.
