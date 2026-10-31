# Product Requirements Document (PRD)

**Project Name:** NutriVault  
**Subtitle:** Local-First Personal and Family Nutrition Tracker  
**Status:** Approved & Locked  
**Version:** 1.0.0  

---

## 1. Problem Statement
Commercial nutritional tracking applications systematically compromise user data sovereignty through continuous cloud telemetry, paywall foundational features behind recurring subscriptions, and monetize personal meal photographs by feeding them into proprietary model-training pipelines. Furthermore, existing open-source and privacy-focused trackers remain strictly manual or barcode-dependent, offering zero multimodal vision capabilities and lacking practical workflows for home-cooked family meals where a single dish is prepared and split unevenly across household members with divergent fitness, athletic, or chronic health demands.

## 2. Objective & Core Value Proposition
NutriVault is an open-source, local-first nutritional tracking and analytics system. It runs an ephemeral multimodal vision-language model (VLM) pipeline entirely on a local host machine. The system accepts meal photographs via a local-network web interface, extracts structured food items and portion estimates, maps them deterministically to local nutritional reference tables, purges image data immediately upon user confirmation, and logs nutritional events to a local SQLite database with support for multi-member family profiles, goal-oriented baseline configurations, and fractional batch allocations.

## 3. Non-Negotiables & Guiding Principles
* **Strict Privacy & Zero Data Exfiltration:** Zero analytics SDKs, zero telemetry, zero fingerprinting, and zero cloud services in the data path.
* **Transient Media Lifecycle:** Images are processed exclusively in volatile memory buffers (`io.BytesIO`). Under no circumstances are raw food photos persisted to disk, swap, or external storage.
* **Neuro-Symbolic Grounding:** The local vision model functions strictly as an entity and portion extractor, never an arithmetic calculator. Nutritional calculations are deterministically computed using embedded reference tables (USDA FoodData Central) to prevent model hallucinations.
* **Plug-and-Play Single Host:** The backend runs on the user's home computer, exposing a zero-configuration Progressive Web App (PWA) over the local area network (`.local` mDNS), requiring zero mobile app store installations.
* **Household Data Sovereignty:** Complete user ownership of all data via standard, unencrypted SQLite files, enabling direct queryability, custom scripting, and local statistical analysis.

---

## 4. User Personas & Use Cases

