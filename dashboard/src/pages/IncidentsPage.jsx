import React, { useState } from "react";
import { formatTimestamp, formatGPS, getEvidenceUrl, getSeverityBadgeClass } from "../utils/formatters";
import { API_BASE_URL } from "../utils/formatters";

export default function IncidentsPage({ alerts, onSelectAlert, onRefresh }) {
  const [activeTab, setActiveTab] = useState("all");
  const incidentAlerts = alerts.filter((a) => a.module?.type === "incident_anpr");

  const emergencyEvents = incidentAlerts.filter(
    (i) => i.payload?.assigned_team === "emergency_team" || i.severity === "critical"
  );
  const rashEvents = incidentAlerts.filter(
    (i) => i.payload?.assigned_team === "rash_driving_team" && i.severity !== "critical"
  );

  const displayedIncidents = activeTab === "emergency"
    ? emergencyEvents
    : activeTab === "rash_driving"
      ? rashEvents
      : incidentAlerts;

  const handleStatusChange = async (eventId, newStatus) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/incidents/${eventId}/status?status=${newStatus}`, {
        method: "PATCH",
      });
      if (resp.ok && onRefresh) {
        onRefresh();
      }
    } catch (err) {
      console.error("Failed to update incident status:", err);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Incident Command & Enforcement Center</h1>
          <p>Module 3 — Dangerous behavior analysis, collision monitoring, and emergency response dispatch workflow.</p>
        </div>
        <div className="page-header-badges">
          <span className="badge badge-critical">{emergencyEvents.length} Emergency Dispatches</span>
          <span className="badge badge-high">{rashEvents.length} Behavioral Cases</span>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Total Incidents</span>
            <span className="metric-icon">🚨</span>
          </div>
          <div className="metric-value">{incidentAlerts.length}</div>
          <div className="metric-footer"><span>Confirmed incident events</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Accidents & Collisions</span>
            <span className="metric-icon">🚑</span>
          </div>
          <div className="metric-value" style={{ color: "#EF4444" }}>{emergencyEvents.length}</div>
          <div className="metric-footer"><span>Immediate dispatch required</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Rash Driving & Speeding</span>
            <span className="metric-icon">🏎️</span>
          </div>
          <div className="metric-value" style={{ color: "#F59E0B" }}>{rashEvents.length}</div>
          <div className="metric-footer"><span>Traffic enforcement notice</span></div>
        </div>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Resolved / Dispatched</span>
            <span className="metric-icon">✅</span>
          </div>
          <div className="metric-value" style={{ color: "#10B981" }}>
            {incidentAlerts.filter((i) => i.payload?.status === "dispatched" || i.payload?.status === "resolved").length}
          </div>
          <div className="metric-footer"><span>Actioned by operational teams</span></div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title-group">
            <h2>Incident Case Management</h2>
            <p>Select case status to update operational workflow in real-time</p>
          </div>
          <div className="panel-actions">
            <div className="segmented-control">
              <button
                className={`segment-btn ${activeTab === "all" ? "active" : ""}`}
                onClick={() => setActiveTab("all")}
              >
                All ({incidentAlerts.length})
              </button>
              <button
                className={`segment-btn segment-red ${activeTab === "emergency" ? "active" : ""}`}
                onClick={() => setActiveTab("emergency")}
              >
                🚨 Emergency ({emergencyEvents.length})
              </button>
              <button
                className={`segment-btn segment-yellow ${activeTab === "rash_driving" ? "active" : ""}`}
                onClick={() => setActiveTab("rash_driving")}
              >
                ⚡ Enforcement ({rashEvents.length})
              </button>
            </div>
          </div>
        </div>

        {displayedIncidents.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "var(--muted)" }}>
            No incident events recorded in this category.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="event-table">
              <thead>
                <tr>
                  <th>Evidence</th>
                  <th>Incident ID / Type</th>
                  <th>Assigned Team</th>
                  <th>Recognized Plate</th>
                  <th>Severity</th>
                  <th>Current Status</th>
                  <th>GPS Fix</th>
                  <th>Workflow Action</th>
                </tr>
              </thead>
              <tbody>
                {[...displayedIncidents].reverse().map((alert) => {
                  const p = alert.payload || {};
                  const evidenceUrl = getEvidenceUrl(alert);
                  const isEmergency = p.assigned_team === "emergency_team" || alert.severity === "critical";
                  const currentStatus = p.status || "reported";

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
                          {p.event_type?.toUpperCase() || "VEHICLE INCIDENT"}
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                          {alert.alert_id}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${isEmergency ? "badge-critical" : "badge-medium"}`}>
                          {isEmergency ? "🚨 Emergency Team" : "⚡ Enforcement Bureau"}
                        </span>
                      </td>
                      <td>
                        {p.plate_number ? (
                          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, background: "var(--section-bg)", padding: "3px 8px", borderRadius: "var(--radius-xs)", border: "1px solid var(--line)" }}>
                            {p.plate_number}
                          </span>
                        ) : (
                          <span style={{ color: "var(--muted)", fontSize: "12px" }}>Unresolved</span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${getSeverityBadgeClass(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </td>
                      <td>
                        <select
                          value={currentStatus}
                          onChange={(e) => handleStatusChange(alert.alert_id, e.target.value)}
                          style={{
                            padding: "4px 8px",
                            borderRadius: "var(--radius-full)",
                            background: "var(--panel-bg)",
                            border: "1px solid var(--line)",
                            fontSize: "12px",
                            fontWeight: 600,
                            color: "var(--text-bright)",
                            cursor: "pointer",
                          }}
                        >
                          <option value="reported">Reported</option>
                          <option value="dispatched">Dispatched</option>
                          <option value="investigating">Investigating</option>
                          <option value="resolved">Resolved</option>
                        </select>
                      </td>
                      <td>
                        <span className="meta-val gps-tag">{formatGPS(alert.gps)}</span>
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
