# Product Requirements Document (PRD)

**Project Name:** NutriVault  
**Subtitle:** Local-First Personal and Family Nutrition Tracker  
**Status:** Approved & Locked  
**Version:** 1.4.0  

---

## 1. Problem Statement
Commercial nutritional tracking applications systematically compromise user data sovereignty through continuous cloud telemetry, paywall foundational features behind recurring subscriptions, and monetize personal meal photographs by feeding them into proprietary model-training pipelines. Furthermore, existing open-source and privacy-focused trackers remain strictly manual, offering zero multimodal vision capabilities and lacking practical workflows for home-cooked family meals where a single dish is prepared and split unevenly across household members with divergent fitness, athletic, or chronic health demands.

At the same time, local-first privacy tools often suffer from three adoption barriers for everyday non-technical users:
1. **Setup & Model Selection Friction:** Expecting users to install developer toolchains (`git`, `uv`, Python), manually hunt for compatible `.gguf` and multimodal projector (`mmproj`) weights, and run multi-flag CLI inference servers.
2. **Away-from-Home Disconnection:** When a user is dining at a restaurant, travelling on the road away from their laptop, or in a grocery store with poor reception, a purely LAN-tethered web app becomes unreachable.
3. **In-Store Grocery Friction:** Scanning packaged food barcodes in a grocery aisle requires instant camera barcode recognition that works gracefully even when the user's phone is offline.

## 2. Objective & Core Value Proposition
NutriVault is an open-source, local-first "one-stop shop" nutritional tracking and analytics system designed to be approachable by any user in under 60 seconds—both at home and on the go. It combines:
* A **zero-configuration, offline-capable Progressive Web App (PWA)** with Service Worker and IndexedDB queuing (**"Snap & Sync Later"**).
* **Predefined, hardware-matched small VLM profiles** (defaulting to the ultra-lightweight `SmolVLM-500M-Instruct` for universal CPU/Docker operation) so users never have to choose or manually configure model weights.
* **In-browser camera barcode scanning** with a 3-tier graceful offline resolution architecture (Phone IndexedDB Cache $\rightarrow$ Local SQLite Lookup $\rightarrow$ Deferred Offline Barcode Queue & 1-Tap Custom Barcode Mapping).
* **Ephemeral in-memory vision processing (`0x00` purge)**, deterministic USDA grounding, multi-member family batch portion allocation, clinical/athletic advisory safeguards, and rolling 7-day chrononutrition analytics.

## 3. Non-Negotiables & Guiding Principles
* **Strict Privacy & Zero Data Exfiltration:** Zero analytics SDKs, zero telemetry, zero fingerprinting, and zero cloud services in the data path.
* **Transient Media Lifecycle:** Images processed by the backend are held exclusively in volatile memory buffers (`io.BytesIO`) and overwritten with `0x00` bytes upon completion. Under no circumstances are raw food photos persisted to server disk, swap, or external cloud storage.
* **Neuro-Symbolic Grounding:** The local vision model functions strictly as an entity and portion extractor, never an arithmetic calculator. Nutritional calculations are deterministically computed using embedded reference tables (USDA FoodData Central & verified local barcode mappings) to prevent model hallucinations.
* **One-Stop-Shop Onboarding ("Zero Jargon & Double-Click Launch"):** The application ships with native double-click desktop launchers (`Start_NutriVault.command` for macOS Finder, `Start_NutriVault.bat` for Windows Explorer, and `Start_NutriVault.sh` for Linux) that automatically start the server and open the user's web browser (`--open-browser`), displays the host computer's exact home Wi-Fi link (`local_lan_url`) right inside the web app header for effortless phone pairing, seeds a starter USDA & barcode catalog automatically, and separates end-user documentation (`MANUAL.md`, including clean uninstallation instructions) from developer internals (`DEV_MANUAL.md`).
* **Offline-First Mobility ("Snap & Sync Later" + Optional P2P Live Access):** Users can capture meal photos, scan grocery barcodes, and log meals on their phone while completely offline (at a restaurant, grocery store, or travelling) and automatically synchronize with their host laptop/server upon reconnection—or optionally use a zero-config P2P VPN sidecar (e.g., Tailscale) for live remote VLM inference.
* **Household Data Sovereignty:** Complete user ownership of all data via standard, unencrypted SQLite files, enabling direct queryability, custom scripting, and local statistical analysis.