### 4.1 Personas
* **Primary Cook / Parent:** Plans and prepares meals for the household; needs to log a single cooked batch once and distribute realistic portion percentages to individual family members without re-entering ingredients per person.
* **Endurance Athlete / Runner:** Prioritizes high carbohydrate availability around training windows, electrolyte replenishment (sodium, potassium, magnesium), iron maintenance, and glycogen replenishment curves.
* **Hypertrophy Athlete / Bodybuilder:** Tracks precise protein-to-bodyweight ratios ($\text{g/kg}$), progressive caloric surpluses or deficits, and consistent multi-meal daily distributions.
* **Chronic Condition Manager (e.g., Crohn's Disease, Lupus / Autoimmune, CKD):** Relies on strict micro/macronutrient and ingredient tracking to manage inflammation, flare-up triggers, specific electrolyte limits (e.g., potassium/phosphorus in kidney concerns), or high-fiber versus low-residue phases where diet and clinical outcomes are tightly coupled.
* **Household Member / Child:** Consumes meals logged by the primary cook; views individual daily targets and intakes on a shared tablet or personal smartphone.

### 4.2 Core User Journeys
1. **Single-Dish Family Logging:** The cook takes a photo of a freshly prepared casserole or shared pan, confirms the detected ingredients and weights, assigns fractional allocations (e.g., Parent A: 40%, Parent B: 40%, Child: 20%), commits the meal to the ledger, and the system purges the image.
2. **Personal Plate Logging:** An individual user snaps a photo of a solo meal or post-workout shake, reviews the extracted candidate items, fine-tunes portion masses, commits directly to their personal profile, and clears the image buffer.
3. **Multi-Profile Goal & Target Configuration:** A user sets granular micro- and macro-nutrient targets for themselves and each individual family member, switching between clinical presets, athletic templates, or customized numeric limits.
4. **Local Nutritional Analysis:** A user opens the desktop dashboard to review rolling 7-day nutrient moving averages, micronutrient target adherence, and temporal eating windows.

---

## 5. Scope Boundaries

### 5.1 In-Scope (Phase 1 MVP)
* **Single-Host Daemon & PWA:** Standalone local web server broadcasting over mDNS (`http://nutrivault.local:8080`) serving an installable PWA for mobile browsers.
* **In-Memory Vision Pipeline:** Direct integration with an embedded local inference engine (`llama.cpp` / loopback REST) receiving in-memory multipart image streams.
* **Hardware Profiling & Cascading Model Tiering:** Dynamic hardware detection that gates allowable model sizes based on host RAM, VRAM, and accelerator backend (Apple Metal, CUDA, CPU).
* **Deterministic Nutritional Grounding:** Local SQLite integration with USDA FoodData Central (SR Legacy and Foundation Foods) providing calories, protein, carbohydrates, fats, fiber, and primary micronutrients (iron, calcium, magnesium, potassium, B-complex).
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
* Barcode UPC/EAN scanning (reserved for Phase 2 pantry extensions).
* Automated public network traversal / cloud relays (requires manual WireGuard/Tailscale if accessed remotely).

---

## 6. Functional Requirements (FRs)

* **FR-1: Profile & Target Envelope Management**
  * System must support creating, editing, and deleting independent household profiles.
  * Each profile must allow setting custom daily targets for calories, macronutrients (protein, carbs, fat, fiber), and micronutrients (calcium, iron, potassium, magnesium, sodium, vitamins).
  * System must support two target-setting pathways:
    1. *Manual Entry / Clinical Import:* Directly enter custom numeric limits as directed by a healthcare provider.
    2. *Local Model Fitness Recommendation:* Optional prompt-based assistant running on the local model that suggests macro splits and caloric bands based on athletic goals (e.g., marathon training, hypertrophy) and body metrics.
* **FR-2: Tiered Advisory and Recommendation Disclaimers**
  * *Medical & Chronic Health Profiles (Non-Negotiable Hard Lock):* Profiles tagged as `chronic_condition` (e.g., Crohn’s, Lupus, CKD) completely disable the local AI goal-generator. Prominently display the non-dismissible clinical notice:
    > *"Nutritional goals for chronic conditions must be established by a qualified physician or registered dietitian. NutriVault does not provide clinical diagnoses or therapeutic prescriptions."*
  * *Fitness & Athletic Profiles (Local Model Advisory Wire):* When users generate athletic or body composition targets using the local model, the system must display an explicit advisory banner before allowing them to save:
    > *"Local model fitness baselines are heuristic estimates. For rigorous training regimens or metabolic adjustments, consult a certified fitness trainer or cross-reference using privacy-preserving frontier endpoints (e.g., search.brave.com/ask)."*
    The user must explicitly tap **"Acknowledge & Apply"** to write these values into their profile's `target_envelopes`.
* **FR-3: In-Memory Image Ingestion & Prompting**
  * System must accept image uploads via an HTTP multipart POST endpoint into volatile RAM.
  * System must dispatch the in-memory payload to the local vision model using a strict prompt enforcing valid JSON output:
    ```json
    [
      {"item_name": "string", "estimated_grams": 0.0}
    ]
    ```
* **FR-4: Deterministic USDA Resolution**
  * System must take detected item names and query the local USDA reference table using deterministic text matching (exact or normalized substring/token matching).
  * System must calculate total calories, macronutrients, and micronutrients strictly as a linear function of `estimated_grams` against USDA per-100g values.
* **FR-5: Interactive Confirmation & Portion Allocation**
  * System must return candidate items and calculated values to the PWA client for review.
  * System must allow users to edit item names, adjust gram weights, add missing items, or delete misidentified items.
  * System must allow assigning the meal to a single profile or distributing fractional portions ($\le 100\%$) across multiple profiles.
* **FR-6: Ephemeral Image Lifecycle Guarantee**
  * Image data must be held exclusively in volatile memory buffers.
  * Memory buffers must be cleared and garbage-collected immediately once the client confirms or cancels the meal entry. No image bytes may be written to persistent block storage.
* **FR-7: Immutable Event-Sourced Journaling**
  * Confirmed meals must be written to an SQLite table (`meal_logs`) recording profile ID, timestamp, resolved food items, portion fraction, and computed nutrients.
* **FR-8: Rolling Statistical Queries**
  * System must provide read endpoints calculating 7-day rolling exponential moving averages (EMA) for caloric intake, macronutrient distributions, and target adherence deltas across personal and family profiles.
* **FR-9: Hardware Profiling & Adaptive Model Tiering**
  * System must inspect host compute resources (CPU, RAM, GPU/VRAM, Metal/CUDA acceleration) on startup.
  * System must lock model selection to allowable tiers:
    * *Tier 1 (CPU / Low-Spec, CPU-only or $<6\text{ GB}$ dedicated VRAM or $<16\text{ GB}$ unified/system RAM):* Locked to $\le 4\text{B}$ quantized models (SmolVLM, MiniCPM-V, Moondream2).
    * *Tier 2 (Mid-Spec / Dedicated GPU $\ge 6\text{ GB}$ VRAM or Apple Silicon $\ge 16\text{ GB}$ Unified Memory):* Unlocks $7\text{B}\text{--}9\text{B}$ models (Qwen2.5-VL 7B Q4).
    * *Tier 3 (High-Spec / Dedicated GPU $\ge 16\text{ GB}$ VRAM or Apple Silicon $\ge 32\text{ GB}$ Unified Memory):* Unlocks $14\text{B}+$ models.
  * Prohibit user selection of tiers exceeding host capabilities to prevent system freezing.

---

## 7. Non-Functional Requirements (NFRs)

* **NFR-1 (Portability):** Backend architecture must be OS-independent, operating consistently across macOS, Linux, and Windows.
* **NFR-2 (Latency):** Total round-trip time from image submission to candidate presentation in the PWA must not exceed local model inference time $+ 200\text{ ms}$ host overhead.
* **NFR-3 (Data Integrity):** The local SQLite database must operate in WAL (`Write-Ahead Logging`) mode with foreign key constraints enabled.
* **NFR-4 (Security & Network Isolation):** System must bind strictly to local network interfaces; zero external inbound or outbound WAN connections permitted.