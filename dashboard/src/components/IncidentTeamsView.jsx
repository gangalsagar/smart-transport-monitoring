import React, { useState } from "react";

const API_URL = "http://127.0.0.1:8001";

function IncidentTeamsView({ incidents, onStatusUpdated }) {
  const [activeTeamTab, setActiveTeamTab] = useState("emergency"); // "emergency" | "rash_driving"

  const emergencyEvents = incidents.filter(
    (inc) => inc.payload?.assigned_team === "emergency_team" || inc.severity === "critical"
  );

  const rashDrivingCases = incidents.filter(
    (inc) => inc.payload?.assigned_team === "rash_driving_team" && inc.severity !== "critical"
  );

  const handleStatusChange = async (eventId, newStatus) => {
    try {
      const resp = await fetch(`${API_URL}/incidents/${eventId}/status?status=${newStatus}`, {
        method: "PATCH",
      });
      if (resp.ok && onStatusUpdated) {
        onStatusUpdated();
      }
    } catch (err) {
      console.error("Failed to update incident status:", err);
    }
  };

  const getEvidenceSrc = (inc) => {
    const rawPath = inc.evidence?.image_path || inc.payload?.evidence_image_path;
    if (!rawPath) return null;
    const normalized = rawPath.replaceAll("\\", "/");
    const filename = normalized.split("/").pop();
    return `${API_URL}/evidence/${encodeURIComponent(filename)}`;
  };

  return (
    <section className="panel" style={{ marginTop: "20px" }}>
      <div className="panel-header" style={{ flexWrap: "wrap", gap: "14px" }}>
        <div>
          <h2>Incident & Operational Dispatch Hub</h2>
          <p>
            {activeTeamTab === "emergency"
              ? "Emergency Response Team · Live accident detection, collision impact triage & paramedic routing"
              : "Traffic Enforcement Bureau · Reckless driving telemetry, automated challan dispatch & ANPR linking"}
          </p>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className={`button ${activeTeamTab === "emergency" ? "button-emergency-active" : "button-dark"}`}
            onClick={() => setActiveTeamTab("emergency")}
          >
            <span>🚨 Emergency Dispatch</span>
            <span className="nav-badge" style={{ background: activeTeamTab === "emergency" ? "#EF4444" : "rgba(239,68,68,0.2)", color: "#FFF" }}>
              {emergencyEvents.length}
            </span>
          </button>
          <button
            type="button"
            className={`button ${activeTeamTab === "rash_driving" ? "button-rash-active" : "button-dark"}`}
            onClick={() => setActiveTeamTab("rash_driving")}
          >
            <span>⚡ Enforcement Bureau</span>
            <span className="nav-badge" style={{ background: activeTeamTab === "rash_driving" ? "#F59E0B" : "rgba(245,158,11,0.2)", color: "#FFF" }}>
              {rashDrivingCases.length}
            </span>
          </button>
        </div>
      </div>

      <div style={{ padding: "16px 20px" }}>
        {activeTeamTab === "emergency" ? (
          <div>
            {emergencyEvents.length === 0 ? (
              <div className="empty-state">
                <span className="empty-state-icon">🛡️</span>
                <span className="empty-state-title">No Active Critical Emergencies</span>
                <span className="empty-state-desc">All monitored sectors reporting clear roadways and zero catastrophic impacts.</span>
              </div>
            ) : (
              <div className="incident-grid">
                {[...emergencyEvents].reverse().map((event) => {
                  const p = event.payload || {};
                  const evidenceUrl = getEvidenceSrc(event);
                  const currentStatus = p.status || "new";

                  return (
                    <article key={event.alert_id} className="incident-card emergency-card">
                      <div className="incident-card-top">
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span className="badge badge-critical">🚨 CRITICAL</span>
                          <span className="incident-code">#{event.alert_id.slice(-8)}</span>
                        </div>
                        <span className={`status-pill status-${currentStatus}`}>
                          {currentStatus.replace("_", " ").toUpperCase()}
                        </span>
                      </div>

                      <div style={{ marginTop: "10px" }}>
                        <div className="incident-headline">{p.event_type?.replace(/_/g, " ").toUpperCase() || "VEHICLE COLLISION"}</div>
                        <div className="incident-subline">Detected via Edge Inference Pipeline</div>
                      </div>

                      <div className="incident-metrics-grid">
                        <div className="metric-box">
                          <span className="metric-lbl">CONFIDENCE</span>
                          <span className="metric-val text-green">{Math.round((p.model_confidence || 0.75) * 100)}%</span>
                        </div>
                        <div className="metric-box">
                          <span className="metric-lbl">PLATE MATCH</span>
                          <span className="metric-val">{p.plate_number || "OBSCURED"}</span>
                        </div>
                        <div className="metric-box">
                          <span className="metric-lbl">TRACK ID</span>
                          <span className="metric-val">#{p.vehicle_track_id ?? "N/A"}</span>
                        </div>
                        <div className="metric-box">
                          <span className="metric-lbl">TIMESTAMP</span>
                          <span className="metric-val">{new Date(event.timestamp).toLocaleTimeString()}</span>
                        </div>
                      </div>

                      <div className="incident-location-bar">
                        <span>📍 GPS: {event.gps?.latitude?.toFixed(4)}, {event.gps?.longitude?.toFixed(4)}</span>
                        <span className="gps-source-tag">{p.gps_source || "Active GPS"}</span>
                      </div>

                      <div className="incident-action-row">
                        <label>Dispatch Action:</label>
                        <select
                          className="status-select"
                          value={currentStatus}
                          onChange={(e) => handleStatusChange(event.alert_id, e.target.value)}
                        >
                          <option value="new">Pending Review</option>
                          <option value="acknowledged">Acknowledged by Dispatch</option>
                          <option value="dispatched">Ambulance / Units En Route</option>
                          <option value="resolved">Incident Cleared / Resolved</option>
                          <option value="closed">Case Closed</option>
                        </select>
                      </div>

                      {evidenceUrl && (
                        <div className="incident-evidence-wrap">
                          <img
                            src={evidenceUrl}
                            alt="Emergency Evidence"
                            onError={(e) => { e.currentTarget.style.display = "none"; }}
                          />
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <div>
            {rashDrivingCases.length === 0 ? (
              <div className="empty-state">
                <span className="empty-state-icon">🏎️</span>
                <span className="empty-state-title">No Dangerous Driving Events</span>
                <span className="empty-state-desc">Traffic behavior models confirm normal driving patterns across active camera sectors.</span>
              </div>
            ) : (
              <div className="incident-grid">
                {[...rashDrivingCases].reverse().map((event) => {
                  const p = event.payload || {};
                  const evidenceUrl = getEvidenceSrc(event);
                  const currentStatus = p.status || "new";

                  return (
                    <article key={event.alert_id} className="incident-card rash-card">
                      <div className="incident-card-top">
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span className="badge badge-high">🏎️ VIOLATION</span>
                          <span className="incident-code">#{event.alert_id.slice(-8)}</span>
                        </div>
                        <span className={`status-pill status-${currentStatus}`}>
                          {currentStatus.replace("_", " ").toUpperCase()}
                        </span>
                      </div>

                      <div style={{ marginTop: "10px" }}>
                        <div className="incident-headline">{p.event_type?.replace(/_/g, " ").toUpperCase() || "RECKLESS MANEUVER"}</div>
                        <div className="incident-subline">Aggressive lane deviation / excessive speed trajectory</div>
                      </div>

                      <div className="incident-metrics-grid">
                        <div className="metric-box">
                          <span className="metric-lbl">TARGET PLATE</span>
                          <span className="metric-val text-yellow" style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                            {p.plate_number || "IDENTIFYING"}
                          </span>
                        </div>
                        <div className="metric-box">
                          <span className="metric-lbl">OCR STATUS</span>
                          <span className="metric-val">{p.plate_status ? p.plate_status.toUpperCase() : "RESOLVED"}</span>
                        </div>
                        <div className="metric-box">
                          <span className="metric-lbl">TRACK ID</span>
                          <span className="metric-val">#{p.vehicle_track_id ?? "N/A"}</span>
                        </div>
                        <div className="metric-box">
                          <span className="metric-lbl">TIME</span>
                          <span className="metric-val">{new Date(event.timestamp).toLocaleTimeString()}</span>
                        </div>
                      </div>

                      <div className="incident-location-bar">
                        <span>📍 GPS: {event.gps?.latitude?.toFixed(4)}, {event.gps?.longitude?.toFixed(4)}</span>
                        <span className="gps-source-tag">Surveillance Stream</span>
                      </div>

                      <div className="incident-action-row">
                        <label>Enforcement Action:</label>
                        <select
                          className="status-select"
                          value={currentStatus}
                          onChange={(e) => handleStatusChange(event.alert_id, e.target.value)}
                        >
                          <option value="new">Pending Review</option>
                          <option value="in_progress">Video Audit In Progress</option>
                          <option value="dispatched">Digital Challan Issued</option>
                          <option value="resolved">Fine Processed / Resolved</option>
                          <option value="closed">Record Archived</option>
                        </select>
                      </div>

                      {evidenceUrl && (
                        <div className="incident-evidence-wrap">
                          <img
                            src={evidenceUrl}
                            alt="Vehicle Violation Evidence"
                            onError={(e) => { e.currentTarget.style.display = "none"; }}
                          />
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default IncidentTeamsView;