---

## 4. User Personas & Use Cases

### 4.1 Personas
* **Everyday Privacy-Conscious User (On-the-Go & At-Home):** Wants a turnkey app that works on their phone at home, at a restaurant, or in a grocery store aisle without knowing what `uv`, `git`, `.gguf`, or `mmproj` mean.
* **Primary Cook / Parent:** Plans and prepares meals for the household; needs to log a single cooked batch once and distribute realistic portion percentages to individual family members without re-entering ingredients per person.
* **Endurance Athlete / Runner:** Prioritizes high carbohydrate availability around training windows, electrolyte replenishment (sodium, potassium, magnesium), iron maintenance, and glycogen replenishment curves.
* **Hypertrophy Athlete / Bodybuilder:** Tracks precise protein-to-bodyweight ratios ($\text{g/kg}$), progressive caloric surpluses or deficits, and consistent multi-meal daily distributions.
* **Chronic Condition Manager (e.g., Crohn's Disease, Lupus / Autoimmune, CKD):** Relies on strict micro/macronutrient and ingredient tracking to manage inflammation, flare-up triggers, specific electrolyte limits (e.g., potassium/phosphorus in kidney concerns), or high-fiber versus low-residue phases where diet and clinical outcomes are tightly coupled.
* **Household Member / Child:** Consumes meals logged by the primary cook; views individual daily targets and intakes on a shared tablet or personal smartphone.

### 4.2 Core User Journeys
1. **Zero-VLM Instant Search Logging (Day-1 Onboarding):** A user launches NutriVault, opens `http://localhost:8080`, searches `"brown rice"` and `"roasted chicken breast"`, adjusts gram weights, and commits their first meal in under 60 seconds.
2. **Restaurant / Travel "Snap & Sync Later" (Offline Mode):** While dining out or travelling away from their laptop, a user opens the installed NutriVault PWA on their phone (loaded offline via Service Worker), snaps a photo of their meal (or queues items), records the exact meal timestamp, and taps **"Queue for Sync"**. When they return to their laptop/home Wi-Fi, the PWA automatically syncs the queue, runs VLM/USDA resolution, logs the meal with its original restaurant timestamp, and purges the image buffer.
3. **Grocery Store Barcode Scanning (Online & Offline):** In a supermarket aisle (even without connection to their home laptop), a user opens the in-browser camera barcode scanner:
   * *Tier 1 (Cached Barcode):* If the barcode is in the phone's local IndexedDB cache, nutrients appear in $<10\text{ ms}$ offline.
   * *Tier 2 (Deferred Offline Scan):* If the phone is offline and the barcode is brand-new, the scan (`[barcode, grams, timestamp]`) is saved to the offline queue and automatically resolved against the server database when reconnected.
   * *Tier 3 (Custom Barcode Registration):* If a local store barcode is unrecognized, the user maps it once to a USDA item or nutrition label (`PUT /api/v1/foods/barcode/{code}`), caching it permanently for future offline scans.
4. **Single-Dish Family Logging:** The cook takes a photo of a freshly prepared casserole (or searches/scans ingredients), confirms the detected ingredients and weights, assigns fractional allocations via interactive sliders (e.g., Parent A: 40%, Parent B: 40%, Child: 20%), commits the meal to the ledger, and the system purges the image.
5. **Multi-Profile Goal & Target Configuration:** A user sets granular micro- and macro-nutrient targets for themselves and each individual family member in the web UI, switching between clinical presets, athletic templates, or customized numeric limits.
6. **Local Nutritional Analysis:** A user opens the dashboard to review rolling 7-day nutrient moving averages, micronutrient target adherence, and temporal eating/fasting windows.

---

## 5. Scope Boundaries

### 5.1 In-Scope
* **Built-In Offline-First Progressive Web App (PWA) & Service Worker (`GET /`, `GET /manifest.json`, `GET /sw.js`):** Self-contained HTML5/CSS3/ES6 web application with Service Worker asset caching and IndexedDB offline storage (`offline_foods_cache` and `offline_sync_queue`).
* **In-Browser Camera Barcode Scanner & 3-Tier Offline Barcode Resolution:** Native `BarcodeDetector` camera scanning UI (with manual entry fallback), SQLite `usda_foods.barcode` indexing, barcode lookup (`GET /api/v1/foods/barcode/{code}`), custom barcode registration (`PUT /api/v1/foods/barcode/{code}`), and batch offline queue synchronization (`POST /api/v1/sync/batch`).
* **Predefined Hardware-Matched VLM Catalog & Turnkey Sidecar:** Hardcoded, checksum-pinned VLM registry (`PREDEFINED_VLM_CATALOG`) mapping each hardware tier to an exact default small VLM (`SmolVLM-500M-Instruct-Q8_0` for `tier_1_cpu`, `Qwen2.5-VL-3B-Instruct-Q4_K_M` for `tier_2_mid`, `Qwen2.5-VL-7B-Instruct-Q4_K_M` for `tier_3_high`), automatic `llama-server --hf-repo` command synthesis, and a turnkey `docker-compose.yml` bundling both NutriVault and the local VLM sidecar (plus an optional P2P remote access profile).
* **Out-of-the-Box Curated USDA Starter Seed (with Barcodes) & Search API:** Pre-populated USDA reference foods (including common UPC/EAN barcodes) on first launch plus a live search and portion-scaling endpoint (`/api/v1/foods/search`).
* **In-Memory Vision Pipeline:** Direct integration with an embedded local inference engine (`llama.cpp` / loopback REST on `:8081`) receiving in-memory multipart image streams and executing `0x00` volatile buffer purges.
* **Family Profiles & Batch Splitting:** Support for multiple user profiles under a single household, each with customizable DRI/RDA baselines, plus a fractional portion allocator ($\sum \text{fractions} \le 1.0$).
* **Clinical Disclaimers & Local AI Fitness Advisor:** Mandatory clinical hard lock (`ERR_CLINICAL_AI_RESTRICTED` / HTTP 403) on `chronic_condition` profiles and mandatory trainer/`search.brave.com/ask` advisory wire with explicit acknowledgment on `athletic` profiles.
* **Tabular Analytics Layer:** 7-day rolling exponential moving averages (EMA), target adherence deltas, and consecutive-day chrononutrition eating/fasting windows.
* **Role-Separated Documentation (`MANUAL.md` vs `DEV_MANUAL.md`):** Jargon-free end-user guide (`MANUAL.md`) separated from developer architecture, TDD, and CLI internals (`DEV_MANUAL.md`).

### 5.2 Out-of-Scope (Deferred to Later Phases)
* Remote multi-tenant cloud SaaS hosting.
* Native mobile store binaries (iOS App Store / Google Play)—handled via installable offline-first PWA.

---

## 6. Functional Requirements (FRs)

* **FR-1: Profile & Target Envelope Management**
  * System must support creating, editing, and listing independent household profiles (`standard`, `athletic`, `chronic_condition`).
  * Each profile must allow setting custom daily targets for calories, macronutrients (protein, carbs, fat, fiber), and micronutrients.
* **FR-2: Tiered Advisory and Recommendation Disclaimers**
  * *Medical & Chronic Health Profiles (Non-Negotiable Hard Lock):* Profiles tagged as `chronic_condition` completely disable the local AI goal-generator (HTTP 403 `ERR_CLINICAL_AI_RESTRICTED`) and display:
    > *"Nutritional goals for chronic conditions must be established in consultation with a qualified physician or registered dietitian. NutriVault does not provide clinical diagnoses or therapeutic prescriptions."*
  * *Fitness & Athletic Profiles (Local Model Advisory Wire):* Athletic AI targets must display:
    > *"Local model fitness baselines are heuristic estimates. For rigorous training regimens or metabolic adjustments, consult a certified fitness trainer or cross-reference using privacy-preserving frontier endpoints (e.g., search.brave.com/ask)."*
    Saving AI-generated targets requires explicit `acknowledged: true`.
* **FR-3: In-Memory Image Ingestion & Prompting**
  * System must accept image uploads via HTTP multipart POST into volatile RAM and dispatch to the local VLM enforcing JSON array output: `[{"item_name": "string", "estimated_grams": 100.0}]`.
* **FR-4: Deterministic USDA & Barcode Nutritional Resolution**
  * System must resolve food items either by deterministic text matching against `usda_foods.description` or by exact UPC/EAN barcode lookup against `usda_foods.barcode`.
  * System must calculate total calories, macronutrients, and micronutrients strictly as a linear function of `grams` against per-100g reference values.
* **FR-5: Interactive Confirmation & Portion Allocation**
  * System must allow users to search, scan barcodes, or upload photos, adjust gram weights, and distribute fractional portions ($\le 100\%$) across multiple household profiles.
* **FR-6: Ephemeral Image Lifecycle Guarantee**
  * Backend image data must be held exclusively in volatile memory buffers (`io.BytesIO`), overwritten in-place with `0x00` bytes, truncated, closed, and garbage-collected immediately upon VLM completion or error.
* **FR-7: Immutable Event-Sourced Journaling**
  * Confirmed meals must be written atomically to SQLite tables (`dishes` and `meal_logs`) recording profile ID, original consumption timestamp (`logged_at`), resolved food items, portion fraction, and computed nutrients.
* **FR-8: Rolling Statistical Queries**
  * System must provide read endpoints calculating 7-day rolling exponential moving averages (EMA) for caloric intake, macronutrient distributions, target adherence deltas, and daily eating/overnight fasting windows.
* **FR-9: Hardware Profiling & Predefined Small VLM Catalog**
  * System must inspect host compute resources on startup and map each hardware tier (`tier_1_cpu`, `tier_2_mid`, `tier_3_high`) to a **predefined default VLM specification** (`PredefinedVLMModel`) containing pinned HuggingFace repository IDs (`hf_repo`), GGUF model filenames (`model_file`), multimodal projector filenames (`mmproj_file`), approximate download size (`approx_size_mb`), and auto-generated `llama-server --hf-repo` launch commands:
    * *`tier_1_cpu` Default:* `SmolVLM-500M-Instruct-Q8_0` (~550 MB total) — universal default runnable on any CPU or Docker container.
    * *`tier_2_mid` Default:* `Qwen2.5-VL-3B-Instruct-Q4_K_M` (~2.2 GB).
    * *`tier_3_high` Default:* `Qwen2.5-VL-7B-Instruct-Q4_K_M` (~5.0 GB).
  * Prohibit selection of tiers exceeding host capabilities (`ERR_HARDWARE_TIER_EXCEEDED`).
* **FR-10: Out-of-the-Box Curated USDA Starter Seed (with Barcodes) & Direct Search API**
  * System must automatically seed `usda_foods` on startup when empty (`seed_default_usda_foods`), including pre-populated UPC/EAN barcodes on staple items.
  * System must expose `GET /api/v1/foods/search?q={query}&grams={grams}&limit={limit}` returning ranked items and scaled nutrients.
* **FR-11: Built-In Zero-Build Progressive Web App (PWA) Interface**
  * System must serve the responsive web application at `GET /`, web manifest at `GET /manifest.json`, and offline Service Worker at `GET /sw.js`.
* **FR-12: Double-Click Desktop Launchers, Automatic Browser Launch & Turnkey Containerization**
  * System must provide native double-click launcher scripts (`Start_NutriVault.command` for macOS, `Start_NutriVault.bat` for Windows, and `Start_NutriVault.sh` for Linux) that require zero terminal usage, automatically bootstrap/run the local server, and open `http://localhost:8080` in the user's default browser (`--open-browser`).
  * System must automatically detect the host computer's local LAN IP address (`detect_local_lan_ip`) and expose `local_lan_url` (`http://<lan_ip>:8080`) in `GET /api/v1/hardware` and the PWA header (`📱 Phone Wi-Fi Link`) so users never have to search OS network settings to connect their phone.
  * System must also provide a `docker-compose.yml` that launches `nutrivault` alongside a preconfigured `nutrivault-vlm` (`SmolVLM-500M-Instruct-Q8_0`) sidecar and an optional P2P VPN profile (`remote`).
* **FR-13: Offline-First "Snap & Sync Later" Queue (Away-from-Laptop Mode)**
  * When the client device is offline or away from the host laptop (e.g., at a restaurant or travelling), the PWA must remain loadable via `GET /sw.js` and allow users to queue meal drafts, photos (with original `logged_at` timestamps), and barcode scans in browser IndexedDB (`offline_sync_queue`).
  * Upon reconnecting to the NutriVault host, the PWA must synchronize queued items via `POST /api/v1/sync/batch` (and `POST /api/v1/meals/parse-image` for queued photos), preserving original consumption timestamps for chrononutrition accuracy.
* **FR-14: In-Browser Camera Barcode Scanner & 3-Tier Graceful Offline Barcode Resolution**
  * The PWA must provide an in-browser camera barcode scanner (using `BarcodeDetector` with manual UPC/EAN fallback).
  * The system must support a 3-tier resolution flow:
    1. *Tier 1 (Offline Phone Cache):* Check local IndexedDB `offline_foods_cache` synced from the server (`GET /api/v1/foods/catalog`) for instant $<10\text{ ms}$ offline nutrient lookup.
    2. *Tier 2 (Live Server Lookup / Deferred Queue):* Query `GET /api/v1/foods/barcode/{code}?grams={grams}` when online; if offline and uncached, store as a pending barcode entry in `offline_sync_queue` and resolve automatically via `POST /api/v1/sync/batch` on reconnect.
    3. *Tier 3 (Custom Barcode Registration):* Expose `PUT /api/v1/foods/barcode/{code}` allowing users to link or register an unrecognized barcode to per-100g nutritional values in `usda_foods` so future offline scans resolve at Tier 1.

---

## 7. Non-Functional Requirements (NFRs)

* **NFR-1 (Portability):** Backend architecture must be OS-independent, operating consistently across macOS, Linux, Windows, and OCI/Docker containers.
* **NFR-2 (Latency):** Direct USDA text search and barcode queries must resolve in $< 50\text{ ms}$ on the host and $< 10\text{ ms}$ when served from the phone's IndexedDB cache.
* **NFR-3 (Data Integrity):** The local SQLite database must operate in WAL (`Write-Ahead Logging`) mode with foreign key constraints enabled, and schema migrations (such as adding `barcode` to `usda_foods`) must be idempotent.
* **NFR-4 (Security & Network Isolation):** System must bind strictly to local network interfaces; zero external CDN assets loaded by the web UI, and loopback VLM connections strictly guarded against SSRF.
* **NFR-5 (Zero-Build Frontend Simplicity):** The embedded PWA frontend and Service Worker (`sw.js`) must be written in standard, dependency-free HTML5, CSS3, and vanilla JavaScript served directly by the Python backend.
* **NFR-6 (Graceful Degradation Offline & Without VLM):** All profile management, USDA food search, cached barcode scanning, offline meal/photo queuing, batch meal allocation, and rolling analytics features must remain functional when `llama-server` is offline or when the mobile client is temporarily disconnected from the host laptop.
* **NFR-7 (Strict Documentation Separation):** End-user documentation (`README.md`, `MANUAL.md`) must be written for an average non-technical user without requiring Python/`uv`/`git` knowledge, while developer setup, TDD architecture, and implementation details must reside in `DEV_MANUAL.md`.
