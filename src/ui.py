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
        (<a href="https://search.brave.com/ask" target="_blank"
            style="color:#fde68a;">search.brave.com/ask</a>).
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

    // Initialization
    window.addEventListener('DOMContentLoaded', async () => {
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
      const primaryModel = (hw.recommended_models && hw.recommended_models[0]) || 'model.gguf';
      const mmprojModel = primaryModel.replace('.gguf', '-mmproj-f16.gguf');
      drawer.innerText = [
        '===========================================================',
        '               NutriVault Local VLM Setup Guide            ',
        '===========================================================',
        `Host OS:             ${hw.os_name}`,
        `Total System RAM:    ${hw.total_ram_gb} GB`,
        `Accelerator Backend: ${hw.accelerator.toUpperCase()}`,
        `Active Model Tier:   ${hw.active_tier_ceiling}`,
        '-----------------------------------------------------------',
        'Recommended Models for This Tier:',
        ...(hw.recommended_models || []).map(m => `  • ${m}`),
        '-----------------------------------------------------------',
        'Command to launch llama-server on loopback port 8081:',
        `./llama-server -m ./models/${primaryModel} \\\\`,
        `  --mmproj ./models/${mmprojModel} \\\\`,
        '  --port 8081 --host 127.0.0.1',
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

    // USDA Food Search
    async function searchFood() {
      const q = document.getElementById('food-search-input').value.trim();
      const grams = parseFloat(document.getElementById('food-search-grams').value) || 100;
      if (!q) return;

      const container = document.getElementById('search-results-container');
      container.innerHTML =
        '<div style="padding:8px; font-size:0.8rem; color:var(--text-muted);">' +
        'Searching USDA...</div>';

      try {
        const url = `/api/v1/foods/search?q=${encodeURIComponent(q)}&grams=${grams}&limit=6`;
        const res = await fetch(url);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        state.searchResults = data.results || [];
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
