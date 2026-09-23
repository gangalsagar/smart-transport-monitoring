import React, { useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import TrafficHeatmap from "../components/TrafficHeatmap";
import { formatTimestamp, formatGPS, formatConfidence, getEvidenceUrl, getSeverityBadgeClass } from "../utils/formatters";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

export default function MapPage({ alerts, trafficDensity, onSelectAlert }) {
  const [viewMode, setViewMode] = useState("all");

  const validAlerts = alerts.filter(
    (a) => a.gps && typeof a.gps.latitude === "number" && typeof a.gps.longitude === "number" && (a.gps.latitude !== 0 || a.gps.longitude !== 0)
  );

  const mapCenter = validAlerts.length > 0
    ? [validAlerts[0].gps.latitude, validAlerts[0].gps.longitude]
    : [12.9716, 77.5946];

  const displayedMarkers = validAlerts.filter((a) => {
    if (viewMode === "heatmap") return a.module?.type !== "traffic";
    if (viewMode === "defects") return a.module?.type === "road_defect";
    if (viewMode === "incidents") return a.module?.type === "incident_anpr";
    return true;
  });

  return (
    <div className="page-container" style={{ paddingBottom: "24px" }}>
      <div className="page-header-row">
        <div className="page-header-text">
          <h1>Geographic Information System (GIS) Map</h1>
          <p>Real-time spatial telemetry of road surface defects, vehicle incidents, and traffic flow heatmaps.</p>
        </div>
        <div className="page-header-badges">
          <span className="badge badge-low">{validAlerts.length} Geolocated Coordinates</span>
        </div>
      </div>

      <div className="panel" style={{ height: "calc(100vh - 200px)", display: "flex", flexDirection: "column" }}>
        <div className="panel-header">
          <div className="panel-title-group">
            <h2>Command Map View</h2>
            <p>
              {viewMode === "heatmap"
                ? "Traffic density heat distribution (Kernel Density Estimation)"
                : "Active geolocated telemetric markers"}
            </p>
          </div>
          <div className="panel-actions">
            <div className="segmented-control">
              <button
                className={`segment-btn ${viewMode === "all" ? "active" : ""}`}
                onClick={() => setViewMode("all")}
              >
                All Markers ({validAlerts.length})
              </button>
              <button
                className={`segment-btn segment-cyan ${viewMode === "heatmap" ? "active" : ""}`}
                onClick={() => setViewMode("heatmap")}
              >
                🔥 Density Heatmap
              </button>
              <button
                className={`segment-btn segment-yellow ${viewMode === "defects" ? "active" : ""}`}
                onClick={() => setViewMode("defects")}
              >
                🛠️ Defects ({validAlerts.filter(a => a.module?.type === "road_defect").length})
              </button>
              <button
                className={`segment-btn segment-red ${viewMode === "incidents" ? "active" : ""}`}
                onClick={() => setViewMode("incidents")}
              >
                🚨 Incidents ({validAlerts.filter(a => a.module?.type === "incident_anpr").length})
              </button>
            </div>
          </div>
        </div>

        <div style={{ flex: 1, position: "relative", minHeight: 0 }}>
          <MapContainer center={mapCenter} zoom={15} scrollWheelZoom={true} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {(viewMode === "all" || viewMode === "heatmap") && (
              <TrafficHeatmap alerts={alerts} trafficDensity={trafficDensity} />
            )}

            {displayedMarkers.map((alert) => {
              const isTraffic = alert.module?.type === "traffic";
              const isIncident = alert.module?.type === "incident_anpr";
              const evidenceUrl = getEvidenceUrl(alert);

              return (
                <Marker key={alert.alert_id} position={[alert.gps.latitude, alert.gps.longitude]}>
                  <Popup>
                    <div style={{ padding: "4px", maxWidth: "220px", color: "#111111", fontFamily: "var(--font-sans)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <span className={`badge ${getSeverityBadgeClass(alert.severity)}`} style={{ fontSize: "9.5px", padding: "2px 6px" }}>
                          {alert.severity}
                        </span>
                        <span style={{ fontSize: "10px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                          {alert.alert_id}
                        </span>
                      </div>

                      {evidenceUrl && (
                        <img
                          src={evidenceUrl}
                          alt="Evidence"
                          style={{ width: "100%", height: "90px", objectFit: "cover", borderRadius: "var(--radius-sm)", marginBottom: "6px", border: "1px solid var(--line)" }}
                          onError={(e) => { e.currentTarget.style.display = "none"; }}
                        />
                      )}

                      <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "4px" }}>
                        {isTraffic
                          ? `Traffic: ${alert.payload?.congestion_level?.toUpperCase() || "CORRIDOR"}`
                          : isIncident
                            ? `Incident: ${alert.payload?.event_type?.toUpperCase() || "COLLISION"}`
                            : `Defect: ${alert.payload?.defect_type?.toUpperCase() || "POTHOLE"}`}
                      </div>

                      <div style={{ fontSize: "11px", color: "var(--muted)", marginBottom: "8px" }}>
                        GPS: {formatGPS(alert.gps)}
                      </div>

                      <button
                        className="button button-dark button-sm"
                        style={{ width: "100%", padding: "5px", fontSize: "11px" }}
                        onClick={() => onSelectAlert(alert)}
                      >
                        Inspect Evidence
                      </button>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}
