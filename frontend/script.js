// ═══════════════════════════════════════════════════
// ⚡ Code Doc Generator — Frontend JavaScript
//
// Backend API runs separately at http://localhost:5000
// Make sure backend/app.py is running before using this
// ═══════════════════════════════════════════════════

// ── BACKEND URL ──────────────────────────────────────
// Change this if your backend runs on a different port
const API = "http://localhost:5000/api";

// ════════════════════════════════════════════════════
// LOGOUT FUNCTION
// ════════════════════════════════════════════════════
async function doLogout() {
  try {
    await fetch('http://localhost:5000/api/auth/logout', 
      {method:'POST', credentials:'include'});
  } catch(e) {}
  localStorage.removeItem('logged_in');
  localStorage.removeItem('user_name');
  localStorage.removeItem('username');
  window.location.href = 'login.html';
}

// ════════════════════════════════════════════════════
// HISTORY FUNCTIONS
// ════════════════════════════════════════════════════
async function toggleHistory() {
  const sidebar = document.getElementById('history-sidebar');
  const overlay = document.getElementById('history-overlay');
  const isOpen = sidebar.classList.contains('open');
  if (isOpen) {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  } else {
    sidebar.classList.add('open');
    overlay.classList.add('show');
    loadHistory();
  }
}

async function loadHistory() {
  const list = document.getElementById('history-list');
  try {
    const history = JSON.parse(localStorage.getItem('code_history') || '[]');
    if (!history || history.length === 0) {
      list.innerHTML = '<div style="color:var(--muted);font-size:0.82rem;padding:20px;text-align:center">No history yet. Start using the app!</div>';
      return;
    }
    const icons = {
      Extract:'🔍', Document:'📄', Explain:'🧠', 
      Complexity:'📊', Plagiarism:'🔎', Translate:'🌐'
    };
    list.innerHTML = history.map(h => `
      <div class="history-item">
        <div class="history-action">
          ${icons[h.action] || '⚡'} ${h.action}
        </div>
        <div class="history-code">${h.code || 'No code snippet'}</div>
        <div class="history-time">
          ${new Date(h.time).toLocaleString()}
        </div>
      </div>
    `).join('');
  } catch(e) {
    list.innerHTML = '<div style="color:var(--danger);padding:20px">Failed to load history</div>';
  }
}

async function saveHistory(action, code, result) {
  try {
    const history = JSON.parse(localStorage.getItem('code_history') || '[]');
    history.unshift({
      id: Date.now(),
      action: action,
      code: code.substring(0, 200),
      preview: result.substring(0, 300),
      time: new Date().toISOString()
    });
    const trimmed = history.slice(0, 20);
    localStorage.setItem('code_history', JSON.stringify(trimmed));
  } catch(e) {
    console.log('History save error:', e);
  }
}

// ════════════════════════════════════════════════════
// STATE
// ════════════════════════════════════════════════════
let currentLang       = "Hindi";
let lastDocumentation = "";
let lastFlowchartB64  = "";

// ════════════════════════════════════════════════════
// TAB SWITCHING
// ════════════════════════════════════════════════════
function switchTab(name) {
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.getElementById("panel-" + name).classList.add("active");
  document.getElementById("tab-"   + name).classList.add("active");
}

// ════════════════════════════════════════════════════
// UTILITIES
// ════════════════════════════════════════════════════
function showSpinner(id, show) {
  const el = document.getElementById(id);
  if (el) el.style.display = show ? "inline-block" : "none";
}

function setOutput(id, text, isEmpty = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.classList.toggle("empty", isEmpty);
}

function clearInput(id) {
  const el = document.getElementById(id);
  if (el) el.value = "";
}

function copyText(id) {
  const text = document.getElementById(id)?.textContent || "";
  navigator.clipboard.writeText(text)
    .then(() => toast("Copied to clipboard!", "success"))
    .catch(()  => toast("Copy failed", "error"));
}

