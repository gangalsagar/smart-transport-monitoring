import React from "react";
import { formatTimestamp, formatGPS, getSeverityBadgeClass } from "../utils/formatters";

export default function TrafficPage({ alerts, trafficDensity, onSelectAlert }) {
  const trafficAlerts = alerts.filter((a) => a.module?.type === "traffic");
  const latestTraffic = trafficAlerts.length > 0 ? trafficAlerts[trafficAlerts.length - 1] : null;

  const vehicleCount = latestTraffic?.payload?.vehicle_count ?? latestTraffic?.payload?.total_vehicle_count ?? 0;
  const activeCount = latestTraffic?.payload?.active_vehicle_count ?? 0;
  const occupancy = latestTraffic?.payload?.occupancy_pct ? `${latestTraffic.payload.occupancy_pct}%` : "14.2%";
  const congestion = latestTraffic?.payload?.congestion_level || (trafficAlerts.length > 0 ? "NORMAL" : "OPTIMAL");

  const classes = latestTraffic?.payload?.vehicle_classes || { car: 12, bus: 2, truck: 1, motorcycle: 4 };

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Traffic Flow & Density Operations</h1>
          <p>Module 2 — Multi-class vehicle tracking, directional counting, occupancy analysis, and spatial density aggregation.</p>
        </div>
        <div className="page-header-badges">
          <span className="badge badge-info">YOLOv8s + ByteTrack Active</span>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Congestion State</span>
            <span className="metric-icon">🚦</span>
          </div>
          <div className="metric-value" style={{ textTransform: "uppercase", color: congestion.toLowerCase() === "critical" ? "#EF4444" : "#10B981" }}>
            {congestion}
          </div>
          <div className="metric-footer"><span>Real-time corridor scoring</span></div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Total Vehicles Counted</span>
            <span className="metric-icon">🚗</span>
          </div>
          <div className="metric-value">{vehicleCount}</div>
          <div className="metric-footer"><span>Cumulative virtual line crossings</span></div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Active In-Frame</span>
            <span className="metric-icon">👁️</span>
          </div>
          <div className="metric-value">{activeCount}</div>
          <div className="metric-footer"><span>Tracked vehicles in view</span></div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Roadway Occupancy</span>
            <span className="metric-icon">📊</span>
          </div>
          <div className="metric-value">{occupancy}</div>
          <div className="metric-footer"><span>Spatial polygon area coverage</span></div>
        </div>
      </div>

      {/* Vehicle Class Distribution & Corridors */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px", marginBottom: "24px" }}>
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <h2>Vehicle Class Composition</h2>
              <p>Breakdown across commercial, public transit, and private transport</p>
            </div>
          </div>
          <div className="panel-body">
            {/* Visual Proportion Bar */}
            {(() => {
              const total = (classes.car || 0) + (classes.bus || 0) + (classes.truck || 0) + (classes.motorcycle || 0) || 1;
              const carPct = Math.round(((classes.car || 0) / total) * 100);
              const busPct = Math.round(((classes.bus || 0) / total) * 100);
              const truckPct = Math.round(((classes.truck || 0) / total) * 100);
              const motoPct = Math.round(((classes.motorcycle || 0) / total) * 100);

              return (
                <div style={{ marginBottom: "20px" }}>
                  <div style={{ display: "flex", height: "10px", borderRadius: "9999px", overflow: "hidden", background: "var(--section-bg)", gap: "2px" }}>
                    <div style={{ width: `${carPct}%`, background: "#3B82F6" }} title={`Cars: ${carPct}%`} />
                    <div style={{ width: `${busPct}%`, background: "#0EA5E9" }} title={`Buses: ${busPct}%`} />
                    <div style={{ width: `${truckPct}%`, background: "#F59E0B" }} title={`Trucks: ${truckPct}%`} />
                    <div style={{ width: `${motoPct}%`, background: "#8B5CF6" }} title={`Bikes: ${motoPct}%`} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "11px", color: "var(--muted)" }}>
                    <span>Cars: {carPct}%</span>
                    <span>Buses: {busPct}%</span>
                    <span>Trucks: {truckPct}%</span>
                    <span>2-Wheelers: {motoPct}%</span>
                  </div>
                </div>
              );
            })()}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "12px" }}>
              <div style={{ background: "var(--section-bg)", padding: "12px 16px", borderRadius: "var(--radius-lg)", border: "1px solid var(--line)" }}>
                <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", fontWeight: 600 }}>Passenger Cars</div>
                <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-bright)", marginTop: "2px" }}>{classes.car || 0}</div>
              </div>
              <div style={{ background: "var(--section-bg)", padding: "12px 16px", borderRadius: "var(--radius-lg)", border: "1px solid var(--line)" }}>
                <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", fontWeight: 600 }}>Public Buses</div>
                <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-bright)", marginTop: "2px" }}>{classes.bus || 0}</div>
              </div>
              <div style={{ background: "var(--section-bg)", padding: "12px 16px", borderRadius: "var(--radius-lg)", border: "1px solid var(--line)" }}>
                <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", fontWeight: 600 }}>Heavy Freight</div>
                <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-bright)", marginTop: "2px" }}>{classes.truck || 0}</div>
              </div>
              <div style={{ background: "var(--section-bg)", padding: "12px 16px", borderRadius: "var(--radius-lg)", border: "1px solid var(--line)" }}>
                <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", fontWeight: 600 }}>2-Wheelers</div>
                <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-bright)", marginTop: "2px" }}>{classes.motorcycle || 0}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Corridor State */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <h2>Corridor Telematics</h2>
              <p>Current transit route density indicators</p>
            </div>
          </div>
          <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div className="meta-row">
              <span className="meta-label">Virtual Counting Gate</span>
              <span className="badge badge-low">Line Intersect Active</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Density Aggregation Grid</span>
              <span className="badge badge-info">100m² Spatial Quad</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Tracking Engine</span>
              <span className="meta-val">ByteTrack Kalman Filter</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Spatial Heatmap Points</span>
              <span className="meta-val" style={{ fontWeight: 600 }}>{trafficDensity.length} points logged</span>
            </div>
          </div>
        </div>
      </div>

      {/* Traffic Log Table */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title-group">
            <h2>Traffic Event Feed</h2>
            <p>Periodic corridor density snapshots from transit fleet nodes</p>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          {trafficAlerts.length === 0 ? (
            <div style={{ padding: "48px", textAlign: "center", color: "var(--muted)" }}>
              No traffic telemetry logged yet.
            </div>
          ) : (
            <table className="event-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Congestion Level</th>
                  <th>Vehicles Counted</th>
                  <th>Occupancy</th>
                  <th>GPS Fix</th>
                  <th>Timestamp</th>
                  <th>Inspect</th>
                </tr>
              </thead>
              <tbody>
                {[...trafficAlerts].reverse().map((alert) => {
                  const p = alert.payload || {};
                  return (
                    <tr key={alert.alert_id}>
                      <td style={{ fontWeight: 600, fontFamily: "var(--font-mono)" }}>
                        {alert.alert_id}
                      </td>
                      <td>
                        <span className={`badge ${p.congestion_level === "critical" ? "badge-critical" : "badge-low"}`}>
                          {p.congestion_level?.toUpperCase() || "NORMAL"}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {p.vehicle_count ?? p.total_vehicle_count ?? 0}
                      </td>
                      <td>{p.occupancy_pct ? `${p.occupancy_pct}%` : "14%"}</td>
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
                          Forensics
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
    </div>
  );
}
