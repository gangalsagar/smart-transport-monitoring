import React from "react";
import { formatTimestamp, formatGPS, formatConfidence, getEvidenceUrl, getSeverityBadgeClass } from "../utils/formatters";

export default function VehiclesANPRPage({ alerts, onSelectAlert }) {
  const incidentAlerts = alerts.filter((a) => a.module?.type === "incident_anpr");
  const recognizedPlates = incidentAlerts.filter((a) => a.payload?.plate_number && a.payload?.plate_status === "recognized");

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Vehicle Intelligence & ANPR Registry</h1>
          <p>Automated Number Plate Recognition (CRNN OCR) and vehicle telemetry linking incident history with identity.</p>
        </div>
        <div className="page-header-badges">
          <span className="badge badge-info">CRNN Plate Recognizer Active</span>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Plates Recognized</span>
            <span className="metric-icon">🚘</span>
          </div>
          <div className="metric-value" style={{ color: "#10B981" }}>{recognizedPlates.length}</div>
          <div className="metric-footer"><span>Alphanumeric strings resolved</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Plate Candidates Scanned</span>
            <span className="metric-icon">🔍</span>
          </div>
          <div className="metric-value">{incidentAlerts.length}</div>
          <div className="metric-footer"><span>Cropped vehicle plate patches</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Average OCR Confidence</span>
            <span className="metric-icon">📈</span>
          </div>
          <div className="metric-value">
            {recognizedPlates.length > 0
              ? `${Math.round(
                  (recognizedPlates.reduce((acc, curr) => acc + (curr.payload?.plate_confidence || 0.8), 0) /
                    recognizedPlates.length) *
                    100
                )}%`
              : "N/A"}
          </div>
          <div className="metric-footer"><span>High-precision threshold</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Unresolved / Obscured</span>
            <span className="metric-icon">⚠️</span>
          </div>
          <div className="metric-value" style={{ color: "#F59E0B" }}>
            {incidentAlerts.filter((a) => a.payload?.plate_status !== "recognized").length}
          </div>
          <div className="metric-footer"><span>Motion blur or low illumination</span></div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title-group">
            <h2>Recognized Vehicle Plate Records</h2>
            <p>Direct linking between recognized license plates, cropped visual patches, and violation events</p>
          </div>
        </div>

        {incidentAlerts.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "var(--muted)" }}>
            No vehicle plate records detected yet.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="event-table">
              <thead>
                <tr>
                  <th>Vehicle Patch</th>
                  <th>License Plate</th>
                  <th>OCR Status</th>
                  <th>OCR Confidence</th>
                  <th>Associated Incident</th>
                  <th>Track ID</th>
                  <th>GPS Coordinates</th>
                  <th>Timestamp</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {[...incidentAlerts].reverse().map((alert) => {
                  const p = alert.payload || {};
                  const evidenceUrl = getEvidenceUrl(alert);
                  const isRecognized = p.plate_status === "recognized";

                  return (
                    <tr key={alert.alert_id}>
                      <td>
                        {evidenceUrl ? (
                          <img
                            src={evidenceUrl}
                            alt="Vehicle Patch"
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
                            🚘
                          </div>
                        )}
                      </td>
                      <td>
                        {p.plate_number ? (
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "13px",
                              fontWeight: 700,
                              background: "var(--section-bg)",
                              padding: "4px 10px",
                              borderRadius: "var(--radius-sm)",
                              border: "1px solid var(--line)",
                              color: "var(--text-bright)",
                            }}
                          >
                            {p.plate_number}
                          </span>
                        ) : (
                          <span style={{ color: "var(--muted)", fontSize: "12px" }}>UNRESOLVED</span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${isRecognized ? "badge-low" : "badge-medium"}`}>
                          {p.plate_status?.toUpperCase() || "SCANNED"}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                          {p.plate_confidence ? `${Math.round(p.plate_confidence * 100)}%` : "N/A"}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: "var(--text-bright)" }}>
                          {p.event_type?.toUpperCase() || "INCIDENT"}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontFamily: "var(--font-mono)", color: "var(--muted)", fontSize: "12px" }}>
                          {p.track_id ? `#${p.track_id}` : "N/A"}
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
