import React from "react";
import { getEvidenceUrl, formatGPS, formatTimestamp, formatConfidence, getSeverityBadgeClass } from "../utils/formatters";

export default function EvidenceModal({ item, onClose }) {
  if (!item) return null;

  const evidenceUrl = getEvidenceUrl(item);
  const p = item.payload || {};
  const isTraffic = item.module?.type === "traffic";
  const isIncident = item.module?.type === "incident_anpr";
  const isDefect = item.module?.type === "road_defect";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span className={`badge ${getSeverityBadgeClass(item.severity)}`}>
              {item.severity}
            </span>
            <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-bright)", letterSpacing: "-0.01em" }}>
              {item.alert_id}
            </span>
            <span style={{ fontSize: "11px", color: "var(--muted)", padding: "3px 8px", background: "var(--section-bg)", borderRadius: "var(--radius-full)", border: "1px solid var(--line)" }}>
              {isTraffic ? "TRAFFIC SENSING" : isIncident ? "CRITICAL INCIDENT" : "ROAD SURFACE DEFECT"}
            </span>
          </div>
          <button
            onClick={onClose}
            className="modal-close-btn"
            title="Close forensic viewer"
          >
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="modal-preview">
            {evidenceUrl ? (
              <div className="evidence-frame">
                <img
                  src={evidenceUrl}
                  alt={`Evidence ${item.alert_id}`}
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
                <div className="evidence-watermark">
                  <span>FORENSIC FRAME · {item.source?.device_id || "EDGE-01"}</span>
                  <span>{formatTimestamp(item.timestamp)}</span>
                </div>
              </div>
            ) : (
              <div className="evidence-placeholder">
                <span style={{ fontSize: "32px", opacity: 0.6 }}>📷</span>
                <span>No photographic evidence captured for this event</span>
              </div>
            )}
          </div>

          <div className="modal-sidebar">
            <div className="sidebar-section-title">
              <span>Forensic Telemetry Record</span>
            </div>

            <div className="meta-row">
              <span className="meta-label">Module Pipeline</span>
              <span className="meta-val" style={{ fontWeight: 600 }}>
                {isTraffic ? "Module 2: Traffic Flow" : isIncident ? "Module 3: Incident & ANPR" : "Module 1: Road Defect"}
              </span>
            </div>

            <div className="meta-row">
              <span className="meta-label">Recorded Time</span>
              <span className="meta-val">{formatTimestamp(item.timestamp)}</span>
            </div>

            <div className="meta-row">
              <span className="meta-label">Geospatial Fix</span>
              <span className="meta-val gps-tag">{formatGPS(item.gps)}</span>
            </div>

            <div className="meta-row">
              <span className="meta-label">Fleet Unit Node</span>
              <span className="meta-val" style={{ fontFamily: "var(--font-mono)" }}>
                {item.bus_id || item.source?.device_id || "EDGE-01"}
              </span>
            </div>

            {isIncident && (
              <>
                <div className="sidebar-section-title" style={{ marginTop: "16px" }}>
                  <span>Incident Classification</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Event Category</span>
                  <span className="meta-val" style={{ textTransform: "uppercase", color: "#EF4444", fontWeight: 700 }}>
                    {p.event_type || "N/A"}
                  </span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Resolved Plate</span>
                  <span className="meta-val" style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                    {p.plate_number || "Unresolved"}
                  </span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">OCR Confidence</span>
                  <span className="meta-val">{formatConfidence(p.plate_confidence)}</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Assigned Dispatch</span>
                  <span className="meta-val">{p.assigned_team || "Emergency Team"}</span>
                </div>
              </>
            )}

            {isDefect && (
              <>
                <div className="sidebar-section-title" style={{ marginTop: "16px" }}>
                  <span>Surface Defect Analytics</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Defect Classification</span>
                  <span className="meta-val" style={{ textTransform: "capitalize", fontWeight: 600 }}>
                    {p.defect_type || "Pothole"}
                  </span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Detection Confidence</span>
                  <span className="meta-val" style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                    {formatConfidence(p.confidence)}
                  </span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Track Continuity ID</span>
                  <span className="meta-val" style={{ fontFamily: "var(--font-mono)" }}>
                    {p.track_id ? `#${p.track_id}` : "N/A"}
                  </span>
                </div>
              </>
            )}

            {isTraffic && (
              <>
                <div className="sidebar-section-title" style={{ marginTop: "16px" }}>
                  <span>Traffic Corridor Metrics</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Vehicles In Corridor</span>
                  <span className="meta-val">{p.vehicle_count ?? p.total_vehicle_count ?? 0}</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Roadway Congestion</span>
                  <span className="meta-val" style={{ textTransform: "uppercase", fontWeight: 600 }}>
                    {p.congestion_level || "Normal"}
                  </span>
                </div>
              </>
            )}

            <div style={{ marginTop: "24px" }}>
              <button
                className="button button-dark"
                style={{ width: "100%" }}
                onClick={onClose}
              >
                Close Forensic Record
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
