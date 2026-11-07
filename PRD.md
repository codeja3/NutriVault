# Product Requirements Document (PRD)

**Project Name:** NutriVault  
**Subtitle:** Local-First Personal and Family Nutrition Tracker  
**Status:** Approved & Locked  
**Version:** 1.2.0  

---

## 1. Problem Statement
Commercial nutritional tracking applications systematically compromise user data sovereignty through continuous cloud telemetry, paywall foundational features behind recurring subscriptions, and monetize personal meal photographs by feeding them into proprietary model-training pipelines. Furthermore, existing open-source and privacy-focused trackers remain strictly manual or barcode-dependent, offering zero multimodal vision capabilities and lacking practical workflows for home-cooked family meals where a single dish is prepared and split unevenly across household members with divergent fitness, athletic, or chronic health demands. At the same time, self-hosted privacy tools often suffer from high setup friction (manual database seeding, complex local model configuration, and CLI-only interfaces) that alienates everyday users.

## 2. Objective & Core Value Proposition
NutriVault is an open-source, local-first nutritional tracking and analytics system designed to be approachable by any user in under 60 seconds. It pairs a built-in, zero-configuration Progressive Web App (PWA) and pre-seeded USDA nutritional database with an optional ephemeral multimodal vision-language model (VLM) pipeline running on the local host machine. Users can log meals immediately via instant USDA text search or snap meal photographs that are processed exclusively in volatile memory, mapped deterministically to USDA reference tables, purged immediately in-place (`0x00`), and logged to a local SQLite database with support for multi-member family profiles, goal-oriented baseline configurations, and fractional batch allocations.

## 3. Non-Negotiables & Guiding Principles
* **Strict Privacy & Zero Data Exfiltration:** Zero analytics SDKs, zero telemetry, zero fingerprinting, and zero cloud services in the data path.
* **Transient Media Lifecycle:** Images are processed exclusively in volatile memory buffers (`io.BytesIO`) and overwritten with `0x00` bytes upon completion. Under no circumstances are raw food photos persisted to disk, swap, or external storage.
* **Neuro-Symbolic Grounding:** The local vision model functions strictly as an entity and portion extractor, never an arithmetic calculator. Nutritional calculations are deterministically computed using embedded reference tables (USDA FoodData Central) to prevent model hallucinations.
* **Zero-Friction Onboarding ("60-Second Time-to-First-Meal"):** The application must work out-of-the-box with a pre-seeded USDA starter database, a built-in browser UI (`http://localhost:8080`), one-command Docker or local startup, and full functionality even before a local VLM is configured.
* **Plug-and-Play Single Host:** The backend runs on the user's home computer, exposing a zero-configuration Progressive Web App (PWA) over the local area network (`.local` mDNS), requiring zero mobile app store installations.
* **Household Data Sovereignty:** Complete user ownership of all data via standard, unencrypted SQLite files, enabling direct queryability, custom scripting, and local statistical analysis.

---

## 4. User Personas & Use Cases

