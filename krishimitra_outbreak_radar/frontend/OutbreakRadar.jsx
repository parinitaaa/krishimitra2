import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const API_BASE =
  (import.meta.env?.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function FitSignals({ signals }) {
  const map = useMap();
  useEffect(() => {
    if (signals.length === 1) {
      map.setView([signals[0].latitude, signals[0].longitude], 9);
    } else if (signals.length > 1) {
      map.fitBounds(signals.map((s) => [s.latitude, s.longitude]), { padding: [35, 35] });
    }
  }, [signals, map]);
  return null;
}

const levelStyle = {
  high: { color: "#dc2626", label: "High activity" },
  moderate: { color: "#ea580c", label: "Moderate activity" },
  watch: { color: "#ca8a04", label: "Watch" },
};

export default function OutbreakRadar() {
  const [days, setDays] = useState("7");
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  async function loadSignals() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/outbreaks?days=${days}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to load outbreak signals");
      setSignals(data.signals || []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e) {
      setError(`${e.message}. Check the backend URL, database connection and CORS settings.`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadSignals(); }, [days]);

  const high = signals.filter((s) => s.level === "high").length;
  const farmers = signals.reduce((sum, s) => sum + s.unique_farmers, 0);

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div>
          <div style={styles.eyebrow}>KRISHIMITRA · ADMIN INTELLIGENCE</div>
          <h1 style={styles.title}>Outbreak Radar</h1>
          <p style={styles.subtitle}>Monitor clusters of recent crop-disease detections.</p>
        </div>
        <div style={styles.controls}>
          <label style={styles.selectLabel}>
            Time window
            <select value={days} onChange={(e) => setDays(e.target.value)} style={styles.select}>
              <option value="1">Last 24 hours</option>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="30">Last 30 days</option>
            </select>
          </label>
          <button onClick={loadSignals} style={styles.refresh} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </header>

      <section style={styles.stats}>
        <Stat label="Potential clusters" value={signals.length} />
        <Stat label="High-activity clusters" value={high} />
        <Stat label="Farmer counts across clusters" value={farmers} />
      </section>

      {error && <div role="alert" style={styles.error}>{error}</div>}

      <section style={styles.mapCard}>
        <div style={styles.mapHeading}>
          <div>
            <h2 style={styles.sectionTitle}>Regional disease activity</h2>
            <p style={styles.small}>Updated {lastUpdated || "—"} · Aggregated locations only</p>
          </div>
          <div style={styles.legend}>
            {Object.entries(levelStyle).map(([key, value]) => (
              <span key={key} style={styles.legendItem}>
                <i style={{ ...styles.dot, background: value.color }} /> {value.label}
              </span>
            ))}
          </div>
        </div>

        <div style={styles.map}>
          <MapContainer center={[20.5937, 78.9629]} zoom={5} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitSignals signals={signals} />
            {signals.map((signal) => {
              const style = levelStyle[signal.level] || levelStyle.watch;
              return (
                <CircleMarker
                  key={signal.id}
                  center={[signal.latitude, signal.longitude]}
                  radius={Math.min(22, 7 + signal.unique_farmers)}
                  pathOptions={{ color: style.color, fillColor: style.color, fillOpacity: 0.42, weight: 2 }}
                >
                  <Popup>
                    <div style={{ minWidth: 190 }}>
                      <strong style={{ textTransform: "capitalize" }}>{signal.disease}</strong>
                      <p style={{ margin: "6px 0" }}>{style.label}</p>
                      <div>Unique farmers: {signal.unique_farmers}</div>
                      <div>Observations: {signal.observations}</div>
                      <div>Average model confidence: {(signal.average_confidence * 100).toFixed(1)}%</div>
                      <div>Severe observations: {signal.severe_observations}</div>
                      <small>Latest: {new Date(signal.latest_detection).toLocaleString()}</small>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
        {!loading && signals.length === 0 && !error && (
          <div style={styles.empty}>
            No clusters meet the current threshold yet. Add geolocated disease observations to populate the radar.
          </div>
        )}
      </section>

      <section style={styles.tableCard}>
        <h2 style={styles.sectionTitle}>Detected signals</h2>
        {signals.length === 0 ? (
          <p style={styles.small}>No signals to display.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={styles.table}>
              <thead><tr>
                <th style={styles.th}>Disease</th><th style={styles.th}>Activity</th>
                <th style={styles.th}>Farmers</th><th style={styles.th}>Observations</th>
                <th style={styles.th}>Latest detection</th>
              </tr></thead>
              <tbody>
                {signals.map((s) => (
                  <tr key={s.id}>
                    <td style={styles.td}>{s.disease}</td>
                    <td style={styles.td}><span style={{ color: levelStyle[s.level]?.color, fontWeight: 700 }}>{levelStyle[s.level]?.label}</span></td>
                    <td style={styles.td}>{s.unique_farmers}</td>
                    <td style={styles.td}>{s.observations}</td>
                    <td style={styles.td}>{new Date(s.latest_detection).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p style={styles.disclaimer}>
        Radar signals are generated from model detections and location clusters. They are not confirmed outbreaks;
        an agronomist or local authority should verify before issuing public warnings.
      </p>
    </main>
  );
}

function Stat({ label, value }) {
  return <article style={styles.stat}><div style={styles.statValue}>{value}</div><div style={styles.statLabel}>{label}</div></article>;
}

const styles = {
  page: { maxWidth: 1200, margin: "0 auto", padding: "28px 20px", fontFamily: "Inter, system-ui, sans-serif", color: "#17231c" },
  header: { display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 18, alignItems: "end", marginBottom: 22 },
  eyebrow: { color: "#287447", fontSize: 11, letterSpacing: 2, fontWeight: 800 },
  title: { fontSize: "clamp(28px, 4vw, 38px)", margin: "8px 0" },
  subtitle: { color: "#64746a", margin: 0 },
  controls: { display: "flex", gap: 10, alignItems: "end" },
  selectLabel: { display: "flex", flexDirection: "column", gap: 6, fontSize: 12, color: "#64746a" },
  select: { padding: "10px 12px", border: "1px solid #d1ddd4", borderRadius: 9, background: "#fff", color: "#17231c" },
  refresh: { padding: "11px 16px", background: "#216e43", color: "white", border: 0, borderRadius: 9, fontWeight: 700, cursor: "pointer" },
  stats: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 14, marginBottom: 18 },
  stat: { border: "1px solid #e0e8e1", borderRadius: 14, padding: 18, background: "#fff" },
  statValue: { fontSize: 30, fontWeight: 800 },
  statLabel: { color: "#64746a", fontSize: 12, marginTop: 5 },
  mapCard: { border: "1px solid #e0e8e1", borderRadius: 16, padding: 16, background: "#fff", marginBottom: 18 },
  mapHeading: { display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 14 },
  sectionTitle: { fontSize: 18, margin: "0 0 6px" },
  small: { color: "#64746a", fontSize: 12, margin: 0, lineHeight: 1.5 },
  legend: { display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" },
  legendItem: { fontSize: 11, color: "#526258", display: "inline-flex", gap: 5, alignItems: "center" },
  dot: { width: 8, height: 8, borderRadius: "50%", display: "inline-block" },
  map: { height: 480, borderRadius: 12, overflow: "hidden", border: "1px solid #e0e8e1" },
  empty: { padding: 14, color: "#64746a", fontSize: 13 },
  tableCard: { border: "1px solid #e0e8e1", borderRadius: 16, padding: 18, background: "#fff" },
  table: { width: "100%", borderCollapse: "collapse", marginTop: 10, fontSize: 13, textAlign: "left" },
  th: { color: "#64746a", padding: "12px 10px", borderBottom: "1px solid #e0e8e1", fontWeight: 650, whiteSpace: "nowrap" },
  td: { padding: "13px 10px", borderBottom: "1px solid #eef2ee", whiteSpace: "nowrap" },
  error: { padding: 14, borderRadius: 10, marginBottom: 16, background: "#fff0f0", color: "#a51d1d" },
  disclaimer: { fontSize: 12, lineHeight: 1.6, color: "#64746a", marginTop: 14 },
};
