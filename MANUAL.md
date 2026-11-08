# NutriVault User Guide 🥗📱

Welcome to **NutriVault**, your private, personal, and family nutrition companion. NutriVault helps you and your household track meals, understand nutrition, and scan grocery barcodes—completely private, with zero ads, and zero cloud tracking.

---

## Table of Contents

1. [60-Second Quickstart](#1-60-second-quickstart)
2. [Installing NutriVault on Your Phone (PWA)](#2-installing-nutrivault-on-your-phone-pwa)
3. [Managing Household Profiles & Goals](#3-managing-household-profiles--goals)
4. [Logging Meals at Home](#4-logging-meals-at-home)
   - [Instant Search (Staple Foods)](#instant-search-staple-foods)
   - [Meal Photos (Private Camera AI)](#meal-photos-private-camera-ai)
   - [Family Cooking Splitter (Cook Once, Log for Everyone)](#family-cooking-splitter-cook-once-log-for-everyone)
5. [3-Tier Grocery Barcode Scanner](#5-3-tier-grocery-barcode-scanner)
6. ["Snap & Sync Later" (Restaurants & Travel Mode)](#6-snap--sync-later-restaurants--travel-mode)
7. [7-Day Trends & Intermittent Fasting Windows](#7-7-day-trends--intermittent-fasting-windows)
8. [Backing Up Your Nutrition Data](#8-backing-up-your-nutrition-data)

---

## 1. 60-Second Quickstart

NutriVault runs right on your home computer or server.

### Launching NutriVault
Open your computer terminal and start the turnkey service:
```bash
docker compose up
```

Open your browser and navigate to:
```
http://localhost:8080
```
NutriVault will immediately open with its full library of staple foods pre-loaded!

---

## 2. Installing NutriVault on Your Phone (PWA)

You don't need an app store. NutriVault installs directly as a lightweight, lightning-fast app on your home screen:

### On iPhone (Safari)
1. On your iPhone, connect to your home Wi-Fi and open Safari.
2. Go to `http://<your-computer-ip>:8080` (or `http://nutrivault.local:8080`).
3. Tap the **Share** button (the box with an upward arrow at the bottom of the screen).
4. Scroll down and tap **"Add to Home Screen"**.
5. Tap **Add**. The NutriVault icon 🥗 will now appear on your phone's home screen.

### On Android (Chrome)
1. Connect to your home Wi-Fi and open Chrome.
2. Go to `http://<your-computer-ip>:8080`.
3. Tap the **three dots** in the top right corner.
4. Select **"Install app"** or **"Add to Home screen"**.

Once installed, NutriVault opens full-screen like a native app and works offline when you're away from home!

---

## 3. Managing Household Profiles & Goals

NutriVault is designed for individuals and families:

* **Switch Profiles:** Select any family member from the top dropdown.
* **Add a Profile:** Tap **"+ New"** to add a family member, athlete, or child.
* **Nutrition Goals:** Set daily targets for Calories, Protein, Carbs, Fat, and Fiber.
* **Health Safeguards:**
  * **Athletic Goals:** Automatically calculates baseline targets for endurance, strength, or balanced training.
  * **Medical Conditions:** NutriVault protects your safety. If a profile is marked with a chronic medical condition, automatic AI targets are locked to ensure you consult your registered dietitian or physician.

---

## 4. Logging Meals at Home

### Instant Search (Staple Foods)
1. Type what you're eating into the search bar (e.g., `brown rice`, `chicken breast`, `eggs`, `spinach`).
2. Enter your portion size in grams (default is 100g).
3. Tap **Search** and then **+ Add** to place it into your current dish draft.

### Meal Photos (Private Camera AI)
1. Snap a photo of your plate or upload an existing photo.
2. NutriVault's private vision AI identifies the foods and estimates their weights.
3. **100% Private:** Photos stay strictly in temporary memory while being analyzed. Your photos are never saved to disk and are completely erased immediately after review.

### Family Cooking Splitter (Cook Once, Log for Everyone)
Cooking a large shared meal (like a family stew, casserole, or pasta dish)?
1. Add all the ingredients of the entire recipe to your draft.
2. Scroll to the **Family Batch Portion Allocator**.
3. Adjust the sliders for each household member (e.g., Parent A: 40%, Parent B: 35%, Kid: 25%).
4. Choose your meal type (**Breakfast**, **Lunch**, **Dinner**, or **Snack**).
5. Tap **"Commit Meal to Ledger"**. NutriVault automatically calculates and logs everyone's exact portion in one tap!

---

## 5. 3-Tier Grocery Barcode Scanner

Scan groceries effortlessly in your kitchen or at the store:

* **Tier 1 (Instant Local Lookups):** Scans against your local catalog on your phone in under 10 milliseconds—even with zero Wi-Fi or cellular signal!
* **Tier 2 (Home Server Lookups):** Queries your home database for any item previously registered in your household.
* **Tier 3 (1-Tap Custom Barcode Registration):** Scanned a brand new packaged food? NutriVault immediately prompts you with a quick form: enter the calories, protein, carbs, and fat from the nutrition label on the box. Once saved, it's permanently stored and recognized forever across all your devices!

### How to Scan
* **Camera Scanning:** Tap **"📷 Camera"**, point your phone camera at the barcode, and NutriVault will scan it automatically.
* **Manual Entry:** If your camera is busy, type the barcode number (e.g., `0030000010204`) into the box and tap **Lookup**.

---

## 6. "Snap & Sync Later" (Restaurants & Travel Mode)

What happens when you're eating at a restaurant or travelling away from your home computer?

NutriVault features **Snap & Sync Later**:
1. When you leave home, NutriVault automatically switches to **Offline Mode**.
2. Search staple foods, scan grocery barcodes, and log your meals as usual.
3. Your meals are saved safely in your phone's local offline queue, preserving the exact date and time you ate.
4. When you reconnect to your home Wi-Fi, NutriVault will automatically sync your meals to your permanent diary! You can also tap **"Sync Now 🔄"** at any time.

---

## 7. 7-Day Trends & Intermittent Fasting Windows

NutriVault tracks your health over time:

* **Rolling 7-Day Averages:** Shows your smoothed daily calorie and macronutrient intake, filtering out day-to-day noise.
* **Target Adherence:** Highlights whether you are on track with your goals with clear positive and negative indicators.
* **Intermittent Fasting & Eating Windows:** Automatically computes when you ate your first meal, your last meal, how many hours your eating window lasted, and your overnight fast between consecutive days.

---

## 8. Backing Up Your Nutrition Data

All your profiles, meal journals, and custom foods are stored in a single file on your computer:
```
data/nutrivault.db
```
To back up your entire history, simply copy `data/nutrivault.db` to a backup drive or cloud folder. To restore, place it back into `data/`. That's it!