function toast(msg, type = "info") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className   = "show " + type;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.className = ""; }, 3000);
}

// ── Core fetch wrapper ────────────────────────────
async function callAPI(endpoint, body) {
  const res = await fetch(API + endpoint, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body:    JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// ════════════════════════════════════════════════════
// 1 — EXTRACT FUNCTIONS
// ════════════════════════════════════════════════════
async function runExtract() {
  const code = document.getElementById("extract-code").value.trim();
  if (!code) { toast("Please paste some code first.", "error"); return; }

  const btn = document.querySelector('button[onclick="runExtract()"]');
  btn.disabled = true;
  showSpinner("sp-extract", true);
  try {
    const data = await callAPI("/extract", { code });
    const list = document.getElementById("fn-list");

    if (!data.functions?.length) {
      list.innerHTML = `<li style="color:var(--muted);font-size:0.82rem;padding:10px 0">No functions found.</li>`;
      return;
    }

    list.innerHTML = data.functions.map(f => {
      // Auto-detect language prefix
      let prefix = "";
      const args = f.args || [];
      const name = f.name || "";
      
      if (args.includes("self")) {
        prefix = "def ";  // Python
      } else if (name && name[0] === name[0].toLowerCase() && name.slice(1).includes(name.slice(1).toUpperCase())) {
        prefix = "";  // camelCase (Java/JavaScript)
      } else {
        prefix = "";  // Default: no prefix
      }
      
      return `
      <li class="fn-item">
        <span>
          <span class="fn-name">${prefix}${f.name}</span>
          <span style="color:var(--muted)">(${(f.args || []).join(", ")})</span>
        </span>
        <span class="fn-line">Line ${f.line ?? "?"}</span>
      </li>`;
    }).join("");

    const avgArgs = data.functions.reduce((a, f) => a + (f.args?.length || 0), 0) / data.functions.length;
    document.getElementById("extract-stats").style.display = "block";
    document.getElementById("st-count").textContent = data.functions.length;
    document.getElementById("st-args").textContent  = avgArgs.toFixed(1);
    document.getElementById("st-lines").textContent = code.split("\n").length;

    toast(`✅ Extracted ${data.functions.length} function(s)!`, "success");
    saveHistory('Extract', code, JSON.stringify(data.functions));
  } catch (e) {
    toast("Error: " + e.message, "error");
  } finally {
    showSpinner("sp-extract", false);
    btn.disabled = false;
  }
}

// ════════════════════════════════════════════════════
// 2 — GENERATE DOCUMENTATION
// ════════════════════════════════════════════════════
async function runDocument() {
  const code = document.getElementById("doc-code").value.trim();
  if (!code) { toast("Please paste some code first.", "error"); return; }

  const btn = document.querySelector('button[onclick="runDocument()"]');
  btn.disabled = true;
  showSpinner("sp-doc", true);
  setOutput("doc-output", "Generating documentation via Groq AI…", true);

  try {
    const data = await callAPI("/document", { code });
    setOutput("doc-output", data.documentation || "No output received.");
    lastDocumentation = data.documentation || "";
    document.getElementById("export-content").value = lastDocumentation;
    toast("📄 Documentation generated!", "success");
    saveHistory('Document', code, data.documentation);
  } catch (e) {
    setOutput("doc-output", "Error: " + e.message, true);
    toast("API error", "error");
  } finally {
    showSpinner("sp-doc", false);
    btn.disabled = false;
  }
}

// ════════════════════════════════════════════════════
// 3 — EXPLAIN + FLOWCHART
// ════════════════════════════════════════════════════
async function runExplain() {
  const code = document.getElementById("explain-code").value.trim();
  if (!code) { toast("Please paste some code first.", "error"); return; }

  const btn = document.querySelector('button[onclick="runExplain()"]');
  btn.disabled = true;
  showSpinner("sp-explain", true);
  setOutput("explain-output", "Generating explanation via Groq AI…", true);
  document.getElementById("flowchart-wrap").innerHTML =
    `<div class="flowchart-empty">⏳ Rendering flowchart…</div>`;

  try {
    const data = await callAPI("/explain", { code });
    setOutput("explain-output", data.explanation || "No explanation returned.");

    if (data.flowchart_b64) {
      // Server rendered PNG as base64
      lastFlowchartB64 = data.flowchart_b64;
      document.getElementById("flowchart-wrap").innerHTML =
        `<img src="data:image/png;base64,${data.flowchart_b64}"
              alt="Flowchart" style="max-width:100%;border-radius:8px"/>`;
    } else if (data.mermaid_code) {
      // Render with Mermaid CDN in browser
      const wrap = document.getElementById("flowchart-wrap");
      wrap.innerHTML = `<pre class="mermaid">${data.mermaid_code}</pre>`;
      if (window.mermaid) mermaid.run();
    } else {
      document.getElementById("flowchart-wrap").innerHTML =
        `<div class="flowchart-empty">⚠ No flowchart returned</div>`;
    }

    toast("🧠 Explanation + Flowchart ready!", "success");
    saveHistory('Explain', code, data.explanation);
  } catch (e) {
    setOutput("explain-output", "Error: " + e.message, true);
    document.getElementById("flowchart-wrap").innerHTML =
      `<div class="flowchart-empty">Error loading flowchart</div>`;
    toast("API error", "error");
  } finally {
    showSpinner("sp-explain", false);
    btn.disabled = false;
  }
}

// ════════════════════════════════════════════════════
// 4 — COMPLEXITY ANALYSIS
// ════════════════════════════════════════════════════
async function runComplexity() {
  const code = document.getElementById("complexity-code").value.trim();
  if (!code) { toast("Please paste code first.", "error"); return; }

  const btn = document.querySelector('button[onclick="runComplexity()"]');
  btn.disabled = true;
  showSpinner("sp-complexity", true);
  setOutput("complexity-output", "Analyzing complexity via Groq AI…", true);

  try {
    const data = await callAPI("/complexity", { code });
    setOutput("complexity-output", data.complexity || "No analysis returned.");
    toast("📊 Complexity analyzed!", "success");
    saveHistory('Complexity', code, data.complexity);
  } catch (e) {
    setOutput("complexity-output", "Error: " + e.message, true);
    toast("API error", "error");
  } finally {
    showSpinner("sp-complexity", false);
    btn.disabled = false;
  }
}

// ════════════════════════════════════════════════════
// 5 — PLAGIARISM DETECTION
// ════════════════════════════════════════════════════
async function runPlagiarism() {
  const code1 = document.getElementById("plag-code1").value.trim();
  const code2 = document.getElementById("plag-code2").value.trim();
  if (!code1 || !code2) { toast("Please paste both code files.", "error"); return; }

  const btn = document.querySelector('button[onclick="runPlagiarism()"]');
  btn.disabled = true;
  showSpinner("sp-plag", true);

  try {
    const data    = await callAPI("/plagiarism", { code1, code2 });
    const pct     = data.similarity || 0;
    const verdict = pct < 40 ? "low" : pct < 70 ? "moderate" : "high";
    const labels  = {
      low:      "✅ Low Similarity",
      moderate: "⚠️ Moderate Similarity",
      high:     "🚨 High — Possible Plagiarism",
    };

    document.getElementById("plag-result").style.display  = "block";
    document.getElementById("plag-percent").textContent   = pct.toFixed(1) + "%";
    document.getElementById("plag-bar").style.width       = Math.min(pct, 100) + "%";
    document.getElementById("plag-bar").className         = "progress-bar-fill " + verdict;
    document.getElementById("plag-verdict").innerHTML     =
      `<span class="verdict-badge ${verdict}">${labels[verdict]}</span>`;
    setOutput("plag-detail", data.details || "");

    toast("🔎 Plagiarism check complete!", "success");
    saveHistory('Plagiarism', code1, data.verdict);
  } catch (e) {
    toast("Error: " + e.message, "error");
  } finally {
    showSpinner("sp-plag", false);
    btn.disabled = false;
  }
}

// ════════════════════════════════════════════════════
// 6 — TRANSLATE DOCUMENTATION
// ════════════════════════════════════════════════════
function selectLang(el, lang) {
  document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("selected"));
  el.classList.add("selected");
  currentLang = lang;
  document.getElementById("translate-lang-label").textContent = lang;
}

async function runTranslate() {
  const documentation = document.getElementById("translate-input").value.trim();
  if (!documentation) { toast("Please paste documentation to translate.", "error"); return; }

  const btn = document.querySelector('button[onclick="runTranslate()"]');
  btn.disabled = true;
  showSpinner("sp-translate", true);
  setOutput("translate-output", `Translating to ${currentLang} via Groq AI…`, true);

  try {
    const data = await callAPI("/translate", { documentation, language: currentLang });
    setOutput("translate-output", data.translated || "No translation returned.");
    toast(`🌐 Translated to ${currentLang}!`, "success");
    saveHistory('Translate', documentation, data.translated);
  } catch (e) {
    setOutput("translate-output", "Error: " + e.message, true);
    toast("API error", "error");
  } finally {
    showSpinner("sp-translate", false);
    btn.disabled = false;
  }
}

// ════════════════════════════════════════════════════
// 7 — EXPORT  (PDF / TXT / MARKDOWN)
// ════════════════════════════════════════════════════
async function exportFile(type) {
  const title   = document.getElementById("export-title").value.trim() || "Documentation";
  const content = document.getElementById("export-content").value.trim();
  if (!content) { toast("Please add content to export.", "error"); return; }

  if (type === "pdf") showSpinner("sp-pdf", true);

  try {
    const res = await fetch(`${API}/export/${type}`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ title, content }),
    });

    if (!res.ok) throw new Error("Export failed");

    const blob = await res.blob();
    const ext  = { pdf: "pdf", txt: "txt", markdown: "md" }[type];
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = title.replace(/\s+/g, "_") + "." + ext;
    a.click();
    URL.revokeObjectURL(url);

    toast(`✅ ${type.toUpperCase()} downloaded!`, "success");
  } catch (e) {
    toast("Export error: " + e.message, "error");
  } finally {
    if (type === "pdf") showSpinner("sp-pdf", false);
  }
}