### 4.1 Personas
* **Everyday Privacy-Conscious User:** Wants a simple, visual browser app that runs via a single command (`docker compose up` or `uv run python -m src.api`) and logs meals immediately without requiring deep Python or LLM knowledge.
* **Primary Cook / Parent:** Plans and prepares meals for the household; needs to log a single cooked batch once and distribute realistic portion percentages to individual family members without re-entering ingredients per person.
* **Endurance Athlete / Runner:** Prioritizes high carbohydrate availability around training windows, electrolyte replenishment (sodium, potassium, magnesium), iron maintenance, and glycogen replenishment curves.
* **Hypertrophy Athlete / Bodybuilder:** Tracks precise protein-to-bodyweight ratios ($\text{g/kg}$), progressive caloric surpluses or deficits, and consistent multi-meal daily distributions.
* **Chronic Condition Manager (e.g., Crohn's Disease, Lupus / Autoimmune, CKD):** Relies on strict micro/macronutrient and ingredient tracking to manage inflammation, flare-up triggers, specific electrolyte limits (e.g., potassium/phosphorus in kidney concerns), or high-fiber versus low-residue phases where diet and clinical outcomes are tightly coupled.
* **Household Member / Child:** Consumes meals logged by the primary cook; views individual daily targets and intakes on a shared tablet or personal smartphone.

### 4.2 Core User Journeys
1. **Zero-VLM Instant Search Logging (Day-1 Onboarding):** A user starts NutriVault, opens `http://localhost:8080` in their browser, types `"brown rice"` and `"roasted chicken breast"` into the live USDA search bar, adjusts portion weights, and commits their first meal in under 60 seconds—without needing to download a vision model first.
2. **Single-Dish Family Logging:** The cook takes a photo of a freshly prepared casserole or shared pan (or searches ingredients), confirms the detected ingredients and weights, assigns fractional allocations via interactive sliders (e.g., Parent A: 40%, Parent B: 40%, Child: 20%), commits the meal to the ledger, and the system purges the image.
3. **Personal Plate Logging:** An individual user snaps a photo of a solo meal or post-workout shake, reviews the extracted candidate items, fine-tunes portion masses, commits directly to their personal profile, and clears the image buffer.
4. **Multi-Profile Goal & Target Configuration:** A user sets granular micro- and macro-nutrient targets for themselves and each individual family member in the web UI, switching between clinical presets, athletic templates, or customized numeric limits.
5. **Local Nutritional Analysis:** A user opens the dashboard to review rolling 7-day nutrient moving averages, micronutrient target adherence, and temporal eating/fasting windows.

---

## 5. Scope Boundaries

### 5.1 In-Scope
* **Built-In Progressive Web App (PWA) & Single-Host Daemon:** Standalone local web server (`http://localhost:8080` / `http://nutrivault.local:8080`) serving a zero-build, installable HTML5/CSS/JS PWA alongside the REST API.
* **Out-of-the-Box Curated USDA Starter Seed & Search API:** Pre-populated USDA reference foods on first launch plus a live search and portion-scaling endpoint (`/api/v1/foods/search`) so the app is immediately usable without manual dataset imports or mandatory VLM setup.
* **In-Memory Vision Pipeline:** Direct integration with an embedded local inference engine (`llama.cpp` / loopback REST on `:8081`) receiving in-memory multipart image streams.
* **Hardware Profiling & Cascading Model Tiering:** Dynamic hardware detection that gates allowable model sizes based on host RAM, VRAM, and accelerator backend (Apple Metal, CUDA, CPU) and provides copy-paste setup guidance (`--vlm-guide`) for the recommended model tier.
* **Turnkey Containerization (`Dockerfile` & `docker-compose.yml`):** One-command container launch with persistent SQLite volume mounting and optional VLM sidecar profile.
* **Deterministic Nutritional Grounding:** Local SQLite integration with USDA FoodData Central (SR Legacy and Foundation Foods) providing calories, protein, carbohydrates, fats, fiber, and primary micronutrients (iron, calcium, magnesium, potassium, sodium, zinc, vitamin C, vitamin D, B-complex).
* **Family Profiles & Batch Splitting:** Support for multiple user profiles under a single household, each with customizable DRI/RDA baselines, plus a fractional portion allocator ($\sum \text{fractions} \le 1.0$).
* **Goal-Setting Architecture (Personal & Family):** Granular target envelopes at both personal and family-member levels, accommodating general wellness, athletic templates, and clinical restriction profiles.
* **Clinical Disclaimers & Local AI Fitness Advisor:**
  * Mandatory disclaimer banners enforcing that medical, metabolic, and chronic-disease dietary constraints must be established by licensed medical providers.
  * Hard lock preventing local AI target generation for chronic condition profiles.
  * Advisory wire for athletic targets recommending verification with certified trainers or private frontier endpoints (e.g., `search.brave.com/ask`).
* **Review, Correct & Purge Wire:** Interactive UI step presenting extracted items, confidence bounds, and editable portion fields, paired with immediate memory buffer deallocation upon log confirmation.
* **Tabular Analytics Layer:** Relational SQLite schema optimized for time-series extraction, rolling averages, and window functions.

### 5.2 Out-of-Scope (Deferred to Later Phases)
* Remote multi-tenant team/athlete coaching outside the local network.
* Native mobile binaries (iOS App Store / Google Play).
* Barcode UPC/EAN scanning (reserved for future pantry extensions).
* Automated public network traversal / cloud relays (requires manual WireGuard/Tailscale if accessed remotely).

---

## 6. Functional Requirements (FRs)

* **FR-1: Profile & Target Envelope Management**
  * System must support creating, editing, and deleting independent household profiles.
  * Each profile must allow setting custom daily targets for calories, macronutrients (protein, carbs, fat, fiber), and micronutrients (calcium, iron, potassium, magnesium, sodium, vitamins).
  * System must support two target-setting pathways:
    1. *Manual Entry / Clinical Import:* Directly enter custom numeric limits as directed by a healthcare provider.
    2. *Local Model Fitness Recommendation:* Optional assistant that suggests macro splits and caloric bands based on athletic goals (e.g., endurance, hypertrophy) and body metrics.
* **FR-2: Tiered Advisory and Recommendation Disclaimers**
  * *Medical & Chronic Health Profiles (Non-Negotiable Hard Lock):* Profiles tagged as `chronic_condition` (e.g., Crohn’s, Lupus, CKD) completely disable the local AI goal-generator. Prominently display the non-dismissible clinical notice:
    > *"Nutritional goals for chronic conditions must be established in consultation with a qualified physician or registered dietitian. NutriVault does not provide clinical diagnoses or therapeutic prescriptions."*
  * *Fitness & Athletic Profiles (Local Model Advisory Wire):* When users generate athletic or body composition targets using the local model, the system must display an explicit advisory banner before allowing them to save:
    > *"Local model fitness baselines are heuristic estimates. For rigorous training regimens or metabolic adjustments, consult a certified fitness trainer or cross-reference using privacy-preserving frontier endpoints (e.g., search.brave.com/ask)."*
    The user must explicitly acknowledge (`acknowledged: true`) to write these values into their profile's `target_envelopes`.
* **FR-3: In-Memory Image Ingestion & Prompting**
  * System must accept image uploads via an HTTP multipart POST endpoint into volatile RAM.
  * System must dispatch the in-memory payload to the local vision model using a strict prompt enforcing valid JSON output:
    ```json
    [
      {"item_name": "string", "estimated_grams": 100.0}
    ]
    ```
* **FR-4: Deterministic USDA Resolution**
  * System must take detected or searched item names and query the local USDA reference table using deterministic text matching (normalized token overlap, sequence similarity, and preparation-state weighting).
  * System must calculate total calories, macronutrients, and micronutrients strictly as a linear function of `estimated_grams` against USDA per-100g values.
* **FR-5: Interactive Confirmation & Portion Allocation**
  * System must return candidate items and calculated values to the PWA client for review.
  * System must allow users to search and add items, adjust gram weights, or delete misidentified items.
  * System must allow assigning the meal to a single profile or distributing fractional portions ($\le 100\%$) across multiple profiles.
* **FR-6: Ephemeral Image Lifecycle Guarantee**
  * Image data must be held exclusively in volatile memory buffers (`io.BytesIO`).
  * Memory buffers must be overwritten with `0x00` bytes, cleared, and garbage-collected immediately once VLM parsing completes or fails. No image bytes may be written to persistent block storage.
* **FR-7: Immutable Event-Sourced Journaling**
  * Confirmed meals must be written atomically to SQLite tables (`dishes` and `meal_logs`) recording profile ID, timestamp, resolved food items, portion fraction, and computed nutrients.
* **FR-8: Rolling Statistical Queries**
  * System must provide read endpoints calculating 7-day rolling exponential moving averages (EMA) for caloric intake, macronutrient distributions, target adherence deltas, and daily eating/overnight fasting windows across personal and family profiles.
* **FR-9: Hardware Profiling & Adaptive Model Tiering**
  * System must inspect host compute resources (CPU, RAM, GPU/VRAM, Metal/CUDA acceleration) on startup and expose recommended vision models for the resolved tier:
    * *Tier 1 (`tier_1_cpu`):* Locked to $\le 4\text{B}$ quantized models (`SmolVLM-500M-Instruct-Q8_0`, `Moondream2-Q4_K_M`, `MiniCPM-V-2_6-Q4_K_M`).
    * *Tier 2 (`tier_2_mid`):* Unlocks $7\text{B}\text{--}9\text{B}$ models (`Qwen2.5-VL-7B-Instruct-Q4_K_M`, `Gemma-3-4B-IT-Q8_0`).
    * *Tier 3 (`tier_3_high`):* Unlocks $14\text{B}+$ models (`Qwen2.5-VL-14B-Instruct-Q4_K_M`, `Qwen2.5-VL-32B-Instruct-Q4_K_M`).
  * Prohibit selection of tiers exceeding host capabilities to prevent system freezing.
* **FR-10: Out-of-the-Box Curated USDA Starter Seed & Direct Search API**
  * System must include a curated starter catalog of common USDA Foundation / SR Legacy foods and automatically seed `usda_foods` on server startup when the table is empty.
  * System must expose a direct search and linear scaling endpoint (`GET /api/v1/foods/search?q={query}&grams={grams}&limit={limit}`) so users can search and log meals manually or augment VLM drafts without requiring a running VLM.
* **FR-11: Built-In Zero-Build Progressive Web App (PWA) Interface**
  * System must serve a self-contained, responsive web application at `GET /` and a web app manifest at `GET /manifest.json`.
  * The web UI must enable end-to-end graphical operation of all core workflows: profile creation & switching, manual & AI athletic target configuration (with mandatory clinical/athletic disclaimers), photo VLM upload, instant USDA text search, interactive multi-member batch portion splitting, and rolling 7-day analytics visualization.
* **FR-12: Turnkey Containerization & Hardware-Aware VLM Setup Guide**
  * System must provide a `Dockerfile` and `docker-compose.yml` for one-command deployment (`docker compose up`) with persistent `/app/data` storage.
  * System must provide a `--vlm-guide` CLI flag (and UI hardware drawer) that outputs the detected hardware tier, recommended GGUF model filenames, and exact `llama-server` launch command for the host machine.

---

## 7. Non-Functional Requirements (NFRs)

* **NFR-1 (Portability):** Backend architecture must be OS-independent, operating consistently across macOS, Linux, Windows, and OCI/Docker containers.
* **NFR-2 (Latency):** Total round-trip time from image submission to candidate presentation in the PWA must not exceed local model inference time $+ 200\text{ ms}$ host overhead; direct USDA text search queries must resolve in $< 50\text{ ms}$.
* **NFR-3 (Data Integrity):** The local SQLite database must operate in WAL (`Write-Ahead Logging`) mode with foreign key constraints enabled.
* **NFR-4 (Security & Network Isolation):** System must bind strictly to local network interfaces; zero external inbound or outbound WAN connections permitted, and zero external CDN assets loaded by the web UI.
* **NFR-5 (Zero-Build Frontend Simplicity):** The embedded PWA frontend must be written in standard, dependency-free HTML5, CSS3, and vanilla JavaScript served directly by the Python backend, requiring zero Node.js/npm build pipelines.
* **NFR-6 (Graceful Degradation Without VLM):** All profile management, target envelopes, USDA food search, batch meal allocation, and rolling analytics features must remain 100% functional when `llama-server` is offline.
