/* KrishiMitra frontend — only endpoints verified against the live API */
const API_BASE = "http://localhost:8000";

const DISEASES = [
  "Tomato Early blight leaf",
  "Tomato Late blight leaf",
  "Tomato leaf bacterial spot",
  "Tomato leaf mosaic virus",
  "Tomato leaf yellow virus",
  "Tomato mold leaf",
  "Tomato septoria leaf spot",
  "Tomato two spotted spider mites leaf",
  "Tomato leaf",
  "Potato leaf early blight",
  "Potato leaf late blight",
  "Potato leaf",
  "Corn leaf blight",
  "Corn leaf gray spot",
  "Corn rust leaf",
  "Bell_pepper leaf spot",
  "Bell_pepper leaf",
  "Blueberry leaf",
  "Cherry Powdery Mildew leaf",
  "Cherry leaf",
  "Grape leaf black rot",
  "Grape powdery mildew leaf",
  "Grape leaf",
  "Peach leaf bacterial spot",
  "Peach leaf",
  "Squash Powdery mildew leaf",
  "Strawberry leaf scorch",
  "Strawberry leaf",
  "Apple Scab Leaf",
  "Apple rust leaf",
  "Apple leaf",
  "Raspberry leaf",
  "Soyabean leaf",
];

document.addEventListener("DOMContentLoaded", () => {
  fillDiseaseSelects();
  checkApiHealth();
  setInterval(checkApiHealth, 30000);

  document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      switchTab(link.dataset.tab);
    });
  });
});

function fillDiseaseSelects() {
  ["diagnoseDisease", "treatmentDisease", "severityDisease", "progressionDisease"].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = DISEASES.map(d => `<option value="${escHtml(d)}">${escHtml(d)}</option>`).join("");
  });
}

function setDiseaseSelect(selectId, value) {
  const el = document.getElementById(selectId);
  if (!el || !value) return;
  const exists = [...el.options].some(o => o.value === value);
  if (!exists) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    el.prepend(opt);
  }
  el.value = value;
}

function handleDragOver(e) {
  e.preventDefault();
  e.currentTarget.classList.add("drag-over");
}

function handleDrop(e, inputId) {
  e.preventDefault();
  e.currentTarget.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const input = document.getElementById(inputId);
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;
  input.dispatchEvent(new Event("change"));
}

function previewImage(inputId, previewId, zoneId, containerId) {
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  const zone = document.getElementById(zoneId);
  const container = document.getElementById(containerId);
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    preview.src = e.target.result;
    container.style.display = "inline-block";
    zone.style.display = "none";
  };
  reader.readAsDataURL(file);
}

function clearUpload(inputId, previewId, containerId, zoneId) {
  document.getElementById(inputId).value = "";
  document.getElementById(previewId).src = "";
  document.getElementById(containerId).style.display = "none";
  document.getElementById(zoneId).style.display = "";
}