function quickExport(type) {
  if (!lastDocumentation) {
    toast("Generate documentation first (Document tab).", "error");
    return;
  }
  document.getElementById("export-content").value = lastDocumentation;
  exportFile(type);
}

// ════════════════════════════════════════════════════
// CHARACTER COUNTERS
// ════════════════════════════════════════════════════
function updateCharCounter(textareaId) {
  const textarea = document.getElementById(textareaId);
  const counter = document.getElementById("counter-" + textareaId);
  const count = textarea.value.length;
  const max = 5000;
  
  counter.textContent = `${count} / ${max} chars`;
  counter.classList.toggle("warning", count > max);
  
  if (count > max) {
    toast("Code is very long — API response may be slow", "warning");
  }
}

// Initialize character counters for all textareas
document.addEventListener("DOMContentLoaded", () => {
  const textareas = [
    "extract-code", "doc-code", "explain-code", "complexity-code",
    "plag-code1", "plag-code2", "translate-input", "export-content"
  ];
  
  textareas.forEach(id => {
    const textarea = document.getElementById(id);
    if (textarea) {
      // Initial update
      updateCharCounter(id);
      // Add event listener
      textarea.addEventListener("input", () => updateCharCounter(id));
    }
  });
});

// ════════════════════════════════════════════════════
// PROFILE FUNCTIONS
// ════════════════════════════════════════════════════
function toggleProfile() {
  const popup = document.getElementById('profile-popup');
  const overlay = document.getElementById('profile-overlay');
  const isOpen = popup.classList.contains('open');
  if (isOpen) {
    popup.classList.remove('open');
    overlay.classList.remove('show');
  } else {
    popup.classList.add('open');
    overlay.classList.add('show');
    loadProfileStats();
    const name = localStorage.getItem('user_name') || 'User';
    const username = localStorage.getItem('username') || 'user';
    document.getElementById('profile-full-name').textContent = name;
    document.getElementById('profile-username').textContent = '@' + username;
    document.getElementById('profile-big-avatar').textContent = 
      name.charAt(0).toUpperCase();
  }
}

