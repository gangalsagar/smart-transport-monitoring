import React from "react";
import { formatTimestamp, API_BASE_URL } from "../utils/formatters";

export default function SystemHealthPage({ alerts, lastUpdated, backendConnected, onRefresh }) {
  const roadDefects = alerts.filter((a) => a.module?.type === "road_defect");
  const trafficEvents = alerts.filter((a) => a.module?.type === "traffic");
  const incidentEvents = alerts.filter((a) => a.module?.type === "incident_anpr");

  return (
    <div className="page-container">
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Edge Infrastructure & System Diagnostics</h1>
          <p>Real-time telemetry, thread availability, offline queue state, and central backend storage diagnostics.</p>
        </div>
        <div className="page-header-badges">
          <span className={`badge ${backendConnected ? "badge-low" : "badge-critical"}`}>
            <span className={`pulse-dot ${backendConnected ? "green" : "error"}`} style={{ width: "5px", height: "5px" }} />
            {backendConnected ? "SYSTEM OPERATIONAL" : "BACKEND DISCONNECTED"}
          </span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "24px", marginBottom: "24px" }}>
        {/* Edge AI Device */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <h2>Edge AI Device (BUS-TEST)</h2>
              <p>Onboard physical compute node</p>
            </div>
            <span className="badge badge-low">ONLINE</span>
          </div>
          <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div className="meta-row">
              <span className="meta-label">Device Identifier</span>
              <span className="meta-val" style={{ fontFamily: "var(--font-mono)" }}>EDGE-01</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Assigned Vehicle</span>
              <span className="meta-val">BUS-TEST (Front Mount)</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Architecture</span>
              <span className="meta-val">ARM64 / x86_64 Compatible</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Camera Capture</span>
              <span className="meta-val" style={{ color: "#10B981", fontWeight: 600 }}>1080p @ 25 FPS (Active)</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">GPS Telemetry Service</span>
              <span className="meta-val" style={{ color: "#10B981", fontWeight: 600 }}>1.0 Hz Polling (Locked)</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Offline SQLite Queue</span>
              <span className="meta-val" style={{ fontFamily: "var(--font-mono)" }}>alerts.db (WAL Mode)</span>
            </div>
          </div>
        </div>

        {/* Central Server & Storage */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <h2>Central Server (FastAPI)</h2>
              <p>Backend API & Storage Hub</p>
            </div>
            <span className={`badge ${backendConnected ? "badge-info" : "badge-critical"}`}>
              {backendConnected ? "CONNECTED" : "OFFLINE"}
            </span>
          </div>
          <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div className="meta-row">
              <span className="meta-label">REST Endpoint</span>
              <span className="meta-val" style={{ fontFamily: "var(--font-mono)" }}>{API_BASE_URL}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Synchronized Alerts</span>
              <span className="meta-val" style={{ fontWeight: 700 }}>{alerts.length}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Alert JSONL Storage</span>
              <span className="meta-val" style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>backend/data/alerts/</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Traffic Density Store</span>
              <span className="meta-val" style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>traffic_density.jsonl</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Evidence Media Vault</span>
              <span className="meta-val" style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>backend/data/evidence/</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Last Polled</span>
              <span className="meta-val">{formatTimestamp(lastUpdated)}</span>
            </div>
          </div>
        </div>

        {/* Edge AI Modules */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <h2>AI Inference Engines</h2>
              <p>Triple neural threads</p>
            </div>
            <span className="badge badge-low">HEALTHY</span>
          </div>
          <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div className="meta-row">
              <span className="meta-label">Module 1 (Road Defect)</span>
              <span className="meta-val">YOLOv8s · RDD2022</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Module 2 (Traffic Flow)</span>
              <span className="meta-val">YOLOv8s + ByteTrack</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Module 3 (Incident & ANPR)</span>
              <span className="meta-val">CRNN CTC OCR</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Total Defects Ingested</span>
              <span className="meta-val" style={{ fontWeight: 600 }}>{roadDefects.length}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Total Traffic Snapshots</span>
              <span className="meta-val" style={{ fontWeight: 600 }}>{trafficEvents.length}</span>
            </div>
            <div className="meta-row">
              <span className="meta-label">Total Incidents Recorded</span>
              <span className="meta-val" style={{ fontWeight: 600 }}>{incidentEvents.length}</span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button className="button button-primary" onClick={onRefresh}>
          <span>↻ Force Synchronize Telemetry</span>
        </button>
      </div>
    </div>
  );
}
