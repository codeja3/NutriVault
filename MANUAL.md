# NutriVault User Guide 🥗📱

Welcome to **NutriVault**, your private, personal, and family nutrition companion. NutriVault helps you and your household track meals, understand nutrition, and scan grocery barcodes—100% private, with zero ads, zero subscriptions, and zero cloud tracking.

You do **not** need any programming or command-line experience to use NutriVault.

---

## Table of Contents

1. [Step-by-Step: Download & Double-Click Start](#1-step-by-step-download--double-click-start)
2. [Installing NutriVault on Your Phone (No App Store Needed)](#2-installing-nutrivault-on-your-phone-no-app-store-needed)
3. [Managing Household Profiles & Nutrition Goals](#3-managing-household-profiles--nutrition-goals)
4. [Logging Meals at Home](#4-logging-meals-at-home)
   - [Instant Search (Staple Foods)](#instant-search-staple-foods)
   - [Meal Photos (Private Camera AI)](#meal-photos-private-camera-ai)
   - [Family Cooking Splitter (Cook Once, Log for Everyone)](#family-cooking-splitter-cook-once-log-for-everyone)
5. [In-Store Grocery Barcode Scanner (Works Online & Offline)](#5-in-store-grocery-barcode-scanner-works-online--offline)
6. ["Snap & Sync Later" (Restaurants & Travel Away from Your Computer)](#6-snap--sync-later-restaurants--travel-away-from-your-computer)
7. [7-Day Trends & Intermittent Fasting Windows](#7-7-day-trends--intermittent-fasting-windows)
8. [Backing Up Your Nutrition History](#8-backing-up-your-nutrition-history)
9. [Uninstalling NutriVault](#9-uninstalling-nutrivault)

---

## 1. Step-by-Step: Download & Double-Click Start

NutriVault runs right on your home Mac, Windows, or Linux computer. Follow these 3 simple steps:

### Step 1: Download the NutriVault Folder (1 Click)
1. Click this direct link to download NutriVault to your computer:  
   👉 **[Download NutriVault (.zip)](https://github.com/codeja3/NutriVault/archive/refs/heads/main.zip)**
2. Open your computer's **Downloads** folder.
3. Unzip the downloaded `NutriVault-main.zip` file:
   * **On Mac:** Double-click `NutriVault-main.zip` to unpack the **`NutriVault-main`** folder.
   * **On Windows:** Right-click `NutriVault-main.zip`, click **"Extract All..."**, and click **Extract**.
   * **On Linux:** Right-click `NutriVault-main.zip` in your file manager and select **"Extract Here"** (or double-click it and click **Extract**).
4. *(Recommended)* Drag the unpacked **`NutriVault-main`** folder to your **Desktop**, **Home**, or **Documents** folder so it's always easy to find.

### Step 2: Double-Click to Launch NutriVault
Open the **`NutriVault-main`** folder you just unpacked:

* **On a Mac:**
  1. Look for the file named **`Start_NutriVault.command`** and **double-click** it.
  2. *First-Time Mac Tip:* If macOS shows a security popup saying *"Start_NutriVault.command cannot be opened because it is from an unidentified developer"*, simply **Right-Click** (or Control-Click) **`Start_NutriVault.command`**, choose **Open** from the menu, and click **Open** in the dialog box. You only ever have to do this once!
* **On Windows:**
  1. Look for the file named **`Start_NutriVault.bat`** and **double-click** it.
  2. *First-Time Windows Tip:* If Windows SmartScreen shows a blue *"Windows protected your PC"* popup, click **"More info"** and then click **"Run anyway"**.
* **On Linux (Ubuntu, Linux Mint, Fedora, Debian, etc.):**
  1. Look for the file named **`Start_NutriVault.sh`**.
  2. **Right-click** **`Start_NutriVault.sh`** and select **"Run as a Program"** (or double-click it and choose **"Run in Terminal"** / **"Execute"**).
  3. *First-Time Linux Tip:* If your file manager opens `Start_NutriVault.sh` in a text editor instead of running it, right-click `Start_NutriVault.sh` $\rightarrow$ **Properties** $\rightarrow$ **Permissions**, check **"Allow executing file as program"**, close Properties, and then right-click $\rightarrow$ **"Run as a Program"**.

### Step 3: Your Web Browser Opens Automatically!
A small status window will appear to start NutriVault (and automatically finish a one-time setup if it's your very first launch), and your default web browser will automatically open to:
```text
http://localhost:8080
```
*(Keep that small background window open while you use NutriVault, or minimize it to your Dock/Taskbar.)*

---

## 2. Installing NutriVault on Your Phone (No App Store Needed)

You can use NutriVault right on your iPhone or Android phone—both at home and when you are out at a restaurant or grocery store!

### Step 1: Find Your "Phone Wi-Fi Link" at the Top of the Screen
Look at the top-right header of the NutriVault screen on your computer. You will see a green badge that shows your computer's exact home Wi-Fi address, for example:
> **📱 Phone Wi-Fi Link:** `http://192.168.1.42:8080`

*(You don't need to search through your computer settings—NutriVault finds and displays this address for you automatically!)*

### Step 2: Add NutriVault to Your Phone's Home Screen

#### On iPhone (Safari)
1. Make sure your iPhone is connected to the **same home Wi-Fi** as your computer.
2. Open **Safari** on your iPhone and type the exact **`📱 Phone Wi-Fi Link`** shown on your computer screen (for example, `http://192.168.1.42:8080`).
3. Tap the **Share** button at the bottom of Safari (the square with an upward arrow).
4. Scroll down and tap **"Add to Home Screen"**, then tap **Add**.
5. The **NutriVault 🥗** app icon is now on your iPhone home screen!

#### On Android (Chrome)
1. Connect your Android phone to the **same home Wi-Fi** as your computer.
2. Open **Chrome** and type the exact **`📱 Phone Wi-Fi Link`** shown on your computer screen (for example, `http://192.168.1.42:8080`).
3. Tap the **three dots (⋮)** in the top-right corner of Chrome.
4. Tap **"Install app"** or **"Add to Home screen"**.

Once added to your home screen, NutriVault opens full-screen like a native app and **stays usable even when you leave home!**

---

## 3. Managing Household Profiles & Nutrition Goals

NutriVault is built for individuals, athletes, and whole families:

* **Create a Profile:** Click **"+ New"** under **Household Profile & Targets** to add yourself, your partner, or your children.
* **Switch Profiles:** Use the dropdown menu to view or update any family member's targets and dashboard.
* **Daily Nutrition Goals:** Enter your daily targets for Calories, Protein, Carbs, Fat, and Fiber, then click **Save Targets**.
* **Built-In Health Safeguards:**
  * **Athletic Profiles:** Click **"AI Goal Advisor"**, enter your body weight in kg, and NutriVault will suggest heuristic training targets. Review the trainer advisory banner, check the acknowledgment box, and click **Save Targets**.
  * **Chronic Health Conditions:** If a profile is marked as **Chronic Health Condition** (such as Crohn's, Lupus, or Kidney concerns), automatic AI target suggestions are permanently locked for your safety so that your targets are set strictly with your physician or registered dietitian.

---

## 4. Logging Meals at Home

### Instant Search (Staple Foods)
1. In the **Build & Log Dish** card, type a food into the search box (e.g., `brown rice`, `chicken breast`, `oats`, `eggs`, `broccoli`).
2. Enter your portion weight in **grams** (default is `100`).
3. Click **Search**, then click **+ Add** next to the matching food to add it to your **Current Dish Draft**.
4. You can adjust the gram weight of any item directly in the draft table at any time!

### Meal Photos (Private Camera AI)
1. Click **Choose File** (or tap to open your camera on mobile) under **Ephemeral Meal Photo**, select a photo of your plate, and click **Upload Photo**.
2. If Camera AI is running (automatically included if you have Docker Desktop installed, or via the 1-click **VLM Setup Guide ℹ️** button at the top right), NutriVault identifies each food on your plate and estimates its weight in grams.
3. **100% Private:** Your photo is analyzed strictly in temporary memory (`RAM`) and is immediately erased (`0x00`) the moment recognition finishes. No food photos are ever saved to your hard drive or sent to the cloud.

### Family Cooking Splitter (Cook Once, Log for Everyone)
Made a big pot of chili, pasta, or roasted vegetables for the whole family?
1. Add all the ingredients for the entire pot into **Current Dish Draft** and give the dish a name (e.g., `"Sunday Family Lasagna"`).
2. Scroll down to **Family Batch Portion Allocator**.
3. Drag the percentage sliders for each family member who ate a portion (for example: *Alex: 45%*, *Sam: 35%*, *Child: 20%* — any total up to 100%).
4. Select the **Meal Type** (*Breakfast*, *Lunch*, *Dinner*, *Snack*, *Pre-Workout*, or *Post-Workout*) and click **"Commit Meal to Ledger"**.
5. NutriVault automatically calculates and logs each person's exact share of calories, macros, and vitamins in a single click!

---

## 5. In-Store Grocery Barcode Scanner (Works Online & Offline)

Whether you are in your kitchen or standing in a grocery store aisle away from your computer, you can scan packaged food barcodes right from your phone:

1. Under **Grocery Barcode Scanner**, tap **"📷 Camera"** and point your phone camera at the product's barcode (or type the barcode digits into the box and tap **Lookup**).
2. **How NutriVault Handles Barcodes (Even Offline!):**
   * **Tier 1 — Instant Phone Cache (<10 milliseconds):** Every staple and previously scanned product is automatically saved in your phone's memory. Even if you have **zero Wi-Fi or cell service** in the store, familiar items appear instantaneously!
   * **Tier 2 — Home Computer Lookup or Offline Queue:** If you are at home, NutriVault checks your home computer's database. If you are away from home (offline) and scan a brand-new item, NutriVault asks if you want to **Queue it for Sync**—recording the barcode, portion grams, and exact time you ate it so it resolves automatically when you get back home!
   * **Tier 3 — 1-Tap Custom Barcode Save:** If a local store brand isn't in your catalog yet, a quick popup lets you type the Product Name and the per-100g Calories, Protein, Carbs, Fat, and Fiber from the package label. Once you tap **Save Barcode**, your vault remembers that barcode forever for instant Tier-1 offline scans on every future shopping trip!

---

## 6. "Snap & Sync Later" (Restaurants & Travel Away from Your Computer)

What happens when your laptop is at home (or closed in your hotel room) and you are out at a restaurant or travelling?

1. Open the **NutriVault** icon from your phone's home screen.
2. The banner at the top will automatically show:  
   🟡 **`Offline Mode — Snap & Sync Later Active`**
3. While offline, you can:
   * **Search USDA staple foods** (using your phone's built-in offline food catalog) and tap **Commit Meal to Ledger** to save the meal to your phone's offline queue.
   * **Snap a photo of your restaurant plate** and tap **Upload Photo**—NutriVault stores the photo and the exact time you ate inside your phone's private queue.
   * **Scan grocery barcodes** and queue them for sync.
4. Notice the **`Pending Sync`** counter at the top of your screen increase as you log items on the go.
5. **Automatic Sync When Back Home:** The moment your phone reconnects to your home Wi-Fi (or your laptop), NutriVault automatically flushes your queued meals, barcodes, and photos to your computer, records them under the **exact original time you ate**, and updates your analytics! You can also tap **"Sync Now 🔄"** anytime.

---

## 7. 7-Day Trends & Intermittent Fasting Windows

Scroll to **Rolling 7-Day Analytics & Chrononutrition** to see your progress:

* **7-Day EMA Cards:** Shows your smoothed 7-day rolling average for Calories, Protein, Carbs, Fat, and Fiber—plus how close you are to your daily target envelope (`+` or `-`).
* **Feeding Intervals & Overnight Fasts:** Automatically tracks the time of your **First Meal** and **Last Meal** each day, calculates your daily **Eating Window** (in hours), and computes your **Overnight Fast** between consecutive days.

---

## 8. Backing Up Your Nutrition History

You own 100% of your data. Everything you log is stored in a single file inside your `NutriVault-main` folder:
```text
data/nutrivault.db
```
* **To back up your data:** Copy the `nutrivault.db` file from the `data` folder onto a USB drive or your personal backup folder.
* **To restore your data on a new computer:** Place your `nutrivault.db` file back into the `data` folder and double-click `Start_NutriVault`!

---

## 9. Uninstalling NutriVault

Because NutriVault is self-contained inside its folder and does not scatter background services across your operating system, uninstalling it is quick and clean:

### 1. Uninstall from Your Computer (Mac, Windows, or Linux)
1. **Stop NutriVault:** If NutriVault is currently running, close its background launcher window.
2. **(Optional) Save Your Data Backup:** If you want to keep your meal history for the future, copy `data/nutrivault.db` to another folder before deleting.
3. **Delete the Folder:**
   * **On Mac:** Drag the **`NutriVault-main`** folder to the **Trash**, then right-click the Trash icon and click **Empty Trash**.
   * **On Windows:** Right-click the **`NutriVault-main`** folder, click **Delete**, and empty your **Recycle Bin**.
   * **On Linux:** Move the **`NutriVault-main`** folder to the **Trash** (or press `Shift + Delete` to delete it permanently).

### 2. Remove the App Icon from Your Phone
* **On iPhone:** Touch and hold the **NutriVault 🥗** icon on your Home Screen, tap **Remove App**, and tap **Delete**.
* **On Android:** Touch and hold the **NutriVault 🥗** icon on your Home Screen and drag it to **Uninstall** (or tap **App info $\rightarrow$ Uninstall**).

### 3. Optional Deep Cleanup (If You Used Docker or the First-Time Python Helper)
* **If you used Docker Desktop:** Open **Docker Desktop**, go to the **Containers** and **Images** tabs, and click the trash can icon next to `nutrivault` and `nutrivault-vlm`.
* **If NutriVault installed the lightweight Python helper (`uv`) during first launch:** You can delete the `.local/bin/uv` file in your user home folder (`~/.local/bin/uv` on Mac/Linux, or `C:\Users\<YourName>\.local\bin\uv.exe` on Windows).