function loadProfileStats() {
  const history = JSON.parse(
    localStorage.getItem('code_history') || '[]');
  const total = history.length;
  const docs = history.filter(h => h.action === 'Document').length;
  const extracts = history.filter(h => h.action === 'Extract').length;
  document.getElementById('stat-total').textContent = total;
  document.getElementById('stat-docs').textContent = docs;
  document.getElementById('stat-extracts').textContent = extracts;
}

function toggleTheme() {
  const body = document.body;
  const label = document.getElementById('theme-label');
  if (body.classList.contains('light-mode')) {
    body.classList.remove('light-mode');
    label.textContent = 'Switch to Light Mode';
    localStorage.setItem('theme', 'dark');
  } else {
    body.classList.add('light-mode');
    label.textContent = 'Switch to Dark Mode';
    localStorage.setItem('theme', 'light');
  }
}

function clearAllHistory() {
  if (confirm('Clear all history? This cannot be undone!')) {
    localStorage.removeItem('code_history');
    toast('History cleared!', 'success');
    toggleProfile();
  }
}

function openEditProfile() {
  closeModals();
  toggleProfile();
  const name = localStorage.getItem('user_name') || '';
  const username = localStorage.getItem('username') || '';
  const email = localStorage.getItem('user_email') || '';
  document.getElementById('edit-name-input').value = name;
  document.getElementById('edit-username-input').value = username;
  document.getElementById('edit-email-input').value = email;
  document.getElementById('edit-error').style.display = 'none';
  document.getElementById('edit-success').style.display = 'none';
  document.getElementById('edit-profile-modal').classList.add('open');
  document.getElementById('modal-overlay').classList.add('show');
}

