import { useState } from "react";

const API_BASE =
  (import.meta.env?.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const initialValues = {
  N: "90",
  P: "42",
  K: "43",
  temperature: "24",
  humidity: "80",
  ph: "6.5",
  rainfall: "200",
};

const fields = [
  { key: "N", label: "Nitrogen (N)", min: 0, max: 300, step: 1 },
  { key: "P", label: "Phosphorus (P)", min: 0, max: 300, step: 1 },
  { key: "K", label: "Potassium (K)", min: 0, max: 400, step: 1 },
  { key: "temperature", label: "Temperature (°C)", min: -10, max: 60, step: 0.1 },
  { key: "humidity", label: "Relative humidity (%)", min: 0, max: 100, step: 0.1 },
  { key: "ph", label: "Soil pH", min: 0, max: 14, step: 0.1 },
  { key: "rainfall", label: "Rainfall (mm)", min: 0, max: 3000, step: 1 },
];

export default function CropRecommendation() {
  const [values, setValues] = useState(initialValues);
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(key, value) {
    setValues((old) => ({ ...old, [key]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResults([]);

    try {
      const payload = Object.fromEntries(
        Object.entries(values).map(([key, value]) => [key, Number(value)])
      );

      const response = await fetch(`${API_BASE}/api/crops/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `Request failed (${response.status})`);
      }

      setResults(data.recommendations || []);
    } catch (err) {
      setError(
        `${err.message}. Check that the FastAPI server is running and CORS is configured.`
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section style={styles.page}>
      <div style={styles.header}>
        <div style={styles.eyebrow}>KRISHIMITRA · SMART FARMING</div>
        <h1 style={styles.title}>Crop Recommendation</h1>
        <p style={styles.subtitle}>
          Enter soil and climate values to see the model's top crop predictions.
        </p>
      </div>

      <form onSubmit={handleSubmit} style={styles.card}>
        <div style={styles.grid}>
          {fields.map((field) => (
            <label key={field.key} style={styles.label}>
              {field.label}
              <input
                required
                type="number"
                min={field.min}
                max={field.max}
                step={field.step}
                value={values[field.key]}
                onChange={(e) => update(field.key, e.target.value)}
                style={styles.input}
              />
            </label>
          ))}
        </div>
        <button disabled={loading} type="submit" style={styles.button}>
          {loading ? "Finding crops…" : "Recommend crops"}
        </button>
        <p style={styles.hint}>
          Demo values are prefilled for UI testing. Replace them with actual measurements before interpreting results.
        </p>
      </form>

      {error && <div role="alert" style={styles.error}>{error}</div>}

      {results.length > 0 && (
        <div style={styles.results}>
          <h2 style={styles.resultTitle}>Top recommendations</h2>
          <div style={styles.resultGrid}>
            {results.map((item, index) => (
              <article key={item.crop} style={styles.resultCard}>
                <div style={styles.rank}>OPTION {index + 1}</div>
                <h3 style={styles.crop}>{item.crop}</h3>
                <div style={styles.score}>{item.model_score}%</div>
                <div style={styles.scoreLabel}>Model score · not yield probability</div>
              </article>
            ))}
          </div>
          <p style={styles.disclaimer}>
            These are model predictions based on the training dataset, not guaranteed yield or profit forecasts.
            Confirm local season, irrigation, soil conditions and regional suitability before planting.
          </p>
        </div>
      )}
    </section>
  );
}

const styles = {
  page: {
    maxWidth: 960, margin: "0 auto", padding: "32px 20px",
    color: "#17231c", fontFamily: "Inter, system-ui, sans-serif",
  },
  header: { marginBottom: 24 },
  eyebrow: { fontSize: 12, fontWeight: 800, letterSpacing: 2, color: "#287447" },
  title: { fontSize: "clamp(28px, 4vw, 40px)", margin: "10px 0 8px" },
  subtitle: { color: "#607066", margin: 0, lineHeight: 1.6 },
  card: { padding: 24, border: "1px solid #dce5dd", borderRadius: 18, background: "#fff" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 },
  label: { display: "flex", flexDirection: "column", gap: 8, fontSize: 14, fontWeight: 650 },
  input: { width: "100%", boxSizing: "border-box", padding: "12px", border: "1px solid #cbd7ce", borderRadius: 9, fontSize: 16 },
  button: { marginTop: 22, border: 0, borderRadius: 10, padding: "13px 20px", background: "#216e43", color: "white", fontWeight: 750, fontSize: 15, cursor: "pointer" },
  hint: { color: "#718078", fontSize: 12, lineHeight: 1.5, marginBottom: 0 },
  error: { marginTop: 18, padding: 14, borderRadius: 10, background: "#fff0f0", color: "#a51d1d" },
  results: { marginTop: 28 },
  resultTitle: { fontSize: 22 },
  resultGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 14 },
  resultCard: { border: "1px solid #dce5dd", borderRadius: 16, padding: 20, background: "#f8fbf8" },
  rank: { color: "#287447", fontSize: 11, letterSpacing: 1.5, fontWeight: 800 },
  crop: { textTransform: "capitalize", fontSize: 24, margin: "12px 0" },
  score: { fontSize: 27, fontWeight: 800 },
  scoreLabel: { color: "#718078", fontSize: 11, lineHeight: 1.4, marginTop: 4 },
  disclaimer: { marginTop: 16, color: "#607066", fontSize: 13, lineHeight: 1.6 },
};
