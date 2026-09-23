import React, { useState } from "react";
import { formatTimestamp, formatGPS, formatConfidence, getEvidenceUrl, getSeverityBadgeClass } from "../utils/formatters";

export default function RoadDefectsPage({ alerts, onSelectAlert }) {
  const [severityFilter, setSeverityFilter] = useState("all");
  const roadDefects = alerts.filter((a) => a.module?.type === "road_defect");

  const filteredDefects = roadDefects.filter((d) => {
    if (severityFilter === "all") return true;
    return d.severity?.toLowerCase() === severityFilter.toLowerCase();
  });

  const highCount = roadDefects.filter((d) => d.severity === "high" || d.severity === "critical").length;
  const mediumCount = roadDefects.filter((d) => d.severity === "medium").length;
  const lowCount = roadDefects.filter((d) => d.severity === "low").length;

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Road Defect & Infrastructure Intelligence</h1>
          <p>Module 1 — AI-powered pothole and road crack detection with GPS-tagged photographic evidence.</p>
        </div>
        <div className="page-header-badges">
          <span className="badge badge-neutral">Total Defects: {roadDefects.length}</span>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Total Detected</span>
            <span className="metric-icon">🛠️</span>
          </div>
          <div className="metric-value">{roadDefects.length}</div>
          <div className="metric-footer"><span>Pothole tracks confirmed</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Critical / High Severity</span>
            <span className="metric-icon">⚠️</span>
          </div>
          <div className="metric-value" style={{ color: "#EF4444" }}>{highCount}</div>
          <div className="metric-footer"><span>Requires urgent repair</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Medium Severity</span>
            <span className="metric-icon">🟡</span>
          </div>
          <div className="metric-value" style={{ color: "#F59E0B" }}>{mediumCount}</div>
          <div className="metric-footer"><span>Scheduled maintenance</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Low Severity</span>
            <span className="metric-icon">🟢</span>
          </div>
          <div className="metric-value" style={{ color: "#10B981" }}>{lowCount}</div>
          <div className="metric-footer"><span>Surface monitoring</span></div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title-group">
            <h2>Pothole & Defect Registry</h2>
            <p>Full forensic record with cropped visual evidence and geolocations</p>
          </div>
          <div className="panel-actions">
            <div className="segmented-control">
              {["all", "high", "medium", "low"].map((sev) => (
                <button
                  key={sev}
                  className={`segment-btn ${severityFilter === sev ? "active" : ""}`}
                  onClick={() => setSeverityFilter(sev)}
                >
                  {sev.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        {filteredDefects.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "var(--muted)" }}>
            No road defect records matching the selected severity filter.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="event-table">
              <thead>
                <tr>
                  <th>Evidence</th>
                  <th>Alert ID / Track</th>
                  <th>Defect Type</th>
                  <th>Severity</th>
                  <th>AI Confidence</th>
                  <th>GPS Coordinates</th>
                  <th>Detected At</th>
                  <th>Inspect</th>
                </tr>
              </thead>
              <tbody>
                {[...filteredDefects].reverse().map((alert) => {
                  const p = alert.payload || {};
                  const evidenceUrl = getEvidenceUrl(alert);

                  return (
                    <tr key={alert.alert_id}>
                      <td>
                        {evidenceUrl ? (
                          <img
                            src={evidenceUrl}
                            alt="Evidence"
                            className="evidence-thumb"
                            onClick={() => onSelectAlert(alert)}
                            onError={(e) => {
                              e.currentTarget.style.display = "none";
                            }}
                          />
                        ) : (
                          <div
                            style={{
                              width: "48px",
                              height: "48px",
                              borderRadius: "var(--radius-md)",
                              background: "var(--section-bg)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "18px",
                              border: "1px solid var(--line)",
                            }}
                          >
                            📷
                          </div>
                        )}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: "var(--text-bright)" }}>
                          {alert.alert_id}
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                          Track: {p.track_id ? `#${p.track_id}` : "N/A"}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, textTransform: "capitalize" }}>
                          {p.defect_type || "Pothole"}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${getSeverityBadgeClass(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                          {formatConfidence(p.confidence)}
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
                          Forensics
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