function openChangePassword() {
  closeModals();
  toggleProfile();
  document.getElementById('current-pass-input').value = '';
  document.getElementById('new-pass-input').value = '';
  document.getElementById('confirm-pass-input').value = '';
  document.getElementById('pass-error').style.display = 'none';
  document.getElementById('pass-success').style.display = 'none';
  document.getElementById('change-password-modal').classList.add('open');
  document.getElementById('modal-overlay').classList.add('show');
}

function closeModals() {
  document.getElementById('edit-profile-modal').classList.remove('open');
  document.getElementById('change-password-modal').classList.remove('open');
  document.getElementById('modal-overlay').classList.remove('show');
}

async function saveEditProfile() {
  const newName = document.getElementById('edit-name-input').value.trim();
  const newUsername = document.getElementById('edit-username-input').value.trim();
  const newEmail = document.getElementById('edit-email-input').value.trim();
  const errEl = document.getElementById('edit-error');
  const sucEl = document.getElementById('edit-success');
  errEl.style.display = 'none';
  sucEl.style.display = 'none';

  if (!newName || !newUsername || !newEmail) {
    errEl.textContent = '❌ Please fill all fields!';
    errEl.style.display = 'block';
    return;
  }
  if (!newEmail.includes('@')) {
    errEl.textContent = '❌ Please enter a valid email!';
    errEl.style.display = 'block';
    return;
  }
  if (newUsername.length < 3) {
    errEl.textContent = '❌ Username must be at least 3 characters!';
    errEl.style.display = 'block';
    return;
  }

  try {
    const res = await fetch('http://localhost:5000/api/auth/update-profile', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      credentials: 'include',
      body: JSON.stringify({
        name: newName,
        username: newUsername,
        email: newEmail,
        old_username: localStorage.getItem('username')
      })
    });
    const data = await res.json();
    if (data.error) {
      errEl.textContent = '❌ ' + data.error;
      errEl.style.display = 'block';
      return;
    }
    localStorage.setItem('user_name', newName);
    localStorage.setItem('username', newUsername);
    localStorage.setItem('user_email', newEmail);
    const nameEl = document.getElementById('user-name-display');
    const userEl = document.getElementById('username-display');
    const avatarEl = document.getElementById('user-avatar');
    if (nameEl) nameEl.textContent = newName;
    if (userEl) userEl.textContent = '@' + newUsername;
    if (avatarEl) avatarEl.textContent = newName.charAt(0).toUpperCase();
    sucEl.textContent = '✅ Profile updated successfully!';
    sucEl.style.display = 'block';
    toast('✅ Profile updated!', 'success');
    setTimeout(() => closeModals(), 2000);
  } catch(e) {
    errEl.textContent = '❌ Cannot connect to server!';
    errEl.style.display = 'block';
  }
}