/* ── DETECT ── */
async function runDetect() {
  const file = document.getElementById("detectFile").files[0];
  if (!file) { alert("Upload a plant image first."); return; }

  const formData = new FormData();
  formData.append("file", file);

  showLoading("Running YOLO detection…");
  try {
    const res = await fetch(`${API_BASE}/detect/`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderDetectResult(data);
  } catch (e) {
    renderError("detectResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderDetectResult(data) {
  const el = document.getElementById("detectResult");

  if (data.status === "no_detection" || !data.detections?.length) {
    el.innerHTML = `
      <div class="res-warning">
        <div class="res-title">No disease region detected</div>
        <p style="color:var(--text-secondary);font-size:14px">${escHtml(data.message || "Try another image.")}</p>
        ${renderRaw("detectResult", data)}
      </div>`;
    return;
  }

  const boxes = data.detections.map((d, i) => `
    <div class="detection-box">
      <div class="det-idx">${i + 1}</div>
      <div class="det-info">
        <div class="det-label">${escHtml(d.yolo_label)}</div>
        <div class="det-coords">bbox (${d.bbox.x1}, ${d.bbox.y1}) → (${d.bbox.x2}, ${d.bbox.y2}) · ${d.bbox_pct}% of image</div>
      </div>
      <div class="det-conf">
        <div class="conf-val">${Math.round(d.confidence * 100)}%</div>
        <div class="conf-label">confidence</div>
      </div>
    </div>`).join("");

  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">Detection complete</div>
      <div class="res-grid" style="margin-bottom:16px">
        <div class="res-item"><div class="res-item-label">Detections</div><div class="res-item-value">${data.total}</div></div>
        <div class="res-item"><div class="res-item-label">Image size</div><div class="res-item-value">${data.image_size?.width} × ${data.image_size?.height}</div></div>
      </div>
      ${boxes}
      <p style="font-size:13px;color:var(--text-muted);margin-top:12px">Fields on Diagnose / Treatment / Severity / Progression were auto-filled from the top detection.</p>
      ${renderRaw("detectResult", data)}
    </div>`;

  const first = data.detections[0];
  const label = first.yolo_label || "";
  setDiseaseSelect("diagnoseDisease", label);
  document.getElementById("diagnoseCustom").value = label;
  setDiseaseSelect("treatmentDisease", label);
  document.getElementById("treatmentCustom").value = label;
  setDiseaseSelect("severityDisease", label);
  setDiseaseSelect("progressionDisease", label);
  document.getElementById("progressionBbox").value = first.bbox_pct ?? "";
  document.getElementById("severityW").value = data.image_size?.width ?? "";
  document.getElementById("severityH").value = data.image_size?.height ?? "";
  document.getElementById("bx1").value = first.bbox.x1;
  document.getElementById("by1").value = first.bbox.y1;
  document.getElementById("bx2").value = first.bbox.x2;
  document.getElementById("by2").value = first.bbox.y2;
  document.getElementById("bconf").value = first.confidence;
}

/* ── DIAGNOSE ── */
async function runDiagnose() {
  const file = document.getElementById("diagnoseFile").files[0];
  const disease = diseaseName("diagnoseDisease", "diagnoseCustom");
  const loc = document.getElementById("diagnoseLocation").value.trim() || "India";
  const forceAI = document.getElementById("diagnoseForceAI").checked;

  if (!file) { alert("Upload an image."); return; }
  if (!disease) { alert("Enter a disease name (or run Detect first)."); return; }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("disease_name", disease);
  formData.append("location", loc);
  formData.append("force_ai", forceAI);

  showLoading("Running full diagnosis…");
  try {
    const res = await fetch(`${API_BASE}/diagnose/full`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderDiagnoseResult(data);
  } catch (e) {
    renderError("diagnoseResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderDiagnoseResult(data) {
  const el = document.getElementById("diagnoseResult");
  const d = data.disease_info || {};
  const det = data.detection || {};
  const remedies = d.remedies || {};
  const organic = (remedies.organic || []).map(r => `<li>${escHtml(r)}</li>`).join("");
  const chemical = (remedies.chemical || []).map(r => `<li>${escHtml(r)}</li>`).join("");
  const prevention = (remedies.prevention || []).map(r => `<li>${escHtml(r)}</li>`).join("");

  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">${escHtml(data.display_name || data.disease_name)}</div>
      <div class="res-grid" style="margin-bottom:20px">
        <div class="res-item"><div class="res-item-label">Crop</div><div class="res-item-value">${escHtml(data.crop || "—")}</div></div>
        <div class="res-item"><div class="res-item-label">Source</div><div class="res-item-value" style="font-size:13px">${escHtml(data.source || "—")}</div></div>
        <div class="res-item"><div class="res-item-label">Boxes</div><div class="res-item-value">${det.total_boxes ?? "—"}</div></div>
        <div class="res-item"><div class="res-item-label">Severity</div><div class="res-item-value">${severityBadge(det.overall_severity)}</div></div>
      </div>
      ${d.pathogen ? `<div style="margin-bottom:12px"><strong>Pathogen:</strong> <span style="color:var(--text-secondary)">${escHtml(d.pathogen)}</span></div>` : ""}
      ${d.symptoms ? `<div style="margin-bottom:12px"><strong>Symptoms:</strong> <span style="color:var(--text-secondary)">${escHtml(d.symptoms)}</span></div>` : ""}
      ${d.spread ? `<div style="margin-bottom:12px"><strong>Spread:</strong> <span style="color:var(--text-secondary)">${escHtml(d.spread)}</span></div>` : ""}
      ${d.urgency ? `<div style="margin-bottom:16px"><strong>Urgency:</strong> <span style="color:var(--amber-400)">${escHtml(d.urgency)}</span></div>` : ""}
      ${organic ? `<div class="remedy-block"><h5 class="organic">Organic</h5><ul class="remedy-list organic">${organic}</ul></div>` : ""}
      ${chemical ? `<div class="remedy-block"><h5 class="chemical">Chemical</h5><ul class="remedy-list chemical">${chemical}</ul></div>` : ""}
      ${prevention ? `<div class="remedy-block"><h5 class="prevention">Prevention</h5><ul class="remedy-list prevention">${prevention}</ul></div>` : ""}
      ${d.regional_note ? `<p style="font-size:13px;color:var(--text-muted);margin-top:12px">${escHtml(d.regional_note)}</p>` : ""}
      ${renderRaw("diagnoseResult", data)}
    </div>`;
}

async function checkApiHealth() {
  const dot = document.getElementById("apiStatus");
  const text = document.getElementById("apiStatusText");
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    if (data.status === "ok") {
      dot.className = "status-dot online";
      text.textContent = "API Online";
    } else {
      throw new Error("Not ok");
    }
  } catch {
    dot.className = "status-dot offline";
    text.textContent = "API Offline";
  }
}

function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.getElementById(`tab-${tab}`)?.classList.add("active");
  document.getElementById(`panel-${tab}`)?.classList.add("active");
  document.getElementById("appContainer")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showLoading(msg = "Working…") {
  document.getElementById("loadingText").textContent = msg;
  document.getElementById("loadingOverlay").classList.add("active");
}
function hideLoading() {
  document.getElementById("loadingOverlay").classList.remove("active");
}

function renderError(containerId, msg) {
  document.getElementById(containerId).innerHTML = `
    <div class="res-error">
      <div class="res-title">Error</div>
      <p style="color:var(--text-secondary);font-size:14px">${escHtml(msg)}</p>
    </div>`;
}

function renderRaw(containerId, data) {
  const id = `raw-${containerId}`;
  return `
    <button class="toggle-json" onclick="toggleJson('${id}')">{ } View Raw JSON</button>
    <div id="${id}" class="json-block" style="display:none">${escHtml(JSON.stringify(data, null, 2))}</div>`;
}

function toggleJson(id) {
  const el = document.getElementById(id);
  el.style.display = el.style.display === "none" ? "block" : "none";
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function severityBadge(sev) {
  const level = typeof sev === "object" ? (sev?.level || "Unknown") : (sev || "Unknown");
  return `<span class="sev-badge sev-${level}">${severityEmoji(level)} ${escHtml(level)}</span>`;
}

function severityEmoji(sev) {
  return { Low: "🟢", Mild: "🟢", Moderate: "🟡", Medium: "🟡", High: "🟠", Severe: "🟠", Critical: "🔴" }[sev] || "⚪";
}

function diseaseName(selectId, customId) {
  const custom = document.getElementById(customId)?.value.trim();
  if (custom) return custom;
  return document.getElementById(selectId).value;
}

/* ── TREATMENT ── */
async function runTreatment() {
  const disease = diseaseName("treatmentDisease", "treatmentCustom");
  const loc = document.getElementById("treatmentLocation").value.trim() || "India";
  const forceAI = document.getElementById("treatmentForceAI").checked;
  if (!disease) { alert("Enter a disease name."); return; }

  const formData = new FormData();
  formData.append("disease_name", disease);
  formData.append("location", loc);
  formData.append("force_ai", forceAI);

  showLoading("Fetching treatment plan…");
  try {
    const res = await fetch(`${API_BASE}/treatment/`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderTreatmentResult(data);
  } catch (e) {
    renderError("treatmentResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderTreatmentResult(data) {
  const el = document.getElementById("treatmentResult");
  const remedies = data.remedies || {};
  const organic = (remedies.organic || []).map(r => `<li>${escHtml(r)}</li>`).join("");
  const chemical = (remedies.chemical || []).map(r => `<li>${escHtml(r)}</li>`).join("");
  const prevention = (remedies.prevention || []).map(r => `<li>${escHtml(r)}</li>`).join("");

  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">${escHtml(data.display_name || data.disease_name)}</div>
      <div class="res-grid" style="margin-bottom:20px">
        <div class="res-item"><div class="res-item-label">Crop</div><div class="res-item-value">${escHtml(data.crop || "—")}</div></div>
        <div class="res-item"><div class="res-item-label">Pathogen</div><div class="res-item-value" style="font-size:13px">${escHtml(data.pathogen || "—")}</div></div>
        <div class="res-item"><div class="res-item-label">Urgency</div><div class="res-item-value" style="color:var(--amber-400);font-size:14px">${escHtml(data.urgency || "—")}</div></div>
        <div class="res-item"><div class="res-item-label">Source</div><div class="res-item-value" style="font-size:13px">${escHtml(data.source || "—")}</div></div>
      </div>
      ${data.symptoms ? `<div style="margin-bottom:12px"><strong>Symptoms:</strong> <span style="color:var(--text-secondary)">${escHtml(data.symptoms)}</span></div>` : ""}
      ${data.spread ? `<div style="margin-bottom:16px"><strong>Spread:</strong> <span style="color:var(--text-secondary)">${escHtml(data.spread)}</span></div>` : ""}
      ${organic ? `<div class="remedy-block"><h5 class="organic">Organic</h5><ul class="remedy-list organic">${organic}</ul></div>` : ""}
      ${chemical ? `<div class="remedy-block"><h5 class="chemical">Chemical</h5><ul class="remedy-list chemical">${chemical}</ul></div>` : ""}
      ${prevention ? `<div class="remedy-block"><h5 class="prevention">Prevention</h5><ul class="remedy-list prevention">${prevention}</ul></div>` : ""}
      ${data.regional_note ? `<p style="font-size:13px;color:var(--text-muted);margin-top:12px">${escHtml(data.regional_note)}</p>` : ""}
      ${renderRaw("treatmentResult", data)}
    </div>`;
}

/* ── SEVERITY ── */
async function runSeverity() {
  const disease = document.getElementById("severityDisease").value;
  const w = parseInt(document.getElementById("severityW").value, 10);
  const h = parseInt(document.getElementById("severityH").value, 10);
  const x1 = parseInt(document.getElementById("bx1").value, 10);
  const y1 = parseInt(document.getElementById("by1").value, 10);
  const x2 = parseInt(document.getElementById("bx2").value, 10);
  const y2 = parseInt(document.getElementById("by2").value, 10);
  const conf = parseFloat(document.getElementById("bconf").value);

  if (!disease || !w || !h || [x1, y1, x2, y2, conf].some(Number.isNaN)) {
    alert("Fill in all fields.");
    return;
  }

  showLoading("Calculating severity…");
  try {
    const res = await fetch(`${API_BASE}/severity/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        disease_name: disease,
        image_size: { width: w, height: h },
        detections: [{ bbox: { x1, y1, x2, y2 }, confidence: conf }],
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderSeverityResult(data);
  } catch (e) {
    renderError("severityResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderSeverityResult(data) {
  const el = document.getElementById("severityResult");
  const overall = data.overall_severity;
  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">Severity: ${escHtml(data.disease_name)}</div>
      <div style="margin-bottom:12px">${severityBadge(overall)}</div>
      ${overall?.description ? `<p style="color:var(--text-secondary);margin-bottom:16px">${escHtml(overall.description)}</p>` : ""}
      <div class="res-grid" style="margin-bottom:16px">
        ${overall?.bbox_pct != null ? `<div class="res-item"><div class="res-item-label">Area affected</div><div class="res-item-value">${overall.bbox_pct}%</div></div>` : ""}
        ${overall?.confidence_pct != null ? `<div class="res-item"><div class="res-item-label">Confidence</div><div class="res-item-value">${overall.confidence_pct}%</div></div>` : ""}
      </div>
      ${(data.all_detections || []).map((d, i) => `
        <div class="detection-box">
          <div class="det-idx">${i + 1}</div>
          <div class="det-info">
            <div class="det-label">Detection #${i + 1}</div>
            <div class="det-coords">bbox (${d.bbox.x1}, ${d.bbox.y1}) → (${d.bbox.x2}, ${d.bbox.y2})</div>
          </div>
          <div>${severityBadge(d.severity)}</div>
        </div>`).join("")}
      ${renderRaw("severityResult", data)}
    </div>`;
}

/* ── PROGRESSION ── */
async function runProgression() {
  const disease = document.getElementById("progressionDisease").value;
  const bboxPct = parseFloat(document.getElementById("progressionBbox").value);
  if (!disease || Number.isNaN(bboxPct)) { alert("Fill disease and infected %."); return; }

  showLoading("Predicting progression…");
  try {
    const res = await fetch(`${API_BASE}/progression/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ disease_name: disease, current_bbox_pct: bboxPct }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderProgressionResult(data);
  } catch (e) {
    renderError("progressionResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderProgressionResult(data) {
  const el = document.getElementById("progressionResult");
  const prog = data.progression || {};
  const forecast = prog.daily_projections || prog.forecast || [];

  const bars = forecast.map(f => {
    const pct = f.infected_pct ?? f.pct ?? 0;
    return `
      <div class="prog-bar-wrapper">
        <span class="prog-day">Day ${f.day}</span>
        <div class="prog-bar-bg"><div class="prog-bar" style="width:${Math.min(pct, 100)}%"></div></div>
        <span class="prog-pct">${Number(pct).toFixed(1)}%${f.severity ? ` · ${escHtml(f.severity)}` : ""}</span>
      </div>`;
  }).join("");

  const current = prog.current_infected_pct ?? prog.current_pct;
  const day7 = prog.day_7_infected_pct ?? forecast[forecast.length - 1]?.infected_pct ?? forecast[forecast.length - 1]?.pct;

  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">7-Day Forecast: ${escHtml(data.disease_name)}</div>
      <div class="res-grid" style="margin-bottom:20px">
        <div class="res-item"><div class="res-item-label">Today</div><div class="res-item-value">${current != null ? Number(current).toFixed(1) + "%" : "—"}</div></div>
        <div class="res-item"><div class="res-item-label">Day 7</div><div class="res-item-value" style="color:var(--red-400)">${day7 != null ? Number(day7).toFixed(1) + "%" : "—"}</div></div>
        ${prog.relative_increase_pct != null ? `<div class="res-item"><div class="res-item-label">Relative increase</div><div class="res-item-value">${prog.relative_increase_pct}%</div></div>` : ""}
        ${prog.spread_type ? `<div class="res-item"><div class="res-item-label">Spread type</div><div class="res-item-value">${escHtml(prog.spread_type)}</div></div>` : ""}
      </div>
      ${prog.summary ? `<p style="color:var(--text-secondary);margin-bottom:16px">${escHtml(prog.summary)}</p>` : ""}
      ${bars ? `<div class="progression-chart">${bars}</div>` : ""}
      ${prog.untreated_note ? `<div style="margin-top:16px;padding:14px;background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.2);border-radius:10px;font-size:14px;color:var(--amber-400)">${escHtml(prog.untreated_note)}</div>` : ""}
      ${renderRaw("progressionResult", data)}
    </div>`;
}

/* ── CROP RECOMMENDATION ── */
async function runCropRecommend() {
  const payload = {
    N: Number(document.getElementById("cropN").value),
    P: Number(document.getElementById("cropP").value),
    K: Number(document.getElementById("cropK").value),
    temperature: Number(document.getElementById("cropTemp").value),
    humidity: Number(document.getElementById("cropHumidity").value),
    ph: Number(document.getElementById("cropPh").value),
    rainfall: Number(document.getElementById("cropRainfall").value),
  };

  if (Object.values(payload).some(v => Number.isNaN(v))) {
    alert("Fill in all soil and climate fields with numbers.");
    return;
  }

  showLoading("Finding crops…");
  try {
    const res = await fetch(`${API_BASE}/api/crops/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail;
      const msg = Array.isArray(detail)
        ? detail.map(d => d.msg || JSON.stringify(d)).join("; ")
        : (detail || data.error || `HTTP ${res.status}`);
      throw new Error(msg);
    }
    renderCropResult(data);
  } catch (e) {
    renderError("cropsResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderCropResult(data) {
  const el = document.getElementById("cropsResult");
  const recs = data.recommendations || [];
  if (!recs.length) {
    el.innerHTML = `<div class="res-warning"><div class="res-title">No recommendations returned</div></div>`;
    return;
  }

  const cards = recs.map((item, index) => `
    <div class="crop-result-card ${index === 0 ? "best" : ""}">
      <div class="crop-rank">OPTION ${index + 1}</div>
      <div class="crop-name">${escHtml(item.crop)}</div>
      <div class="crop-score">${item.model_score}%</div>
      <div class="crop-score-label">Model score · not yield probability</div>
    </div>`).join("");

  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">Top recommendations</div>
      <div class="crop-result-grid">${cards}</div>
      <p style="margin-top:16px;font-size:13px;color:var(--text-muted);line-height:1.6">
        ${escHtml(data.note || "These are model predictions based on the training dataset, not guaranteed yield or profit forecasts. Confirm local season, irrigation, soil conditions and regional suitability before planting.")}
      </p>
      ${renderRaw("cropsResult", data)}
    </div>`;
}

/* ── MARKET PRICES ── */
async function runPrices() {
  const commodity = document.getElementById("pricesCommodity").value.trim();
  const state = document.getElementById("pricesState").value.trim();
  if (!commodity) { alert("Enter a commodity."); return; }

  let url = `${API_BASE}/market/prices?commodity=${encodeURIComponent(commodity)}`;
  if (state) url += `&state=${encodeURIComponent(state)}`;

  showLoading("Fetching live prices…");
  try {
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderPricesResult(data);
  } catch (e) {
    renderError("pricesResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderPricesResult(data) {
  const el = document.getElementById("pricesResult");
  if (!data.prices || data.prices.length === 0) {
    el.innerHTML = `<div class="res-warning"><div class="res-title">${escHtml(data.message || "No data found")}</div></div>`;
    return;
  }

  const rows = data.prices.slice(0, 20).map(p => `
    <tr>
      <td>${escHtml(p.market || "—")}</td>
      <td>${escHtml(p.district || "—")}</td>
      <td>${escHtml(p.state || "—")}</td>
      <td class="price-val">₹${(p.modal_price || 0).toLocaleString("en-IN")}</td>
      <td>${escHtml(p.date || "—")}</td>
    </tr>`).join("");

  const s = data.summary || {};
  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">Prices: ${escHtml(data.commodity)}</div>
      <div class="res-grid" style="margin-bottom:16px">
        <div class="res-item"><div class="res-item-label">Min</div><div class="res-item-value" style="color:var(--green-400)">₹${(s.min_price || 0).toLocaleString("en-IN")}</div></div>
        <div class="res-item"><div class="res-item-label">Max</div><div class="res-item-value" style="color:var(--red-400)">₹${(s.max_price || 0).toLocaleString("en-IN")}</div></div>
        <div class="res-item"><div class="res-item-label">Avg</div><div class="res-item-value" style="color:var(--amber-400)">₹${(s.avg_price || 0).toLocaleString("en-IN")}</div></div>
        <div class="res-item"><div class="res-item-label">Mandis</div><div class="res-item-value">${data.total}</div></div>
      </div>
      <table class="price-table">
        <thead><tr><th>Market</th><th>District</th><th>State</th><th>Modal</th><th>Date</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      ${data.total > 20 ? `<p style="font-size:12px;color:var(--text-muted);margin-top:8px">Showing 20 of ${data.total}</p>` : ""}
      ${renderRaw("pricesResult", data)}
    </div>`;
}

/* ── NEARBY ── */
async function runNearby() {
  const location = document.getElementById("nearbyLocation").value.trim();
  const commodity = document.getElementById("nearbyCommodity").value.trim();
  const radius_km = parseFloat(document.getElementById("nearbyRadius").value) || 300;
  const top_n = parseInt(document.getElementById("nearbyTopN").value, 10) || 3;
  if (!location || !commodity) { alert("Enter location and commodity."); return; }

  showLoading("Finding nearby mandis…");
  try {
    const res = await fetch(`${API_BASE}/market/nearby`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ commodity, location, radius_km, top_n }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderNearbyResult(data);
  } catch (e) {
    renderError("nearbyResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderNearbyResult(data) {
  const el = document.getElementById("nearbyResult");
  if (!data.top_mandis || data.top_mandis.length === 0) {
    el.innerHTML = `<div class="res-warning"><div class="res-title">${escHtml(data.message || "No mandis found")}</div></div>`;
    return;
  }

  const cards = data.top_mandis.map((m, i) => `
    <div class="market-card ${i === 0 ? "best" : ""}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          ${i === 0 ? '<span style="font-size:11px;color:var(--green-400);font-weight:700;text-transform:uppercase;letter-spacing:.5px">Best option</span><br>' : ""}
          <div class="market-name">${escHtml(m.market)}, ${escHtml(m.state)}</div>
          <div class="market-meta">${m.distance_km} km · Transport ₹${m.transport_cost}</div>
        </div>
        <div style="text-align:right">
          <div class="market-price">₹${(m.modal_price || 0).toLocaleString("en-IN")}</div>
          <div class="market-net">Net ₹${(m.net_price || 0).toLocaleString("en-IN")}/q</div>
        </div>
      </div>
    </div>`).join("");

  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">Nearby: ${escHtml(data.commodity)}</div>
      ${data.recommendation ? `<div style="margin-bottom:16px;padding:14px;background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);border-radius:10px;font-size:14px;color:var(--green-400)">${escHtml(data.recommendation)}</div>` : ""}
      ${cards}
      ${renderRaw("nearbyResult", data)}
    </div>`;
}

/* ── PREDICT ── */
async function runPredict() {
  const commodity = document.getElementById("predictCommodity").value.trim();
  const market = document.getElementById("predictMarket").value.trim();
  if (!commodity || !market) { alert("Enter commodity and market."); return; }

  showLoading("Predicting prices…");
  try {
    const res = await fetch(
      `${API_BASE}/market/predict?commodity=${encodeURIComponent(commodity)}&market=${encodeURIComponent(market)}`
    );
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderPredictResult(data);
  } catch (e) {
    renderError("predictResult", e.message);
  } finally {
    hideLoading();
  }
}

function renderPredictResult(data) {
  const el = document.getElementById("predictResult");
  const daily = data.daily_predictions || [];
  const rows = daily.map(d => `
    <tr>
      <td>${escHtml(d.date || "—")}</td>
      <td class="price-val">₹${(d.predicted_price || 0).toLocaleString("en-IN")}</td>
    </tr>`).join("");

  el.innerHTML = `
    <div class="res-success">
      <div class="res-title">Forecast: ${escHtml(data.commodity)} @ ${escHtml(data.market || "")}</div>
      <div class="res-grid" style="margin-bottom:16px">
        ${data.current_price != null ? `<div class="res-item"><div class="res-item-label">Current</div><div class="res-item-value">₹${Number(data.current_price).toLocaleString("en-IN")}</div></div>` : ""}
        ${data.day_7_price != null ? `<div class="res-item"><div class="res-item-label">Day 7</div><div class="res-item-value" style="color:var(--green-400)">₹${Number(data.day_7_price).toLocaleString("en-IN")}</div></div>` : ""}
        ${data.change_pct != null ? `<div class="res-item"><div class="res-item-label">Change</div><div class="res-item-value">${data.change_pct}%</div></div>` : ""}
        ${data.trend ? `<div class="res-item"><div class="res-item-label">Trend</div><div class="res-item-value">${escHtml(data.trend)}</div></div>` : ""}
      </div>
      ${data.advice ? `<p style="color:var(--text-secondary);margin-bottom:16px">${escHtml(data.advice)}</p>` : ""}
      ${rows ? `<table class="price-table"><thead><tr><th>Date</th><th>Predicted</th></tr></thead><tbody>${rows}</tbody></table>` : ""}
      ${renderRaw("predictResult", data)}
    </div>`;
}
