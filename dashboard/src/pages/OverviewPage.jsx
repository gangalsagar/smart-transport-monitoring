import React from "react";
import { formatTimestamp, formatGPS, getSeverityBadgeClass } from "../utils/formatters";
import Interactive3DCard from "../components/Interactive3DCard";

export default function OverviewPage({ alerts, trafficDensity, onSelectAlert, onSelectTab }) {
  const roadDefects = alerts.filter((a) => a.module?.type === "road_defect");
  const trafficEvents = alerts.filter((a) => a.module?.type === "traffic");
  const incidentEvents = alerts.filter((a) => a.module?.type === "incident_anpr");

  const criticalCount = alerts.filter((a) => a.severity === "critical" || a.severity === "high").length;
  const latestTraffic = trafficEvents.length > 0 ? trafficEvents[trafficEvents.length - 1] : null;
  const vehicleCount = latestTraffic?.payload?.vehicle_count ?? latestTraffic?.payload?.total_vehicle_count ?? 0;
  const congestion = latestTraffic?.payload?.congestion_level || (trafficEvents.length > 0 ? "NORMAL" : "OPTIMAL");

  const recentActivity = [...alerts].reverse().slice(0, 10);

  return (
    <div className="page-container page-fade-enter">
      {/* Top Editorial Header */}
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Transport Operations Command</h1>
          <p>Real-time telemetry across road infrastructure, vehicle flow, incidents, and field intelligence.</p>
        </div>
        <div className="page-header-badges">
          <span className="badge badge-low">
            <span className="pulse-dot green" style={{ width: "5px", height: "5px" }} />
            EDGE AI: ACTIVE
          </span>
          <span className="badge badge-info">GPS: 1.0 HZ LOCKED</span>
          <span className="badge badge-neutral">SYNC: OK</span>
        </div>
      </div>

      {/* Metric Cards Row with 3D Tilt & Specular Highlights */}
      <div className="metric-grid">
        <Interactive3DCard className="metric-card" style={{ cursor: "pointer" }} onClick={() => onSelectTab("defects")}>
          <div className="metric-header">
            <span className="metric-title">Road Surface Defects</span>
            <span className="metric-icon">🛠️</span>
          </div>
          <div className="metric-value-row">
            <div className="metric-value">{roadDefects.length}</div>
            <svg width="64" height="24" viewBox="0 0 64 24" fill="none">
              <path d="M2 20 L16 16 L28 18 L40 10 L52 14 L62 4" stroke="#F59E0B" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div className="metric-footer">
            <span>● Potholes & Lateral Cracks</span>
          </div>
        </Interactive3DCard>

        <Interactive3DCard className="metric-card" style={{ cursor: "pointer" }} onClick={() => onSelectTab("traffic")}>
          <div className="metric-header">
            <span className="metric-title">Traffic Density State</span>
            <span className="metric-icon">🚦</span>
          </div>
          <div className="metric-value-row">
            <div className="metric-value" style={{ textTransform: "uppercase", fontSize: "20px", color: congestion.toLowerCase() === "critical" ? "#EF4444" : "#10B981" }}>
              {congestion}
            </div>
            <svg width="64" height="24" viewBox="0 0 64 24" fill="none">
              <path d="M2 12 Q10 2 18 12 T34 12 T50 12 T62 12" stroke="#0EA5E9" strokeWidth="2" strokeLinecap="round" fill="none" />
            </svg>
          </div>
          <div className="metric-footer">
            <span>{vehicleCount} vehicles observed in corridor</span>
          </div>
        </Interactive3DCard>

        <Interactive3DCard className="metric-card" style={{ cursor: "pointer" }} onClick={() => onSelectTab("incidents")}>
          <div className="metric-header">
            <span className="metric-title">Incidents & Collisions</span>
            <span className="metric-icon">🚨</span>
          </div>
          <div className="metric-value-row">
            <div className="metric-value" style={{ color: incidentEvents.length > 0 ? "#EF4444" : "#111111" }}>
              {incidentEvents.length}
            </div>
            <svg width="64" height="24" viewBox="0 0 64 24" fill="none">
              <path d="M2 20 L18 16 L34 22 L50 8 L62 4" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div className="metric-footer">
            <span>{incidentEvents.filter((i) => i.payload?.assigned_team === "emergency_team").length} Emergency Dispatches</span>
          </div>
        </Interactive3DCard>

        <Interactive3DCard className="metric-card" style={{ cursor: "pointer" }} onClick={() => onSelectTab("anpr")}>
          <div className="metric-header">
            <span className="metric-title">Plates Recognized (CRNN)</span>
            <span className="metric-icon">🔍</span>
          </div>
          <div className="metric-value-row">
            <div className="metric-value" style={{ color: "#0EA5E9" }}>
              {incidentEvents.filter((i) => i.payload?.plate_number && i.payload?.plate_status === "recognized").length}
            </div>
            <svg width="64" height="24" viewBox="0 0 64 24" fill="none">
              <path d="M2 16 L16 10 L32 14 L48 6 L62 2" stroke="#6366F1" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div className="metric-footer">
            <span>High-precision CTC OCR</span>
          </div>
        </Interactive3DCard>

        <Interactive3DCard className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Priority Alerts</span>
            <span className="metric-icon">⚡</span>
          </div>
          <div className="metric-value-row">
            <div className="metric-value" style={{ color: criticalCount > 0 ? "#F59E0B" : "#111111" }}>
              {criticalCount}
            </div>
            <span className={`pulse-dot ${criticalCount > 0 ? "error" : "green"}`} style={{ width: "8px", height: "8px" }} />
          </div>
          <div className="metric-footer">
            <span>Active Response Threshold</span>
          </div>
        </Interactive3DCard>
      </div>

      {/* Main 2-Column Operational Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1.75fr 1fr", gap: "24px" }}>
        {/* Left: Live Activity Feed */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <h2>Live Activity & Event Stream</h2>
              <p>Real-time telemetry ingested from connected vehicle edge nodes</p>
            </div>
            <div className="panel-actions">
              <span className="badge badge-neutral">Total: {alerts.length}</span>
            </div>
          </div>

          <div style={{ overflowX: "auto" }}>
            {recentActivity.length === 0 ? (
              <div style={{ padding: "48px", textAlign: "center", color: "var(--muted)" }}>
                No events currently recorded. Awaiting edge telemetry synchronization...
              </div>
            ) : (
              <table className="event-table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Type / Description</th>
                    <th>Source Module</th>
                    <th>Location / GPS</th>
                    <th>Timestamp</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {recentActivity.map((alert) => {
                    const isTraffic = alert.module?.type === "traffic";
                    const isIncident = alert.module?.type === "incident_anpr";
                    const eventDesc = isTraffic
                      ? `Congestion: ${alert.payload?.congestion_level?.toUpperCase() || "MONITORING"}`
                      : isIncident
                        ? `Incident: ${alert.payload?.event_type?.toUpperCase() || "EVENT"}`
                        : `Defect: ${alert.payload?.defect_type?.toUpperCase() || "POTHOLE"}`;

                    return (
                      <tr key={alert.alert_id}>
                        <td>
                          <span className={`badge ${getSeverityBadgeClass(alert.severity)}`}>
                            {alert.severity}
                          </span>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, color: "var(--text-bright)" }}>{eventDesc}</div>
                          <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                            {alert.alert_id}
                          </div>
                        </td>
                        <td>
                          <span style={{ fontSize: "12px", color: "var(--muted)", fontWeight: 500 }}>
                            {isTraffic ? "Module 2 (Traffic)" : isIncident ? "Module 3 (Incident)" : "Module 1 (Defect)"}
                          </span>
                        </td>
                        <td>
                          <span className="meta-val gps-tag">{formatGPS(alert.gps)}</span>
                        </td>
                        <td style={{ fontSize: "12px", color: "var(--muted)" }}>
                          {formatTimestamp(alert.timestamp)}
                        </td>
                        <td>
                          <button
                            className="button button-dark button-sm"
                            onClick={() => onSelectAlert(alert)}
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right: Operational Status Panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Module Pipeline Health */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title-group">
                <h2>Neural Pipelines Status</h2>
                <p>Triple edge inference threads</p>
              </div>
            </div>
            <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div className="meta-row">
                <span className="meta-label">Module 1: Road Defect</span>
                <span className="badge badge-low">YOLOv8s Active</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Module 2: Traffic Flow</span>
                <span className="badge badge-low">ByteTrack Active</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Module 3: Incident & ANPR</span>
                <span className="badge badge-low">CRNN OCR Active</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">GPS Spatial Fix</span>
                <span className="badge badge-info">1.0 Hz Polling</span>
              </div>
            </div>
          </div>

          {/* Incident Triage Shortcut */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title-group">
                <h2>Operational Triage</h2>
                <p>Quick team dispatches</p>
              </div>
            </div>
            <div className="panel-body">
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <button
                  className="button button-dark"
                  style={{ justifyContent: "space-between", width: "100%", padding: "10px 16px" }}
                  onClick={() => onSelectTab("incidents")}
                >
                  <span>🚨 Emergency Collisions</span>
                  <span className="nav-badge danger">
                    {incidentEvents.filter((i) => i.payload?.assigned_team === "emergency_team").length}
                  </span>
                </button>
                <button
                  className="button button-dark"
                  style={{ justifyContent: "space-between", width: "100%", padding: "10px 16px" }}
                  onClick={() => onSelectTab("defects")}
                >
                  <span>🛠️ Critical Pothole Fixes</span>
                  <span className="nav-badge">
                    {roadDefects.filter((d) => d.severity === "high" || d.severity === "critical").length}
                  </span>
                </button>
                <button
                  className="button button-dark"
                  style={{ justifyContent: "space-between", width: "100%", padding: "10px 16px" }}
                  onClick={() => onSelectTab("map")}
                >
                  <span>🗺️ Open GIS Full Map</span>
                  <span className="nav-badge">{alerts.length}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