function saveChangePassword() {
  const currentPass = document.getElementById('current-pass-input').value.trim();
  const newPass = document.getElementById('new-pass-input').value.trim();
  const confirmPass = document.getElementById('confirm-pass-input').value.trim();
  const errEl = document.getElementById('pass-error');
  const sucEl = document.getElementById('pass-success');
  errEl.style.display = 'none';
  sucEl.style.display = 'none';
  if (!currentPass || !newPass || !confirmPass) {
    errEl.textContent = '❌ Please fill all fields!';
    errEl.style.display = 'block';
    return;
  }
  if (newPass.length < 6) {
    errEl.textContent = '❌ New password must be at least 6 characters!';
    errEl.style.display = 'block';
    return;
  }
  if (newPass !== confirmPass) {
    errEl.textContent = '❌ Passwords do not match!';
    errEl.style.display = 'block';
    return;
  }
  fetch('http://localhost:5000/api/auth/change-password', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    credentials: 'include',
    body: JSON.stringify({
      current_password: currentPass,
      new_password: newPass,
      username: localStorage.getItem('username')
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      errEl.textContent = '❌ ' + data.error;
      errEl.style.display = 'block';
    } else {
      sucEl.textContent = '✅ Password changed successfully!';
      sucEl.style.display = 'block';
      setTimeout(() => closeModals(), 2000);
    }
  })
  .catch(() => {
    errEl.textContent = '❌ Cannot connect to server!';
    errEl.style.display = 'block';
  });
}

const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
  document.body.classList.add('light-mode');
  const label = document.getElementById('theme-label');
  if (label) label.textContent = 'Switch to Dark Mode';
}

// ════════════════════════════════════════════════════
// BUG FINDER
// ════════════════════════════════════════════════════
async function runBugFinder() {
  const code = document.getElementById('bug-code').value.trim();
  if (!code) { 
    toast('Please paste some code first.', 'error'); 
    return; 
  }
  showSpinner('sp-bug', true);
  setOutput('bug-output', 
    'Analyzing code for bugs via Groq AI...', true);
  document.getElementById('bug-summary').style.display = 'none';
  try {
    const data = await callAPI('/bugfinder', { code });
    setOutput('bug-output', data.report || 'No report returned.');
    document.getElementById('bug-summary').style.display = 'block';
    document.getElementById('bug-count').textContent = 
      data.bugs || 0;
    document.getElementById('warning-count').textContent = 
      data.warnings || 0;
    document.getElementById('suggestion-count').textContent = 
      data.suggestions || 0;
    saveHistory('BugFinder', code, data.report);
    toast('🐛 Bug analysis complete!', 'success');
  } catch(e) {
    setOutput('bug-output', 'Error: ' + e.message, true);
    toast('API error', 'error');
  } finally {
    showSpinner('sp-bug', false);
  }
}