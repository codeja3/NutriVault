"""Zero-build Progressive Web App (PWA) HTML, CSS, and JavaScript interface."""

import json

PWA_MANIFEST_DICT = {
    "name": "NutriVault",
    "short_name": "NutriVault",
    "description": "Local-First Personal and Family Nutrition Tracker",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#111827",
    "theme_color": "#10b981",
    "icons": [
        {
            "src": (
                "data:image/svg+xml,"
                "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
                "<text y='.9em' font-size='90'>🥗</text></svg>"
            ),
            "sizes": "192x192 512x512",
            "type": "image/svg+xml",
        }
    ],
}


def GET_PWA_MANIFEST() -> str:
    """Return JSON manifest for installable Progressive Web App."""
    return json.dumps(PWA_MANIFEST_DICT, indent=2)


def GET_PWA_SERVICE_WORKER() -> str:
    """Return vanilla Service Worker script providing offline-first caching with zero CDN links."""
    return """const CACHE_NAME = 'nutrivault-cache-v1';
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/api/v1/profiles',
  '/api/v1/foods/catalog'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(PRECACHE_URLS).catch(err => {
        console.warn('Pre-cache warning:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') {
    return;
  }

  const url = new URL(event.request.url);

  // API calls: Network-first with cache fallback
  if (url.pathname.startsWith('/api/v1/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Shell navigation and assets: Cache-first with network revalidation
  event.respondWith(
    caches.match(event.request).then(cached => {
      const fetchPromise = fetch(event.request)
        .then(networkResponse => {
          if (networkResponse.ok) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return networkResponse;
        })
        .catch(err => {
          if (!cached && event.request.mode === 'navigate') {
            return caches.match('/');
          }
          throw err;
        });
      return cached || fetchPromise;
    })
  );
});
"""


