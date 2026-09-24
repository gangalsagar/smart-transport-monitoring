import React, { useState, useEffect } from "react";
import LandingPortal from "./pages/LandingPortal";
import OverviewPage from "./pages/OverviewPage";
import RoadDefectsPage from "./pages/RoadDefectsPage";
import TrafficPage from "./pages/TrafficPage";
import IncidentsPage from "./pages/IncidentsPage";
import VehiclesANPRPage from "./pages/VehiclesANPRPage";
import MapPage from "./pages/MapPage";
import SystemHealthPage from "./pages/SystemHealthPage";
import PassengerDemandPage from "./pages/PassengerDemandPage";
import EvidenceModal from "./components/EvidenceModal";
import ThreeParticleCanvas from "./components/ThreeParticleCanvas";
import TransportLogo from "./components/TransportLogo";
import IntroSplash from "./components/IntroSplash";
import { API_BASE_URL, formatTimestamp } from "./utils/formatters";

export default function App() {
  // In-memory state: Always true when application loads or browser refreshes.
  // Never stored in localStorage, so full refresh plays intro, but internal navigation does not!
  const [playIntro, setPlayIntro] = useState(true);

  // Persist view state so refresh returns user to their current view (e.g. /dashboard or landing)
  const [currentView, setCurrentView] = useState(() => {
    return localStorage.getItem("stm_current_view") || "landing";
  });
  const [activeTab, setActiveTab] = useState("overview");

  const navigateToDashboard = () => {
    setCurrentView("dashboard");
    localStorage.setItem("stm_current_view", "dashboard");
  };

  const navigateToLanding = () => {
    setCurrentView("landing");
    localStorage.setItem("stm_current_view", "landing");
  };
  const [alerts, setAlerts] = useState([]);
  const [trafficDensity, setTrafficDensity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);

  // Load backend alerts and traffic density
  async function loadData() {
    try {
      setError("");
      const alertsResponse = await fetch(`${API_BASE_URL}/alerts`);
      if (!alertsResponse.ok) {
        throw new Error(`HTTP error ${alertsResponse.status}`);
      }
      const alertsData = await alertsResponse.json();
      setAlerts(alertsData.alerts || []);

      try {
        const trafficResp = await fetch(`${API_BASE_URL}/traffic/density`);
        if (trafficResp.ok) {
          const trafficData = await trafficResp.json();
          setTrafficDensity(trafficData.traffic_density || []);
        }
      } catch (err) {
        console.warn("Traffic density fetch issue:", err);
      }

      setLastUpdated(new Date());
    } catch (err) {
      console.error("Backend connection error:", err);
      setError(`Central backend disconnected (${API_BASE_URL.replace(/^https?:\/\//, "")})`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const roadDefectsCount = alerts.filter((a) => a.module?.type === "road_defect").length;
  const trafficCount = alerts.filter((a) => a.module?.type === "traffic").length;
  const incidentCount = alerts.filter((a) => a.module?.type === "incident_anpr").length;

  return (
    <div className="command-center">
      {/* Universal 3D Spatial Particle Constellation Backdrop */}
      <ThreeParticleCanvas />

      {/* Application Load / Browser Refresh Intro Experience */}
      {playIntro && (
        <IntroSplash onComplete={() => setPlayIntro(false)} />
      )}

      {currentView === "landing" ? (
        <LandingPortal
          onLaunchDashboard={navigateToDashboard}
          alertsCount={alerts.length}
        />
      ) : (
        <>
          {/* Sidebar Navigation */}
          <aside className="sidebar">
            <div className="sidebar-header" style={{ cursor: "pointer" }} onClick={navigateToLanding} title="Return to Landing Portal">
              <img
                src="/brand/circular_logo_transparent.png"
                alt="DRISHTI"
                style={{ width: "34px", height: "34px", objectFit: "contain", flexShrink: 0 }}
              />
              <div className="brand-info">
                <img
                  src="/brand/brand_name_transparent.png"
                  alt="DRISHTI"
                  style={{ height: "20px", width: "auto", objectFit: "contain", alignSelf: "flex-start" }}
                />
                <span className="brand-subtitle" style={{ fontSize: "10.5px", color: "var(--muted)", fontWeight: 500, letterSpacing: "0.02em" }}>
                  Smart Urban Monitoring
                </span>
              </div>
            </div>

            <nav className="sidebar-nav">
              <div className="nav-section-label">Command & Control</div>

              <button
                className={`nav-item ${activeTab === "overview" ? "active" : ""}`}
                onClick={() => setActiveTab("overview")}
              >
                <span className="nav-icon">📊</span>
                <span>Overview</span>
              </button>

              <button
                className={`nav-item ${activeTab === "map" ? "active" : ""}`}
                onClick={() => setActiveTab("map")}
              >
                <span className="nav-icon">🗺️</span>
                <span>GIS Map</span>
                <span className="nav-badge">{alerts.length}</span>
              </button>

              <div className="nav-section-label">Operational Modules</div>

              <button
                className={`nav-item ${activeTab === "defects" ? "active" : ""}`}
                onClick={() => setActiveTab("defects")}
              >
                <span className="nav-icon">🛠️</span>
                <span>Road Defects</span>
                <span className="nav-badge">{roadDefectsCount}</span>
              </button>

              <button
                className={`nav-item ${activeTab === "traffic" ? "active" : ""}`}
                onClick={() => setActiveTab("traffic")}
              >
                <span className="nav-icon">🚦</span>
                <span>Traffic Flow</span>
                <span className="nav-badge">{trafficCount}</span>
              </button>

              <button
                className={`nav-item ${activeTab === "incidents" ? "active" : ""}`}
                onClick={() => setActiveTab("incidents")}
              >
                <span className="nav-icon">🚨</span>
                <span>Incidents & Dispatch</span>
                {incidentCount > 0 && <span className="nav-badge danger">{incidentCount}</span>}
              </button>

              {/* Temporarily hidden from navigation
              <button
                className={`nav-item ${activeTab === "anpr" ? "active" : ""}`}
                onClick={() => setActiveTab("anpr")}
              >
                <span className="nav-icon">🚘</span>
                <span>Vehicles / ANPR</span>
              </button>
              */}

              <button
                className={`nav-item ${activeTab === "passengers" ? "active" : ""}`}
                onClick={() => setActiveTab("passengers")}
              >
                <span className="nav-icon">👥</span>
                <span>Passenger Demand</span>
                <span className="nav-badge" style={{ background: "rgba(59, 130, 246, 0.15)", color: "#3B82F6", borderColor: "rgba(59, 130, 246, 0.3)" }}>M4</span>
              </button>

              <div className="nav-section-label">Infrastructure</div>

              <button
                className={`nav-item ${activeTab === "health" ? "active" : ""}`}
                onClick={() => setActiveTab("health")}
              >
                <span className="nav-icon">📡</span>
                <span>System Health</span>
              </button>
            </nav>

            <div className="sidebar-footer">
              <div className="system-status-indicator">
                <div className="live-pulse">
                  <span className={`pulse-dot ${error ? "error" : "green"}`} />
                  <span style={{ letterSpacing: "0.5px" }}>{error ? "BACKEND OFFLINE" : "SYSTEM ONLINE"}</span>
                </div>
                <div className="server-endpoint-text">FASTAPI · {API_BASE_URL.replace(/^https?:\/\//, "")}</div>
              </div>
            </div>
          </aside>

          {/* Main Content Area */}
          <main className="main-wrapper">
            <header className="top-bar">
              <div className="top-left">
                <button
                  className="return-home-btn"
                  onClick={navigateToLanding}
                  title="Return to 3D Landing Portal"
                >
                  <span className="return-arrow">←</span>
                  <span>Portal</span>
                </button>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-label">Mission Command</span>
                <span className="breadcrumb-separator">/</span>
                <span className="breadcrumb-current">
                  {activeTab === "overview" && "Executive Fleet Overview"}
                  {activeTab === "map" && "Geospatial Telemetry (GIS)"}
                  {activeTab === "defects" && "Module 1: Road Surface Infrastructure"}
                  {activeTab === "traffic" && "Module 2: Traffic Flow & Congestion"}
                  {activeTab === "incidents" && "Module 3: Incident Response Dispatch"}
                  {activeTab === "anpr" && "Vehicle Identity & ANPR OCR"}
                  {activeTab === "passengers" && "Module 4: Passenger Demand Intelligence"}
                  {activeTab === "health" && "Hardware & Edge Infrastructure"}
                </span>
              </div>

              <div className="top-right">
                <div className="live-clock-pill">
                  <span className="pulse-dot green" style={{ width: "6px", height: "6px" }} />
                  <span>POLLING 5s</span>
                </div>

                <span className="timestamp-indicator">
                  {lastUpdated ? `SYNCED: ${new Date(lastUpdated).toLocaleTimeString()}` : "CONNECTING..."}
                </span>

                <button className="refresh-button" onClick={loadData} title="Force immediate telemetry poll">
                  <span>↻</span>
                  <span>Refresh</span>
                </button>
              </div>
            </header>

        {activeTab === "overview" && (
          <OverviewPage
            alerts={alerts}
            trafficDensity={trafficDensity}
            onSelectAlert={setSelectedAlert}
            onSelectTab={setActiveTab}
          />
        )}

        {activeTab === "defects" && (
          <RoadDefectsPage alerts={alerts} onSelectAlert={setSelectedAlert} />
        )}

        {activeTab === "traffic" && (
          <TrafficPage
            alerts={alerts}
            trafficDensity={trafficDensity}
            onSelectAlert={setSelectedAlert}
          />
        )}

        {activeTab === "incidents" && (
          <IncidentsPage alerts={alerts} onSelectAlert={setSelectedAlert} onRefresh={loadData} />
        )}

        {activeTab === "anpr" && (
          <VehiclesANPRPage alerts={alerts} onSelectAlert={setSelectedAlert} />
        )}

        {activeTab === "passengers" && (
          <PassengerDemandPage />
        )}

        {activeTab === "map" && (
          <MapPage alerts={alerts} trafficDensity={trafficDensity} onSelectAlert={setSelectedAlert} />
        )}

        {activeTab === "health" && (
          <SystemHealthPage
            alerts={alerts}
            lastUpdated={lastUpdated}
            backendConnected={!error}
            onRefresh={loadData}
          />
        )}
      </main>
    </>
  )}

      {/* Forensic Evidence Lightbox Modal */}
      {selectedAlert && (
        <EvidenceModal item={selectedAlert} onClose={() => setSelectedAlert(null)} />
      )}
    </div>
  );
}