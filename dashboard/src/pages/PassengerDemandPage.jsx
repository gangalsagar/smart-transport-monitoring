import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../utils/formatters";

export default function PassengerDemandPage() {
  const [summary, setSummary] = useState({
    total_boardings: 0,
    ticket_boardings: 0,
    pass_boardings: 0,
    suspicious_count: 0,
    invalid_count: 0,
    quality_score: 100,
    bus_capacity: 60,
    routes: [],
    buses: [],
    top_stops: [],
    hourly_demand: [],
  });
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Conductor Interactive Pass Validation Form State
  const [passInput, setPassInput] = useState("P458721");
  const [routeInput, setRouteInput] = useState("25A");
  const [busInput, setBusInput] = useState("BUS-102");
  const [stopInput, setStopInput] = useState("STOP-12");
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);

  // Quick Preset Passes for Demo/Testing
  const presets = [
    { id: "P458721", label: "Valid General Pass (Route 25A)", route: "25A" },
    { id: "STU-9081", label: "Valid Student Pass (Route 25A)", route: "25A" },
    { id: "EXP-2024", label: "Expired Pass (Test Failure)", route: "25A" },
    { id: "RTE-RESTRICT", label: "Wrong Route Pass (Restricted to 999)", route: "25A" },
    { id: "UNKNOWN-99", label: "Unregistered Pass ID", route: "25A" },
  ];

  const fetchData = async () => {
    try {
      setLoading(true);
      setError("");
      const [sumRes, recRes] = await Promise.all([
        fetch(`${API_BASE_URL}/passenger/demand/summary`),
        fetch(`${API_BASE_URL}/passenger/recommendations/frequency`),
      ]);

      if (sumRes.ok) {
        const data = await sumRes.json();
        setSummary(data);
      }
      if (recRes.ok) {
        const recData = await recRes.json();
        setRecommendations(recData.recommendations || []);
      }
    } catch (err) {
      setError("Failed to load passenger demand telemetry from backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleValidatePass = async (e) => {
    e?.preventDefault();
    if (!passInput.trim()) return;

    try {
      setIsValidating(true);
      const res = await fetch(`${API_BASE_URL}/passenger/pass/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pass_id: passInput.trim(),
          route_id: routeInput.trim(),
          bus_id: busInput.trim(),
          stop_id: stopInput.trim(),
        }),
      });

      if (res.ok) {
        const result = await res.json();
        setValidationResult(result);
        fetchData();
      } else {
        setValidationResult({ status: "invalid", reason: "backend_error" });
      }
    } catch (err) {
      setValidationResult({ status: "invalid", reason: "network_error" });
    } finally {
      setIsValidating(false);
    }
  };

  const getStatusBadge = (status) => {
    if (status === "valid") return <span className="status-badge live">VALID PASS</span>;
    if (status === "suspicious") return <span className="status-badge" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#f59e0b", border: "1px solid rgba(245, 158, 11, 0.3)" }}>AUDIT SUSPICIOUS</span>;
    return <span className="status-badge offline">INVALID / REJECTED</span>;
  };

  return (
    <div className="tab-content">
      {/* Top Banner Notice */}
      <div style={{ background: "rgba(255, 255, 255, 0.7)", backdropFilter: "blur(8px)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "16px 20px", marginBottom: "24px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "24px" }}>👥</span>
          <div>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "#111111" }}>
              Module 4: Passenger Demand Intelligence
            </div>
            <div style={{ fontSize: "12.5px", color: "var(--muted)" }}>
              Data-Driven Ridership Telematics &amp; Physical Pass Validation • <strong>No In-Bus Cameras / No Facial Recognition</strong>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <div className="live-clock-pill">
            <span className="pulse-dot green" />
            <span>PASS REGISTRY ACTIVE</span>
          </div>
          <button className="refresh-button" onClick={fetchData} title="Refresh telemetry">
            <span>↻</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="stats-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", marginBottom: "24px" }}>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">TOTAL BOARDINGS</span>
            <span className="stat-icon">📈</span>
          </div>
          <div className="stat-value">{summary.total_boardings}</div>
          <div className="stat-sub">Valid &amp; Audited Passengers</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">NORMAL TICKETS</span>
            <span className="stat-icon">🎟️</span>
          </div>
          <div className="stat-value">{summary.ticket_boardings}</div>
          <div className="stat-sub">Conductor ETM Transactions</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">PHYSICAL BUS PASSES</span>
            <span className="stat-icon">🪪</span>
          </div>
          <div className="stat-value" style={{ color: "#3B82F6" }}>{summary.pass_boardings}</div>
          <div className="stat-sub">Verified against Registry</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">SUSPICIOUS AUDITS</span>
            <span className="stat-icon">⚠️</span>
          </div>
          <div className="stat-value" style={{ color: summary.suspicious_count > 0 ? "#F59E0B" : "var(--muted)" }}>
            {summary.suspicious_count}
          </div>
          <div className="stat-sub">Rate bursts &amp; duplicates</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">DATA QUALITY INDEX</span>
            <span className="stat-icon">🛡️</span>
          </div>
          <div className="stat-value" style={{ color: summary.quality_score >= 90 ? "#10B981" : "#F59E0B" }}>
            {summary.quality_score}%
          </div>
          <div className="stat-sub">Clean entry integrity</div>
        </div>
      </div>

      {/* Grid: Conductor Pass Entry Sandbox & Frequency Recommendations */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "24px", marginBottom: "24px" }}>
        {/* Card: Conductor Physical Pass Entry */}
        <div style={{ background: "#ffffff", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "22px", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 600, color: "#111111", margin: 0 }}>
              Conductor Pass Validation Terminal
            </h3>
            <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", background: "var(--section-bg)", padding: "3px 8px", borderRadius: "4px", border: "1px solid var(--line)" }}>
              ID-LOOKUP
            </span>
          </div>

          <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "16px" }}>
            Conductor inspects physical bus-pass and types unique Pass ID. System performs multi-step temporal and route validity verification without tap-in/tap-out sensors.
          </p>

          <form onSubmit={handleValidatePass} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "11.5px", fontWeight: 500, color: "var(--muted)", display: "block", marginBottom: "4px" }}>
                  PASS NUMBER / PASS ID
                </label>
                <input
                  type="text"
                  value={passInput}
                  onChange={(e) => setPassInput(e.target.value)}
                  placeholder="e.g. P458721"
                  style={{ width: "100%", padding: "10px 12px", border: "1px solid var(--line)", borderRadius: "var(--radius-md)", fontFamily: "var(--font-mono)", fontSize: "14px", fontWeight: 600, textTransform: "uppercase" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "11.5px", fontWeight: 500, color: "var(--muted)", display: "block", marginBottom: "4px" }}>
                  CURRENT ROUTE
                </label>
                <input
                  type="text"
                  value={routeInput}
                  onChange={(e) => setRouteInput(e.target.value)}
                  placeholder="e.g. 25A"
                  style={{ width: "100%", padding: "10px 12px", border: "1px solid var(--line)", borderRadius: "var(--radius-md)", fontSize: "14px", fontWeight: 500 }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "11.5px", fontWeight: 500, color: "var(--muted)", display: "block", marginBottom: "4px" }}>
                  BUS UNIT
                </label>
                <input
                  type="text"
                  value={busInput}
                  onChange={(e) => setBusInput(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--line)", borderRadius: "var(--radius-md)", fontSize: "13px" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "11.5px", fontWeight: 500, color: "var(--muted)", display: "block", marginBottom: "4px" }}>
                  BOARDING STOP
                </label>
                <input
                  type="text"
                  value={stopInput}
                  onChange={(e) => setStopInput(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--line)", borderRadius: "var(--radius-md)", fontSize: "13px" }}
                />
              </div>
            </div>

            {/* Quick Test Presets */}
            <div style={{ marginTop: "4px" }}>
              <div style={{ fontSize: "11px", color: "var(--muted)", marginBottom: "6px" }}>
                Quick Test Scenarios:
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {presets.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => { setPassInput(p.id); setRouteInput(p.route); }}
                    style={{ fontSize: "11.5px", padding: "4px 8px", background: "var(--section-bg)", border: "1px solid var(--line)", borderRadius: "4px", cursor: "pointer" }}
                  >
                    {p.id}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={isValidating}
              className="button button-primary"
              style={{ marginTop: "12px", width: "100%", padding: "12px", justifyContent: "center" }}
            >
              {isValidating ? "Validating Against Registry..." : "Validate & Record Boarding Event"}
            </button>
          </form>

          {/* Validation Feedback Banner */}
          {validationResult && (
            <div style={{ marginTop: "16px", padding: "14px", borderRadius: "var(--radius-md)", border: "1px solid var(--line)", background: validationResult.status === "valid" ? "rgba(16, 185, 129, 0.08)" : validationResult.status === "suspicious" ? "rgba(245, 158, 11, 0.08)" : "rgba(239, 68, 68, 0.08)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <span style={{ fontWeight: 600, fontSize: "13px" }}>Outcome:</span>
                {getStatusBadge(validationResult.status)}
              </div>
              <div style={{ fontSize: "12.5px", color: "var(--muted)" }}>
                Reason: <strong>{validationResult.reason || "None"}</strong> | Pass ID: <code>{validationResult.pass_id || passInput}</code>
              </div>
              {validationResult.event_id && (
                <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--muted)", marginTop: "4px" }}>
                  Event ID: {validationResult.event_id}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Card: Frequency Recommendations */}
        <div style={{ background: "#ffffff", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "22px", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 600, color: "#111111", margin: 0 }}>
              Fleet Frequency Decision Support
            </h3>
            <span style={{ fontSize: "11px", background: "rgba(16, 185, 129, 0.12)", color: "#10b981", padding: "3px 8px", borderRadius: "4px", fontWeight: 600 }}>
              DECISION SUPPORT ONLY
            </span>
          </div>

          <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "16px" }}>
            Compares boarding demand vs configured vehicle capacity (nominal 60 pax). Recommendations are decision aids for transport supervisors; system never automatically dispatches buses.
          </p>

          {recommendations.length === 0 ? (
            <div style={{ textAlign: "center", padding: "32px", color: "var(--muted)", fontSize: "13px" }}>
              No route demand anomalies detected currently. Fleet capacity in equilibrium.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {recommendations.map((rec, i) => (
                <div
                  key={i}
                  style={{
                    padding: "14px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--line)",
                    background: rec.demand_status === "critical" ? "rgba(239, 68, 68, 0.05)" : rec.demand_status === "high" ? "rgba(245, 158, 11, 0.05)" : "var(--section-bg)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontWeight: 700, fontSize: "14px", color: "#111111" }}>Route {rec.route_id}</span>
                      <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                        Load: {(rec.load_factor * 100).toFixed(0)}%
                      </span>
                    </div>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 600,
                        padding: "2px 6px",
                        borderRadius: "3px",
                        background: rec.demand_status === "critical" ? "#ef4444" : rec.demand_status === "high" ? "#f59e0b" : "#10b981",
                        color: "#ffffff",
                      }}
                    >
                      {rec.demand_status.toUpperCase()}
                    </span>
                  </div>

                  <p style={{ fontSize: "12.5px", color: "#374151", margin: 0, lineHeight: 1.5 }}>
                    {rec.recommendation}
                  </p>

                  <div style={{ display: "flex", gap: "16px", marginTop: "8px", fontSize: "11.5px", color: "var(--muted)" }}>
                    <span>Boardings: {rec.hourly_boardings}</span>
                    <span>Cap: {rec.total_capacity}</span>
                    <span>Trips/hr: {rec.current_trips_per_hour} → {rec.recommended_trips_per_hour}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Hourly Boarding Telemetry Bar Distribution */}
      <div style={{ background: "#ffffff", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "22px", boxShadow: "var(--shadow-sm)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 600, color: "#111111", margin: 0 }}>
              24-Hour Passenger Boarding Profile &amp; Peak Hour Detection
            </h3>
            <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: "4px 0 0 0" }}>
              Hourly aggregation identifying recurring morning and evening high-demand intervals.
            </p>
          </div>
          <div style={{ display: "flex", gap: "12px", alignItems: "center", fontSize: "12px" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "10px", height: "10px", background: "#ef4444", borderRadius: "2px" }} />
              <span>Peak Interval</span>
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "10px", height: "10px", background: "#3B82F6", borderRadius: "2px" }} />
              <span>Standard Volume</span>
            </span>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(24, 1fr)", gap: "4px", alignItems: "flex-end", height: "140px", paddingTop: "20px", borderBottom: "1px solid var(--line)" }}>
          {summary.hourly_demand?.map((item) => {
            const maxVal = Math.max(...summary.hourly_demand.map((d) => d.boardings), 1);
            const heightPercent = Math.max(8, Math.round((item.boardings / maxVal) * 100));
            return (
              <div
                key={item.hour}
                title={`${item.hour_label}: ${item.boardings} boardings (Load: ${item.load_factor})`}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  height: "100%",
                  justifyContent: "flex-end",
                  cursor: "pointer",
                }}
              >
                <span style={{ fontSize: "9px", color: "var(--muted)", marginBottom: "3px" }}>
                  {item.boardings > 0 ? item.boardings : ""}
                </span>
                <div
                  style={{
                    width: "100%",
                    height: `${heightPercent}%`,
                    background: item.is_peak ? "#ef4444" : item.boardings > 0 ? "#3B82F6" : "rgba(0,0,0,0.06)",
                    borderRadius: "2px 2px 0 0",
                    transition: "height 0.3s ease",
                  }}
                />
              </div>
            );
          })}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(24, 1fr)", gap: "4px", marginTop: "8px" }}>
          {summary.hourly_demand?.map((item) => (
            <div key={item.hour} style={{ textAlign: "center", fontSize: "9px", color: "var(--muted)" }}>
              {item.hour % 3 === 0 ? item.hour_label : ""}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