def GET_PWA_HTML() -> str:
    """Return complete zero-build single-page application with zero external CDN dependencies."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#10b981">
  <link rel="manifest" href="/manifest.json">
  <title>NutriVault - Local-First Nutrition Tracker</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #10b981;
      --primary-hover: #059669;
      --accent: #3b82f6;
      --danger: #ef4444;
      --warning: #f59e0b;
      --warning-bg: rgba(245, 158, 11, 0.15);
      --radius: 8px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 16px;
      max-width: 1200px;
      margin: 0 auto;
    }
    header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
    }
    .brand h1 {
      font-size: 1.6rem;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand p { font-size: 0.85rem; color: var(--text-muted); }
    .hw-badge {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      padding: 6px 12px;
      border-radius: var(--radius);
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .hw-badge .tier-tag {
      background: var(--primary);
      color: #0f172a;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: bold;
    }
    button {
      background: var(--primary);
      color: #0f172a;
      border: none;
      padding: 8px 14px;
      border-radius: var(--radius);
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }
    button:hover { background: var(--primary-hover); }
    button.secondary {
      background: var(--card-bg);
      color: var(--text);
      border: 1px solid var(--card-border);
    }
    button.secondary:hover { background: #334155; }
    button.danger { background: var(--danger); color: #fff; }
    input, select, textarea {
      background: #0f172a;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 8px 12px;
      border-radius: var(--radius);
      font-size: 0.9rem;
      width: 100%;
    }
    .grid { display: grid; grid-template-columns: 1fr; gap: 20px; }
    @media (min-width: 860px) {
      .grid-2 { grid-template-columns: 1fr 1fr; }
      .grid-3 { grid-template-columns: 1fr 1fr 1fr; }
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      padding: 16px;
      margin-bottom: 20px;
    }
    .card h2 {
      font-size: 1.15rem;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .alert-banner {
      padding: 12px;
      border-radius: var(--radius);
      font-size: 0.85rem;
      margin-bottom: 12px;
    }
    .alert-clinical {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid var(--danger);
      color: #fca5a5;
    }
    .alert-athletic {
      background: var(--warning-bg);
      border: 1px solid var(--warning);
      color: #fde68a;
    }
    .drawer {
      background: #0b1120;
      border: 1px solid var(--accent);
      padding: 14px;
      border-radius: var(--radius);
      margin-bottom: 20px;
      display: none;
      font-family: monospace;
      font-size: 0.82rem;
      white-space: pre-wrap;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.85rem; }
    th, td { padding: 8px; text-align: left; border-bottom: 1px solid var(--card-border); }
    th { color: var(--text-muted); font-weight: 600; }
    .search-results { max-height: 220px; overflow-y: auto; margin-top: 8px; }
    .search-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px;
      border-bottom: 1px solid #334155;
    }
    .search-item:hover { background: #334155; }
    .stat-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 10px;
    }
    .stat-card {
      background: #0f172a;
      border: 1px solid var(--card-border);
      padding: 12px;
      border-radius: var(--radius);
      text-align: center;
    }
    .stat-card .val { font-size: 1.4rem; font-weight: bold; color: var(--primary); }
    .stat-card .lbl { font-size: 0.75rem; color: var(--text-muted); }
    .stat-card .delta { font-size: 0.75rem; font-weight: 600; }
    .delta.pos { color: #f87171; }
    .delta.neg { color: #60a5fa; }
    .delta.zero { color: #34d399; }
    .slider-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .slider-row label { flex: 1; font-size: 0.9rem; }
    .slider-row input[type="range"] { flex: 2; }
    .slider-row span { width: 45px; text-align: right; font-weight: bold; }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <h1>🥗 NutriVault</h1>
      <p>Local-First Personal & Family Nutrition Tracker (Zero Cloud Telemetry)</p>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <div class="hw-badge" id="hw-badge">
        <span>Hardware:</span>
        <span class="tier-tag" id="hw-tier">Probing...</span>
      </div>
      <button class="secondary" id="toggle-guide-btn" onclick="toggleVlmGuide()">
        VLM Setup Guide ℹ️
      </button>
    </div>
  </header>

  <div id="vlm-guide-drawer" class="drawer"></div>

  <div id="connectivity-banner" class="alert-banner"
       style="display:flex; justify-content:space-between; align-items:center;
              background:#1e293b; border:1px solid #334155; margin-bottom:16px;">
    <div style="display:flex; align-items:center; gap:8px;">
      <span id="conn-indicator-dot"
            style="width:10px; height:10px; border-radius:50%; background:var(--primary);
                   display:inline-block;"></span>
      <span id="conn-status-text" style="font-weight:600;">Online — Connected to Host</span>
      <span id="offline-queue-badge"
            style="background:#334155; padding:2px 8px; border-radius:12px;
                   font-size:0.75rem; margin-left:8px;">
        Pending Sync: 0
      </span>
    </div>
    <button id="sync-queue-btn" class="secondary" style="padding:4px 10px; font-size:0.8rem;"
            onclick="syncOfflineQueue()">
      Sync Now 🔄
    </button>
  </div>

  <div class="grid grid-2">
    <!-- 1. Household Profiles & Target Envelopes -->
    <div class="card">
      <h2>👤 Household Profile & Targets</h2>
      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <select id="profile-select" onchange="onProfileChange()"></select>
        <button class="secondary" onclick="openNewProfileModal()">+ New</button>
      </div>

      <div id="profile-meta"
           style="font-size:0.85rem; color:var(--text-muted); margin-bottom:12px;"></div>

      <div id="clinical-disclaimer" class="alert-banner alert-clinical" style="display:none;">
        <strong>Clinical Advisory Notice:</strong>
        Nutritional goals for chronic conditions must be established in consultation
        with a qualified physician or registered dietitian.
        NutriVault does not provide clinical diagnoses or therapeutic prescriptions.
      </div>

      <div id="athletic-advisory" class="alert-banner alert-athletic" style="display:none;">
        <strong>Athletic Advisory Wire:</strong>
        Local model fitness baselines are heuristic estimates. For rigorous training regimens
        or metabolic adjustments, consult a certified fitness trainer or cross-reference
        using privacy-preserving frontier endpoints
        (search.brave.com/ask).
        <div style="margin-top:8px;">
          <label style="font-size:0.8rem; display:flex; align-items:center; gap:6px;">
            <input type="checkbox" id="athletic-ack-checkbox" style="width:auto;">
            I acknowledge this advisory guidance
          </label>
        </div>
      </div>

      <div style="margin-top:10px;">
        <h3 style="font-size:0.95rem; margin-bottom:8px;">Daily Target Envelope</h3>
        <div class="grid grid-3" style="gap:8px; margin-bottom:8px;">
          <div>
            <label style="font-size:0.75rem;">Calories</label>
            <input type="number" id="target-calories" placeholder="2000">
          </div>
          <div>
            <label style="font-size:0.75rem;">Protein (g)</label>
            <input type="number" id="target-protein" placeholder="150">
          </div>
          <div>
            <label style="font-size:0.75rem;">Carbs (g)</label>
            <input type="number" id="target-carbs" placeholder="200">
          </div>
          <div>
            <label style="font-size:0.75rem;">Fat (g)</label>
            <input type="number" id="target-fat" placeholder="65">
          </div>
          <div>
            <label style="font-size:0.75rem;">Fiber (g)</label>
            <input type="number" id="target-fiber" placeholder="30">
          </div>
        </div>
        <div style="display:flex; gap:8px;">
          <button onclick="saveTargets()">Save Targets</button>
          <button class="secondary" id="ai-advisor-btn" onclick="suggestAthleticTargets()">
            AI Goal Advisor
          </button>
        </div>
      </div>
    </div>

    <!-- 2. Meal Ingestion (Search & Ephemeral Camera) -->
    <div class="card">
      <h2>🍳 Build & Log Dish</h2>

      <!-- Mode A: Instant USDA Search -->
      <div style="margin-bottom:14px;">
        <label style="font-size:0.8rem; font-weight:600;">
          Instant USDA Food Search (Works Offline / Zero VLM):
        </label>
        <div style="display:flex; gap:8px; margin-top:4px;">
          <input type="text" id="food-search-input"
                 placeholder="Search USDA e.g. brown rice, chicken, oats..."
                 onkeyup="if(event.key==='Enter') searchFood()">
          <input type="number" id="food-search-grams" value="100" style="width:80px;"
                 title="Portion in grams">
          <button onclick="searchFood()">Search</button>
        </div>
        <div id="search-results-container" class="search-results"></div>
      </div>

      <!-- Mode B: Ephemeral Photo Upload -->
      <div style="padding-top:10px; border-top:1px dashed var(--card-border); margin-bottom:14px;">
        <label style="font-size:0.8rem; font-weight:600;">
          Ephemeral Meal Photo (In-Memory VLM & 0x00 Purge):
        </label>
        <div style="display:flex; gap:8px; margin-top:4px;">
          <input type="file" id="meal-photo-input" accept="image/*" capture="environment">
          <button class="secondary" onclick="parseMealPhoto()">Upload Photo</button>
        </div>
        <div id="vlm-status" style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;">
        </div>
      </div>

      <!-- Mode C: Grocery Barcode Scanner -->
      <div style="padding-top:10px; border-top:1px dashed var(--card-border); margin-bottom:14px;">
        <label style="font-size:0.8rem; font-weight:600;">
          Mode C: Grocery Barcode Scanner (Tier 1-3 Offline / In-Browser):
        </label>
        <div style="display:flex; gap:8px; margin-top:4px;">
          <input type="text" id="manual-barcode-input"
                 placeholder="Scan or enter barcode (e.g. 0030000010204)"
                 onkeyup="if(event.key==='Enter') lookupAndAddBarcode()">
          <input type="number" id="barcode-grams" value="100" style="width:80px;"
                 title="Portion in grams">
          <button onclick="lookupAndAddBarcode()">Lookup</button>
          <button class="secondary" id="toggle-camera-btn"
                  onclick="toggleCameraScanner()">📷 Camera</button>
        </div>
        <video id="barcode-video" autoplay playsinline
               style="display:none; width:100%; max-height:220px; border-radius:var(--radius);
                      margin-top:8px; background:#000;"></video>
        <div id="barcode-status"
             style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;"></div>
      </div>

      <!-- Current Dish Draft -->
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <h3 style="font-size:0.95rem;">Current Dish Draft</h3>
          <input type="text" id="draft-dish-name" value="Family Meal"
                 style="width:160px; font-size:0.8rem;">
        </div>
        <table>
          <thead>
            <tr><th>Item</th><th>Grams</th><th>Calories</th><th>Macros (P/C/F)</th><th></th></tr>
          </thead>
          <tbody id="draft-ingredients-body">
            <tr>
              <td colspan="5" style="text-align:center; color:var(--text-muted);">
                No items in draft. Search or upload photo above.
              </td>
            </tr>
          </tbody>
        </table>
        <div id="draft-totals"
             style="font-size:0.85rem; margin-top:8px; font-weight:600; text-align:right;">
        </div>
      </div>
    </div>
  </div>

  <!-- 3. Family Batch Cooking Splitter -->
  <div class="card">
    <h2>👨‍👩‍👧‍👦 Family Batch Portion Allocator</h2>
    <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:12px;">
      Cook once, log across household members. Distribute fractional portions (&le; 100% total).
    </p>
    <div id="portion-sliders-container"></div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px;">
      <div style="display:flex; align-items:center; gap:8px;">
        <label style="font-size:0.85rem;">Meal Type:</label>
        <select id="meal-type-select" style="width:140px;">
          <option value="dinner">Dinner</option>
          <option value="lunch">Lunch</option>
          <option value="breakfast">Breakfast</option>
          <option value="snack">Snack</option>
          <option value="pre_workout">Pre-Workout</option>
          <option value="post_workout">Post-Workout</option>
        </select>
        <span id="allocation-sum-indicator" style="font-size:0.85rem; font-weight:bold;">
          Total: 0%
        </span>
      </div>
      <button onclick="commitBatchMeal()">Commit Meal to Ledger</button>
    </div>
    <div id="commit-status" style="font-size:0.85rem; margin-top:8px;"></div>
  </div>

  <!-- 4. Rolling 7-Day Analytics & Chrononutrition -->
  <div class="card">
    <h2>📊 Rolling 7-Day Analytics & Chrononutrition</h2>
    <div class="stat-cards" id="analytics-stat-cards">
      <div class="stat-card">
        <div class="val" id="stat-cals">-</div>
        <div class="lbl">7-Day EMA Calories</div>
        <div class="delta" id="delta-cals"></div>
      </div>
      <div class="stat-card">
        <div class="val" id="stat-protein">-</div>
        <div class="lbl">Protein (g)</div>
        <div class="delta" id="delta-protein"></div>
      </div>
      <div class="stat-card">
        <div class="val" id="stat-carbs">-</div>
        <div class="lbl">Carbs (g)</div>
        <div class="delta" id="delta-carbs"></div>
      </div>
      <div class="stat-card">
        <div class="val" id="stat-fat">-</div>
        <div class="lbl">Fat (g)</div>
        <div class="delta" id="delta-fat"></div>
      </div>
      <div class="stat-card">
        <div class="val" id="stat-fiber">-</div>
        <div class="lbl">Fiber (g)</div>
        <div class="delta" id="delta-fiber"></div>
      </div>
    </div>

    <div style="margin-top:16px;">
      <h3 style="font-size:0.95rem; margin-bottom:8px;">Feeding Intervals & Overnight Fasts</h3>
      <table>
        <thead>
          <tr>
            <th>Date</th><th>First Meal</th><th>Last Meal</th>
            <th>Eating Window</th><th>Overnight Fast</th>
          </tr>
        </thead>
        <tbody id="feeding-intervals-body">
          <tr>
            <td colspan="5" style="text-align:center; color:var(--text-muted);">
              No meals recorded in last 7 days.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- New Profile Modal -->
  <div id="new-profile-modal"
       style="display:none; position:fixed; top:0; left:0; width:100%; height:100%;
              background:rgba(0,0,0,0.7); align-items:center; justify-content:center;">
    <div class="card" style="width:380px; max-width:90%;">
      <h2>Create Household Member</h2>
      <div style="display:flex; flex-direction:column; gap:10px;">
        <input type="text" id="new-p-name" placeholder="Name (e.g. Alex)">
        <select id="new-p-type" onchange="toggleConditionNotesInput()">
          <option value="standard">Standard Profile</option>
          <option value="athletic">Athletic Profile</option>
          <option value="chronic_condition">Chronic Health Condition</option>
        </select>
        <input type="date" id="new-p-dob">
        <input type="text" id="new-p-notes"
               placeholder="Condition notes (e.g. Crohn's, CKD, Lupus)" style="display:none;">
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
          <button class="secondary" onclick="closeNewProfileModal()">Cancel</button>
          <button onclick="createNewProfile()">Create</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Custom Barcode Registration Modal (Tier 3) -->
  <div id="register-barcode-modal"
       style="display:none; position:fixed; top:0; left:0; width:100%; height:100%;
              background:rgba(0,0,0,0.7); align-items:center; justify-content:center; z-index:999;">
    <div class="card" style="width:420px; max-width:90%;">
      <h2>📦 Register Custom Barcode (Tier 3)</h2>
      <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:10px;">
        Barcode not recognized. Enter nutrition facts per 100g to save to your local vault.
      </p>
      <div style="display:flex; flex-direction:column; gap:8px;">
        <div>
          <label style="font-size:0.75rem;">Barcode</label>
          <input type="text" id="custom-bc-code" readonly style="background:#1e293b;">
        </div>
        <div>
          <label style="font-size:0.75rem;">Product Description</label>
          <input type="text" id="custom-bc-desc" placeholder="e.g. Greek Nonfat Yogurt">
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
          <div>
            <label style="font-size:0.75rem;">Calories / 100g</label>
            <input type="number" id="custom-bc-cals" value="0">
          </div>
          <div>
            <label style="font-size:0.75rem;">Protein (g) / 100g</label>
            <input type="number" id="custom-bc-protein" value="0" step="0.1">
          </div>
          <div>
            <label style="font-size:0.75rem;">Carbs (g) / 100g</label>
            <input type="number" id="custom-bc-carbs" value="0" step="0.1">
          </div>
          <div>
            <label style="font-size:0.75rem;">Fat (g) / 100g</label>
            <input type="number" id="custom-bc-fat" value="0" step="0.1">
          </div>
        </div>
        <div>
          <label style="font-size:0.75rem;">Fiber (g) / 100g</label>
          <input type="number" id="custom-bc-fiber" value="0" step="0.1">
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:10px;">
          <button class="secondary" onclick="closeBarcodeModal()">Cancel</button>
          <button onclick="submitCustomBarcode()">Save Barcode</button>
        </div>
        <div id="custom-bc-status" style="font-size:0.8rem; margin-top:4px;"></div>
      </div>
    </div>
  </div>

  <script>
    // State
    let state = {
      hardware: null,
      profiles: [],
      activeProfile: null,
      isAiGeneratedDraft: false,
      searchResults: [],
      draftIngredients: [],
      profileAllocations: {}
    };

    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    // Service Worker Registration
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(err => {
        console.warn('SW registration warning:', err);
      });
    }

    // Online / Offline Connectivity Detection
    function updateConnectionStatus() {
      const isOnline = navigator.onLine;
      const dot = document.getElementById('conn-indicator-dot');
      const text = document.getElementById('conn-status-text');
      if (dot && text) {
        if (isOnline) {
          dot.style.background = 'var(--primary)';
          text.innerText = 'Online — Connected to Host';
        } else {
          dot.style.background = 'var(--warning)';
          text.innerText = 'Offline Mode — Snap & Sync Later Active';
        }
      }
      updateOfflineQueueBadge();
    }
    window.addEventListener('online', () => {
      updateConnectionStatus();
      syncOfflineCatalog();
      syncOfflineQueue();
    });
    window.addEventListener('offline', updateConnectionStatus);

    // IndexedDB for Offline Caching & Deferred Sync Queue
    const OFFLINE_DB_NAME = 'nutrivault_offline_db';
    const OFFLINE_DB_VERSION = 1;

    function openOfflineDB() {
      return new Promise((resolve, reject) => {
        const req = indexedDB.open(OFFLINE_DB_NAME, OFFLINE_DB_VERSION);
        req.onupgradeneeded = (e) => {
          const db = e.target.result;
          if (!db.objectStoreNames.contains('offline_foods_cache')) {
            const store = db.createObjectStore('offline_foods_cache', { keyPath: 'fdc_id' });
            store.createIndex('barcode', 'barcode', { unique: false });
          }
          if (!db.objectStoreNames.contains('offline_sync_queue')) {
            db.createObjectStore('offline_sync_queue', { keyPath: 'id', autoIncrement: true });
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }

    async function syncOfflineCatalog() {
      if (!navigator.onLine) return;
      try {
        const res = await fetch('/api/v1/foods/catalog');
        if (!res.ok) return;
        const data = await res.json();
        if (!data.items) return;
        const db = await openOfflineDB();
        const tx = db.transaction('offline_foods_cache', 'readwrite');
        const store = tx.objectStore('offline_foods_cache');
        for (const item of data.items) {
          store.put(item);
        }
      } catch (e) {
        console.warn('Failed to sync offline catalog:', e);
      }
    }

    async function lookupLocalBarcode(code) {
      try {
        const db = await openOfflineDB();
        return new Promise((resolve) => {
          const tx = db.transaction('offline_foods_cache', 'readonly');
          const index = tx.objectStore('offline_foods_cache').index('barcode');
          const req = index.get(code);
          req.onsuccess = () => resolve(req.result || null);
          req.onerror = () => resolve(null);
        });
      } catch (e) {
        return null;
      }
    }

    async function queueOfflineItem(item) {
      const db = await openOfflineDB();
      return new Promise((resolve, reject) => {
        const tx = db.transaction('offline_sync_queue', 'readwrite');
        const store = tx.objectStore('offline_sync_queue');
        const req = store.add(item);
        req.onsuccess = () => {
          updateOfflineQueueBadge();
          resolve(req.result);
        };
        req.onerror = () => reject(req.error);
      });
    }

    async function updateOfflineQueueBadge() {
      try {
        const db = await openOfflineDB();
        const tx = db.transaction('offline_sync_queue', 'readonly');
        const countReq = tx.objectStore('offline_sync_queue').count();
        countReq.onsuccess = () => {
          const badge = document.getElementById('offline-queue-badge');
          if (badge) badge.innerText = `Pending Sync: ${countReq.result}`;
        };
      } catch (e) {
        // Ignore
      }
    }

    // Initialization
    window.addEventListener('DOMContentLoaded', async () => {
      updateConnectionStatus();
      await openOfflineDB();
      syncOfflineCatalog();
      updateOfflineQueueBadge();
      await loadHardware();
      await loadProfiles();
    });

    async function loadHardware() {
      try {
        const res = await fetch('/api/v1/hardware');
        const hw = await res.json();
        state.hardware = hw;
        document.getElementById('hw-tier').innerText = hw.active_tier_ceiling || 'Unknown';
        document.getElementById('hw-badge').title =
          `${hw.os_name} | RAM: ${hw.total_ram_gb}GB | Accel: ${hw.accelerator}`;
      } catch (e) {
        console.error('Failed to probe hardware', e);
      }
    }

    function toggleVlmGuide() {
      const drawer = document.getElementById('vlm-guide-drawer');
      if (drawer.style.display === 'block') {
        drawer.style.display = 'none';
        return;
      }
      if (!state.hardware) return;
      const hw = state.hardware;
      const defVlm = hw.default_vlm || {};
      const vlmName = defVlm.name || 'SmolVLM-500M-Instruct-Q8_0';
      const vlmRepo = defVlm.hf_repo || 'ggml-org/SmolVLM-500M-Instruct-GGUF';
      const vlmSize = defVlm.approx_size_mb || 550;
      const managedCmd = hw.managed_vlm_command ||
        `./llama-server --hf-repo ${vlmRepo} --port 8081 --host 127.0.0.1`;
      drawer.innerText = [
        '===========================================================',
        '               NutriVault Local VLM Setup Guide            ',
        '===========================================================',
        `Host OS:                ${hw.os_name}`,
        `Total System RAM:       ${hw.total_ram_gb} GB`,
        `Accelerator Backend:    ${hw.accelerator.toUpperCase()}`,
        `Active Model Tier:      ${hw.active_tier_ceiling}`,
        '-----------------------------------------------------------',
        `Predefined Default VLM: ${vlmName} (~${vlmSize} MB)`,
        `HuggingFace Repository: ${vlmRepo}`,
        '-----------------------------------------------------------',
        'One-Command Automatic Launch (zero manual file hunting):',
        `  ${managedCmd}`,
        '-----------------------------------------------------------',
        'Alternative Models for This Tier:',
        ...(hw.recommended_models || []).map(m => `  • ${m}`),
        '==========================================================='
      ].join('\\n');
      drawer.style.display = 'block';
    }

    async function loadProfiles() {
      try {
        const res = await fetch('/api/v1/profiles');
        state.profiles = await res.json();
        renderProfileSelect();
        if (state.profiles.length > 0) {
          selectProfile(state.profiles[0].id);
        } else {
          openNewProfileModal();
        }
      } catch (e) {
        console.error('Failed to load profiles', e);
      }
    }

    function renderProfileSelect() {
      const select = document.getElementById('profile-select');
      select.innerHTML = state.profiles.map(p =>
        `<option value="${escapeHtml(p.id)}">` +
        `${escapeHtml(p.name)} (${escapeHtml(p.profile_type)})</option>`
      ).join('');
      renderBatchSliders();
    }

    function onProfileChange() {
      const id = document.getElementById('profile-select').value;
      selectProfile(id);
    }

    async function selectProfile(id) {
      state.activeProfile = state.profiles.find(p => p.id === id);
      state.isAiGeneratedDraft = false;
      if (!state.activeProfile) return;

      const meta = document.getElementById('profile-meta');
      const noteStr = state.activeProfile.condition_notes || 'None';
      meta.innerText = `Type: ${state.activeProfile.profile_type} | Notes: ${noteStr}`;

      const clinBanner = document.getElementById('clinical-disclaimer');
      const athlBanner = document.getElementById('athletic-advisory');
      const aiBtn = document.getElementById('ai-advisor-btn');

      if (state.activeProfile.profile_type === 'chronic_condition') {
        clinBanner.style.display = 'block';
        athlBanner.style.display = 'none';
        aiBtn.disabled = true;
        aiBtn.title = 'AI target generator strictly disabled for chronic conditions.';
      } else if (state.activeProfile.profile_type === 'athletic') {
        clinBanner.style.display = 'none';
        athlBanner.style.display = 'block';
        aiBtn.disabled = false;
        aiBtn.title = '';
      } else {
        clinBanner.style.display = 'none';
        athlBanner.style.display = 'none';
        aiBtn.disabled = false;
        aiBtn.title = '';
      }

      await loadAnalytics(id);
    }

    function openNewProfileModal() {
      document.getElementById('new-profile-modal').style.display = 'flex';
    }
    function closeNewProfileModal() {
      document.getElementById('new-profile-modal').style.display = 'none';
    }
    function toggleConditionNotesInput() {
      const type = document.getElementById('new-p-type').value;
      const isChronic = type === 'chronic_condition';
      document.getElementById('new-p-notes').style.display = isChronic ? 'block' : 'none';
    }
    async function createNewProfile() {
      const name = document.getElementById('new-p-name').value.trim();
      if (!name) return alert('Please enter profile name.');
      const type = document.getElementById('new-p-type').value;
      const dob = document.getElementById('new-p-dob').value || null;
      const notes = document.getElementById('new-p-notes').value.trim() || null;

      try {
        const res = await fetch('/api/v1/profiles', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            name,
            profile_type: type,
            birth_date: dob,
            condition_notes: notes
          })
        });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || 'Failed to create profile');
        }
        closeNewProfileModal();
        await loadProfiles();
      } catch (e) {
        alert(e.message);
      }
    }

    async function suggestAthleticTargets() {
      if (!state.activeProfile) return;
      const weight = prompt('Enter body weight in kg (for macro estimation):', '75.0');
      if (!weight || isNaN(parseFloat(weight))) return;

      try {
        const res = await fetch('/api/v1/advisory/fitness-targets', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            profile_id: state.activeProfile.id,
            athletic_goal: 'general',
            weight_kg: parseFloat(weight)
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        document.getElementById('target-calories').value = data.calories_target;
        document.getElementById('target-protein').value = data.protein_g_target;
        document.getElementById('target-carbs').value = data.carbs_g_target;
        document.getElementById('target-fat').value = data.fat_g_target;
        document.getElementById('target-fiber').value = data.fiber_g_target;
        state.isAiGeneratedDraft = true;
        document.getElementById('athletic-ack-checkbox').checked = false;
        document.getElementById('athletic-advisory').style.display = 'block';
        alert('Heuristic targets applied. Please review and acknowledge the advisory.');
      } catch (e) {
        alert(e.message);
      }
    }

    async function saveTargets() {
      if (!state.activeProfile) return;
      const isAthletic = state.activeProfile.profile_type === 'athletic';
      const ack = document.getElementById('athletic-ack-checkbox').checked;

      const payload = {
        calories_target: parseInt(document.getElementById('target-calories').value) || 2000,
        protein_g_target: parseFloat(document.getElementById('target-protein').value) || 120,
        carbs_g_target: parseFloat(document.getElementById('target-carbs').value) || 200,
        fat_g_target: parseFloat(document.getElementById('target-fat').value) || 60,
        fiber_g_target: parseFloat(document.getElementById('target-fiber').value) || 30,
        is_ai_generated: Boolean(state.isAiGeneratedDraft),
        acknowledged: isAthletic ? ack : false
      };

      try {
        const res = await fetch(`/api/v1/profiles/${state.activeProfile.id}/targets`, {
          method: 'PUT',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to save targets');
        state.isAiGeneratedDraft = false;
        alert('Target envelope saved!');
        await loadAnalytics(state.activeProfile.id);
      } catch (e) {
        alert(e.message);
      }
    }

    // USDA Food Search (Online + Offline IndexedDB Fallback)
    async function searchLocalFoods(q, grams) {
      try {
        const db = await openOfflineDB();
        const items = await new Promise((resolve) => {
          const tx = db.transaction('offline_foods_cache', 'readonly');
          const req = tx.objectStore('offline_foods_cache').getAll();
          req.onsuccess = () => resolve(req.result || []);
          req.onerror = () => resolve([]);
        });
        const tokens = q.toLowerCase().split(/\\s+/).filter(Boolean);
        const factor = grams / 100.0;
        const matched = [];
        for (const it of items) {
          const descLower = (it.description || '').toLowerCase();
          let hits = 0;
          for (const t of tokens) {
            if (descLower.includes(t)) hits += 1;
          }
          if (hits > 0) {
            const scaledMicros = {};
            for (const [k, v] of Object.entries(it.micros_per_100g || {})) {
              scaledMicros[k] = Math.round(v * factor * 1000) / 1000;
            }
            matched.push({
              fdc_id: it.fdc_id,
              description: it.description,
              food_category: it.food_category,
              preparation_state: it.preparation_state,
              confidence_score: hits / tokens.length,
              nutrients: {
                grams: grams,
                calories: Math.round(it.calories_per_100g * factor * 100) / 100,
                protein_g: Math.round(it.protein_g_per_100g * factor * 100) / 100,
                carbs_g: Math.round(it.carbs_g_per_100g * factor * 100) / 100,
                fat_g: Math.round(it.fat_g_per_100g * factor * 100) / 100,
                fiber_g: Math.round(it.fiber_g_per_100g * factor * 100) / 100,
                micronutrients: scaledMicros
              }
            });
          }
        }
        matched.sort((a, b) => b.confidence_score - a.confidence_score);
        return matched.slice(0, 6);
      } catch (e) {
        return [];
      }
    }

    async function searchFood() {
      const q = document.getElementById('food-search-input').value.trim();
      const grams = parseFloat(document.getElementById('food-search-grams').value) || 100;
      if (!q) return;

      const container = document.getElementById('search-results-container');
      container.innerHTML =
        '<div style="padding:8px; font-size:0.8rem; color:var(--text-muted);">' +
        'Searching USDA...</div>';

      try {
        if (!navigator.onLine) {
          state.searchResults = await searchLocalFoods(q, grams);
        } else {
          try {
            const url = `/api/v1/foods/search?q=${encodeURIComponent(q)}&grams=${grams}&limit=6`;
            const res = await fetch(url);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);
            state.searchResults = data.results || [];
          } catch (netErr) {
            state.searchResults = await searchLocalFoods(q, grams);
          }
        }

        if (state.searchResults.length === 0) {
          container.innerHTML =
            '<div style="padding:8px; font-size:0.8rem; color:var(--text-muted);">' +
            'No matching USDA foods found.</div>';
          return;
        }

        container.innerHTML = state.searchResults.map((r, idx) => `
          <div class="search-item">
            <div>
              <div style="font-weight:600; font-size:0.85rem;">${escapeHtml(r.description)}</div>
              <div style="font-size:0.75rem; color:var(--text-muted);">
                ${r.nutrients.grams}g &bull; ${r.nutrients.calories} kcal &bull;
                P: ${r.nutrients.protein_g}g C: ${r.nutrients.carbs_g}g F: ${r.nutrients.fat_g}g
              </div>
            </div>
            <button class="secondary" style="font-size:0.75rem; padding:4px 8px;"
                    onclick="addSearchItemByIndex(${idx})">+ Add</button>
          </div>
        `).join('');
      } catch (e) {
        container.innerHTML =
          `<div style="padding:8px; font-size:0.8rem; color:var(--danger);">` +
          `${escapeHtml(e.message)}</div>`;
      }
    }

    function addSearchItemByIndex(idx) {
      const item = state.searchResults[idx];
      if (!item) return;
      addSearchItemToDraft(item);
    }

    function addSearchItemToDraft(item) {
      state.draftIngredients.push({
        item_name: item.description,
        fdc_id: item.fdc_id,
        grams: item.nutrients.grams,
        calories: item.nutrients.calories,
        protein_g: item.nutrients.protein_g,
        carbs_g: item.nutrients.carbs_g,
        fat_g: item.nutrients.fat_g,
        fiber_g: item.nutrients.fiber_g,
        micros: { ...(item.nutrients.micronutrients || {}) }
      });
      renderDraftTable();
    }

    async function parseMealPhoto() {
      const fileInput = document.getElementById('meal-photo-input');
      if (!fileInput.files || fileInput.files.length === 0) {
        return alert('Please select or capture a photo first.');
      }
      const file = fileInput.files[0];
      const status = document.getElementById('vlm-status');

      if (!navigator.onLine) {
        if (!state.activeProfile) return alert('Select active profile first.');
        const mealType = document.getElementById('meal-type-select').value || 'dinner';
        const dishName = document.getElementById('draft-dish-name').value.trim() || 'Offline Photo';
        await queueOfflineItem({
          type: 'photo',
          blob: file,
          dish_name: dishName,
          allocations: [{
            profile_id: state.activeProfile.id,
            fraction: 1.0,
            meal_type: mealType,
            logged_at: new Date().toISOString()
          }]
        });
        status.innerHTML =
          '<span style="color:var(--warning); font-weight:600;">' +
          'Queued meal photo for Snap & Sync Later (preserves restaurant timestamp)!</span>';
        fileInput.value = '';
        return;
      }

      status.innerText = 'Extracting ingredients via local VLM in volatile memory...';

      const formData = new FormData();
      formData.append('image', file);

      try {
        const res = await fetch('/api/v1/meals/parse-image', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (!res.ok) {
          if (res.status === 503) {
            status.innerHTML =
              '<span style="color:var(--warning);">' +
              'Local VLM (llama-server :8081) is offline. Open "VLM Setup Guide" above ' +
              'or log meals immediately using the USDA search bar!</span>';
            return;
          }
          throw new Error(data.error);
        }

        const items = data.items || [];
        status.innerHTML =
          `<span style="color:var(--primary);">Extracted ${items.length} items & ` +
          'deterministically grounded to USDA. Buffer purged.</span>';
        for (const c of items) {
          const nut = c.nutrients || {};
          state.draftIngredients.push({
            item_name: c.matched_description || c.item_name,
            fdc_id: c.matched_fdc_id !== null && c.matched_fdc_id !== undefined
              ? c.matched_fdc_id : 0,
            grams: nut.grams || 0,
            calories: nut.calories || 0,
            protein_g: nut.protein_g || 0,
            carbs_g: nut.carbs_g || 0,
            fat_g: nut.fat_g || 0,
            fiber_g: nut.fiber_g || 0,
            micros: { ...(nut.micronutrients || {}) }
          });
        }
        renderDraftTable();
      } catch (e) {
        status.innerHTML = `<span style="color:var(--danger);">${escapeHtml(e.message)}</span>`;
      } finally {
        fileInput.value = '';
      }
    }

    function renderDraftTable() {
      const tbody = document.getElementById('draft-ingredients-body');
      if (state.draftIngredients.length === 0) {
        tbody.innerHTML =
          '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">' +
          'No items in draft.</td></tr>';
        document.getElementById('draft-totals').innerText = '';
        return;
      }

      let totalGrams = 0, totalCals = 0, totalP = 0, totalC = 0, totalF = 0;
      tbody.innerHTML = state.draftIngredients.map((ing, idx) => {
        totalGrams += ing.grams;
        totalCals += ing.calories;
        totalP += ing.protein_g;
        totalC += ing.carbs_g;
        totalF += ing.fat_g;
        return `
          <tr>
            <td>${escapeHtml(ing.item_name)}</td>
            <td>
              <input type="number" value="${ing.grams}" style="width:70px; padding:2px 4px;"
                     onchange="updateDraftGrams(${idx}, this.value)">
            </td>
            <td>${ing.calories.toFixed(1)}</td>
            <td>
              ${ing.protein_g.toFixed(1)} / ${ing.carbs_g.toFixed(1)} / ${ing.fat_g.toFixed(1)}
            </td>
            <td>
              <button class="danger" style="padding:2px 6px; font-size:0.75rem;"
                      onclick="removeDraftItem(${idx})">&times;</button>
            </td>
          </tr>
        `;
      }).join('');

      document.getElementById('draft-totals').innerText =
        `Total: ${totalGrams.toFixed(0)}g | ${totalCals.toFixed(0)} kcal ` +
        `(P: ${totalP.toFixed(1)}g, C: ${totalC.toFixed(1)}g, F: ${totalF.toFixed(1)}g)`;
    }

    function updateDraftGrams(idx, newGrams) {
      const g = parseFloat(newGrams);
      if (isNaN(g) || g <= 0) return;
      const ing = state.draftIngredients[idx];
      if (!ing || ing.grams <= 0) return;
      const factor = g / ing.grams;
      ing.grams = Math.round(g * 100) / 100;
      ing.calories = Math.round(ing.calories * factor * 100) / 100;
      ing.protein_g = Math.round(ing.protein_g * factor * 100) / 100;
      ing.carbs_g = Math.round(ing.carbs_g * factor * 100) / 100;
      ing.fat_g = Math.round(ing.fat_g * factor * 100) / 100;
      ing.fiber_g = Math.round(ing.fiber_g * factor * 100) / 100;
      if (ing.micros) {
        const scaledMicros = {};
        for (const [k, v] of Object.entries(ing.micros)) {
          scaledMicros[k] = Math.round(v * factor * 1000) / 1000;
        }
        ing.micros = scaledMicros;
      }
      renderDraftTable();
    }

    function removeDraftItem(idx) {
      state.draftIngredients.splice(idx, 1);
      renderDraftTable();
    }

    // Batch Sliders
    function renderBatchSliders() {
      const container = document.getElementById('portion-sliders-container');
      if (state.profiles.length === 0) {
        container.innerHTML =
          '<div style="color:var(--text-muted); font-size:0.85rem;">' +
          'No profiles created yet.</div>';
        return;
      }

      container.innerHTML = state.profiles.map(p => {
        const val = (state.profiles.length === 1) ? 100 : Math.floor(100 / state.profiles.length);
        state.profileAllocations[p.id] = val;
        const safeId = escapeHtml(p.id);
        return `
          <div class="slider-row">
            <label>${escapeHtml(p.name)}:</label>
            <input type="range" min="0" max="100" step="5" value="${val}"
                   id="slider-${safeId}" oninput="onSliderInput('${safeId}', this.value)">
            <span id="slider-val-${safeId}">${val}%</span>
          </div>
        `;
      }).join('');
      updateAllocationSum();
    }

    function onSliderInput(pid, val) {
      state.profileAllocations[pid] = parseInt(val);
      document.getElementById(`slider-val-${pid}`).innerText = `${val}%`;
      updateAllocationSum();
    }

    function updateAllocationSum() {
      const sum = Object.values(state.profileAllocations).reduce((a, b) => a + b, 0);
      const indicator = document.getElementById('allocation-sum-indicator');
      indicator.innerText = `Total: ${sum}%`;
      if (sum > 100) {
        indicator.style.color = 'var(--danger)';
      } else if (sum === 100) {
        indicator.style.color = 'var(--primary)';
      } else {
        indicator.style.color = 'var(--warning)';
      }
    }

    async function commitBatchMeal() {
      if (state.draftIngredients.length === 0) {
        return alert('Dish draft is empty. Add ingredients first.');
      }
      const dishName = document.getElementById('draft-dish-name').value.trim() || 'Shared Dish';
      const mealType = document.getElementById('meal-type-select').value;

      const allocations = [];
      let totalFraction = 0;
      for (const [pid, pct] of Object.entries(state.profileAllocations)) {
        if (pct > 0) {
          const fraction = pct / 100.0;
          allocations.push({ profile_id: pid, fraction, meal_type: mealType });
          totalFraction += fraction;
        }
      }

      if (allocations.length === 0) {
        return alert('Please allocate at least 1% to a household member.');
      }
      if (totalFraction > 1.0001) {
        return alert(`Total allocation (${(totalFraction*100).toFixed(0)}%) exceeds 100%.`);
      }

      const commitStatus = document.getElementById('commit-status');
      commitStatus.innerText = 'Committing atomically to SQLite ledger...';

      if (!navigator.onLine) {
        const queuedMeal = {
          type: 'meal',
          dish_name: dishName,
          ingredients: state.draftIngredients,
          allocations: allocations.map(a => ({
            ...a,
            logged_at: new Date().toISOString()
          }))
        };
        await queueOfflineItem(queuedMeal);
        commitStatus.innerHTML =
          `<span style="color:var(--warning); font-weight:600;">` +
          `Saved "${escapeHtml(dishName)}" to Offline Queue (Snap & Sync Later active)!</span>`;
        state.draftIngredients = [];
        renderDraftTable();
        return;
      }

      try {
        const payload = {
          dish_name: dishName,
          ingredients: state.draftIngredients,
          allocations: allocations
        };
        const res = await fetch('/api/v1/meals/commit', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        const logCount = (data.meal_log_ids || []).length;
        commitStatus.innerHTML =
          `<span style="color:var(--primary); font-weight:600;">` +
          `Committed dish "${escapeHtml(dishName)}" across ${logCount} ` +
          `profile journal(s)!</span>`;
        state.draftIngredients = [];
        renderDraftTable();
        if (state.activeProfile) await loadAnalytics(state.activeProfile.id);
      } catch (e) {
        commitStatus.innerHTML =
          `<span style="color:var(--danger);">${escapeHtml(e.message)}</span>`;
      }
    }

    // Offline Batch Syncing
    async function requeueUnresolvedBarcodes(unresolvedList) {
      if (!unresolvedList || unresolvedList.length === 0) return;
      for (const u of unresolvedList) {
        await queueOfflineItem({
          type: 'barcode',
          barcode: u.barcode,
          grams: u.grams,
          dish_name: `Scanned Product (${u.barcode})`,
          allocations: u.allocations
        });
      }
    }

    async function syncOfflineQueue() {
      const btn = document.getElementById('sync-queue-btn');
      btn.innerText = 'Syncing...';
      try {
        const db = await openOfflineDB();
        const tx = db.transaction('offline_sync_queue', 'readonly');
        const store = tx.objectStore('offline_sync_queue');
        const req = store.getAll();
        req.onsuccess = async () => {
          const items = req.result;
          if (!items || items.length === 0) {
            btn.innerText = 'Sync Now 🔄';
            alert('Offline queue is empty.');
            return;
          }

          const queuedMeals = [];
          const queuedBarcodes = [];
          const failedPhotos = [];
          for (const it of items) {
            if (it.type === 'meal') {
              queuedMeals.push({
                dish_name: it.dish_name,
                ingredients: it.ingredients,
                allocations: it.allocations
              });
            } else if (it.type === 'barcode') {
              queuedBarcodes.push({
                barcode: it.barcode,
                grams: it.grams,
                dish_name: it.dish_name,
                allocations: it.allocations
              });
            } else if (it.type === 'photo' && it.blob) {
              try {
                const fd = new FormData();
                fd.append('image', it.blob);
                const pRes = await fetch('/api/v1/meals/parse-image', { method: 'POST', body: fd });
                const pData = await pRes.json();
                if (pRes.ok && pData.items && pData.items.length > 0) {
                  const ings = pData.items.map(c => {
                    const nut = c.nutrients || {};
                    return {
                      item_name: c.matched_description || c.item_name,
                      fdc_id: c.matched_fdc_id !== null && c.matched_fdc_id !== undefined
                        ? c.matched_fdc_id : 0,
                      grams: nut.grams || 0,
                      calories: nut.calories || 0,
                      protein_g: nut.protein_g || 0,
                      carbs_g: nut.carbs_g || 0,
                      fat_g: nut.fat_g || 0,
                      fiber_g: nut.fiber_g || 0,
                      micros: { ...(nut.micronutrients || {}) }
                    };
                  });
                  queuedMeals.push({
                    dish_name: it.dish_name || 'Synced Photo Meal',
                    ingredients: ings,
                    allocations: it.allocations
                  });
                } else {
                  failedPhotos.push(it);
                }
              } catch (photoErr) {
                failedPhotos.push(it);
              }
            }
          }

          let syncData = { synced_meals_count: 0, unresolved_barcodes: [] };
          if (queuedMeals.length > 0 || queuedBarcodes.length > 0) {
            const syncRes = await fetch('/api/v1/sync/batch', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                queued_meals: queuedMeals,
                queued_barcodes: queuedBarcodes
              })
            });
            syncData = await syncRes.json();
            if (!syncRes.ok) throw new Error(syncData.error || 'Sync failed.');
          }

          const clearTx = db.transaction('offline_sync_queue', 'readwrite');
          clearTx.objectStore('offline_sync_queue').clear();
          clearTx.oncomplete = async () => {
            await requeueUnresolvedBarcodes(syncData.unresolved_barcodes);
            for (const fp of failedPhotos) {
              await queueOfflineItem(fp);
            }
            updateOfflineQueueBadge();
            btn.innerText = 'Sync Now 🔄';
            alert(`Synced ${syncData.synced_meals_count} meals successfully!`);
            if (syncData.unresolved_barcodes && syncData.unresolved_barcodes.length > 0) {
              const unresolved = syncData.unresolved_barcodes[0];
              openBarcodeModal(unresolved.barcode);
            }
            if (state.activeProfile) loadAnalytics(state.activeProfile.id);
          };
        };
      } catch (e) {
        btn.innerText = 'Sync Now 🔄';
        alert(`Sync error: ${e.message}`);
      }
    }

    // Barcode Lookup & Camera Scanner
    async function lookupAndAddBarcode() {
      const input = document.getElementById('manual-barcode-input');
      const gramsInput = document.getElementById('barcode-grams');
      const status = document.getElementById('barcode-status');
      const rawCode = (input.value || '').trim();
      const grams = parseFloat(gramsInput.value || '100');

      if (!rawCode) {
        status.innerText = 'Please enter a barcode.';
        return;
      }
      if (isNaN(grams) || grams <= 0) {
        status.innerText = 'Portion grams must be > 0.';
        return;
      }

      status.innerText = 'Looking up barcode...';

      // 1. Tier 1: Check local IndexedDB first (<10ms)
      const localItem = await lookupLocalBarcode(rawCode);
      if (localItem) {
        const factor = grams / 100.0;
        const scaledMicros = {};
        for (const [k, v] of Object.entries(localItem.micros_per_100g || {})) {
          scaledMicros[k] = Math.round(v * factor * 1000) / 1000;
        }
        state.draftIngredients.push({
          item_name: localItem.description,
          fdc_id: localItem.fdc_id,
          grams: grams,
          calories: Math.round(localItem.calories_per_100g * factor * 100) / 100,
          protein_g: Math.round(localItem.protein_g_per_100g * factor * 100) / 100,
          carbs_g: Math.round(localItem.carbs_g_per_100g * factor * 100) / 100,
          fat_g: Math.round(localItem.fat_g_per_100g * factor * 100) / 100,
          fiber_g: Math.round(localItem.fiber_g_per_100g * factor * 100) / 100,
          micros: scaledMicros
        });
        renderDraftTable();
        status.innerHTML =
          `<span style="color:var(--primary);">` +
          `Found in local cache: ${escapeHtml(localItem.description)}</span>`;
        input.value = '';
        return;
      }

      // 2. Tier 2: Check backend REST API if online
      if (navigator.onLine) {
        try {
          const encCode = encodeURIComponent(rawCode);
          const res = await fetch(`/api/v1/foods/barcode/${encCode}?grams=${grams}`);
          if (res.status === 404) {
            status.innerHTML =
              `<span style="color:var(--warning);">Unknown barcode. Register below.</span>`;
            openBarcodeModal(rawCode);
            return;
          }
          const item = await res.json();
          if (!res.ok) throw new Error(item.error || 'Barcode lookup failed.');

          state.draftIngredients.push({
            item_name: item.description,
            fdc_id: item.fdc_id,
            grams: item.nutrients.grams,
            calories: item.nutrients.calories,
            protein_g: item.nutrients.protein_g,
            carbs_g: item.nutrients.carbs_g,
            fat_g: item.nutrients.fat_g,
            fiber_g: item.nutrients.fiber_g,
            micros: item.nutrients.micronutrients || {}
          });
          renderDraftTable();
          status.innerHTML =
            `<span style="color:var(--primary);">Added: ${escapeHtml(item.description)}</span>`;
          input.value = '';
          return;
        } catch (e) {
          status.innerHTML = `<span style="color:var(--danger);">${escapeHtml(e.message)}</span>`;
          return;
        }
      }

      // 3. Deferred offline barcode scan
      if (confirm(`Barcode ${rawCode} is not in offline cache. Queue for sync when reconnected?`)) {
        if (!state.activeProfile) return alert('Select active profile first.');
        await queueOfflineItem({
          type: 'barcode',
          barcode: rawCode,
          grams: grams,
          dish_name: `Scanned Product (${rawCode})`,
          allocations: [{
            profile_id: state.activeProfile.id,
            fraction: 1.0,
            meal_type: document.getElementById('meal-type-select').value || 'snack',
            logged_at: new Date().toISOString()
          }]
        });
        status.innerHTML =
          `<span style="color:var(--warning);">` +
          `Queued deferred barcode ${escapeHtml(rawCode)} for later sync.</span>`;
        input.value = '';
      }
    }

    let cameraStream = null;
    let cameraScanning = false;

    async function toggleCameraScanner() {
      const video = document.getElementById('barcode-video');
      const btn = document.getElementById('toggle-camera-btn');
      const status = document.getElementById('barcode-status');

      if (cameraScanning) {
        stopCameraScanner();
        return;
      }

      if (!('BarcodeDetector' in window)) {
        status.innerText = 'BarcodeDetector not supported. Please use manual entry.';
        return;
      }

      try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' }
        });
        video.srcObject = cameraStream;
        video.style.display = 'block';
        btn.innerText = '🛑 Stop Camera';
        cameraScanning = true;
        status.innerText = 'Point camera at grocery barcode...';

        const detector = new window.BarcodeDetector({
          formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128']
        });

        const scanLoop = async () => {
          if (!cameraScanning) return;
          try {
            const barcodes = await detector.detect(video);
            if (barcodes.length > 0) {
              const detected = barcodes[0].rawValue;
              stopCameraScanner();
              document.getElementById('manual-barcode-input').value = detected;
              await lookupAndAddBarcode();
              return;
            }
          } catch (err) {
            // Frame detection error, continue loop
          }
          requestAnimationFrame(scanLoop);
        };
        requestAnimationFrame(scanLoop);
      } catch (err) {
        status.innerText = `Camera access error: ${err.message}`;
        stopCameraScanner();
      }
    }

    function stopCameraScanner() {
      const video = document.getElementById('barcode-video');
      const btn = document.getElementById('toggle-camera-btn');
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
      }
      video.style.display = 'none';
      btn.innerText = '📷 Camera';
      cameraScanning = false;
    }

    // Tier 3 Custom Barcode Registration Modal
    function openBarcodeModal(code) {
      document.getElementById('custom-bc-code').value = code || '';
      document.getElementById('custom-bc-desc').value = '';
      document.getElementById('custom-bc-cals').value = '0';
      document.getElementById('custom-bc-protein').value = '0';
      document.getElementById('custom-bc-carbs').value = '0';
      document.getElementById('custom-bc-fat').value = '0';
      document.getElementById('custom-bc-fiber').value = '0';
      document.getElementById('custom-bc-status').innerText = '';
      document.getElementById('register-barcode-modal').style.display = 'flex';
    }

    function closeBarcodeModal() {
      document.getElementById('register-barcode-modal').style.display = 'none';
    }

    async function submitCustomBarcode() {
      const code = document.getElementById('custom-bc-code').value;
      const desc = document.getElementById('custom-bc-desc').value.trim();
      const cals = parseFloat(document.getElementById('custom-bc-cals').value || '0');
      const protein = parseFloat(document.getElementById('custom-bc-protein').value || '0');
      const carbs = parseFloat(document.getElementById('custom-bc-carbs').value || '0');
      const fat = parseFloat(document.getElementById('custom-bc-fat').value || '0');
      const fiber = parseFloat(document.getElementById('custom-bc-fiber').value || '0');
      const status = document.getElementById('custom-bc-status');

      if (!desc) {
        status.innerText = 'Description cannot be empty.';
        return;
      }

      status.innerText = 'Saving barcode...';
      try {
        const res = await fetch(`/api/v1/foods/barcode/${encodeURIComponent(code)}`, {
          method: 'PUT',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            description: desc,
            calories_per_100g: cals,
            protein_g_per_100g: protein,
            carbs_g_per_100g: carbs,
            fat_g_per_100g: fat,
            fiber_g_per_100g: fiber
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Registration failed.');

        const db = await openOfflineDB();
        const tx = db.transaction('offline_foods_cache', 'readwrite');
        tx.objectStore('offline_foods_cache').put({
          fdc_id: data.fdc_id,
          description: data.description,
          food_category: data.food_category,
          preparation_state: data.preparation_state,
          barcode: data.barcode,
          calories_per_100g: cals,
          protein_g_per_100g: protein,
          carbs_g_per_100g: carbs,
          fat_g_per_100g: fat,
          fiber_g_per_100g: fiber,
          micros_per_100g: {}
        });

        closeBarcodeModal();
        document.getElementById('manual-barcode-input').value = code;
        await lookupAndAddBarcode();
      } catch (e) {
        status.innerHTML = `<span style="color:var(--danger);">${escapeHtml(e.message)}</span>`;
      }
    }

    // Analytics
    async function loadAnalytics(profileId) {
      try {
        const res = await fetch(`/api/v1/analytics/rolling?profile_id=${profileId}&days=7`);
        const data = await res.json();
        if (!res.ok) return;

        const deltas = data.target_deltas || {};

        document.getElementById('stat-cals').innerText =
          data.calories_ema !== undefined && data.calories_ema !== null
            ? data.calories_ema.toFixed(0) : '-';
        document.getElementById('stat-protein').innerText =
          data.protein_g_ema !== undefined && data.protein_g_ema !== null
            ? data.protein_g_ema.toFixed(1) : '-';
        document.getElementById('stat-carbs').innerText =
          data.carbs_g_ema !== undefined && data.carbs_g_ema !== null
            ? data.carbs_g_ema.toFixed(1) : '-';
        document.getElementById('stat-fat').innerText =
          data.fat_g_ema !== undefined && data.fat_g_ema !== null
            ? data.fat_g_ema.toFixed(1) : '-';
        document.getElementById('stat-fiber').innerText =
          data.fiber_g_ema !== undefined && data.fiber_g_ema !== null
            ? data.fiber_g_ema.toFixed(1) : '-';

        formatDelta('delta-cals', deltas.calories, ' kcal');
        formatDelta('delta-protein', deltas.protein_g, 'g');
        formatDelta('delta-carbs', deltas.carbs_g, 'g');
        formatDelta('delta-fat', deltas.fat_g, 'g');
        formatDelta('delta-fiber', deltas.fiber_g, 'g');

        const tbody = document.getElementById('feeding-intervals-body');
        if (!data.feeding_intervals || data.feeding_intervals.length === 0) {
          tbody.innerHTML =
            '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">' +
            'No meals recorded in last 7 days.</td></tr>';
          return;
        }

        tbody.innerHTML = data.feeding_intervals.map(f => {
          const firstMeal = (f.first_meal_time && f.first_meal_time.split(' ')[1])
            || f.first_meal_time || '-';
          const lastMeal = (f.last_meal_time && f.last_meal_time.split(' ')[1])
            || f.last_meal_time || '-';
          const win = f.eating_window_hours !== null ? f.eating_window_hours + ' hrs' : '-';
          const fast = f.overnight_fast_hours !== null ? f.overnight_fast_hours + ' hrs' : '-';
          return `
            <tr>
              <td>${f.date}</td>
              <td>${firstMeal}</td>
              <td>${lastMeal}</td>
              <td>${win}</td>
              <td>${fast}</td>
            </tr>
          `;
        }).join('');
      } catch (e) {
        console.error('Failed to load analytics', e);
      }
    }

    function formatDelta(elemId, val, unit) {
      const el = document.getElementById(elemId);
      if (val === undefined || val === null) {
        el.innerText = '';
        el.className = 'delta';
        return;
      }
      const sign = val > 0 ? '+' : '';
      el.innerText = `${sign}${val}${unit}`;
      el.className = 'delta ' + (val > 0 ? 'pos' : (val < 0 ? 'neg' : 'zero'));
    }
  </script>
</body>
</html>
"""
