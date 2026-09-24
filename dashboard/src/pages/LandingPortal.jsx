import React, { useState, useEffect } from "react";
import HeroInteractiveMapBox from "../components/HeroInteractiveMapBox";
import TransportLogo from "../components/TransportLogo";
import Interactive3DCard from "../components/Interactive3DCard";
import AnimatedSection from "../components/AnimatedSection";

export default function LandingPortal({ onLaunchDashboard, alertsCount = 0 }) {
  const [textAnimKey, setTextAnimKey] = useState(0);

  const handleVideoLoop = () => {
    // Re-trigger the word slide entrance smoothly in sync with video loop
    setTextAnimKey((prev) => prev + 1);
  };

  return (
    <div className="landing-portal page-fade-enter">
      {/* Top Editorial Nav Header */}
      <header className="landing-nav">
        <div className="landing-brand" id="landing-brand-target">
          <img
            src="/brand/circular_logo_transparent.png"
            alt="DRISHTI"
            style={{ width: "38px", height: "38px", objectFit: "contain", flexShrink: 0 }}
          />
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <img
              src="/brand/brand_name_transparent.png"
              alt="DRISHTI"
              style={{ height: "26px", width: "auto", objectFit: "contain" }}
            />
            <span style={{ color: "var(--muted)", fontSize: "13px", fontWeight: 500 }}>
              | Smart Urban Monitoring
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <button className="launch-btn" onClick={onLaunchDashboard}>
            <span>GIS DASHBOARD</span>
            <span>→</span>
          </button>
        </div>
      </header>

      {/* Main Hero Section */}
      <section className="landing-hero" style={{ position: "relative" }}>
        <div className="hero-content" style={{ position: "relative", zIndex: 2 }}>
          <h1
            key={textAnimKey}
            className="hero-title hero-title-words-slide"
            aria-label="MOBILE URBAN INTELLIGENCE PLATFORM"
          >
            <span className="hero-slide-word" style={{ animationDelay: "0.15s" }}>MOBILE</span>{" "}
            <span className="hero-slide-word" style={{ animationDelay: "0.28s" }}>URBAN</span>{" "}
            <span className="hero-slide-word" style={{ animationDelay: "0.41s" }}>INTELLIGENCE</span>{" "}
            <span className="hero-slide-word" style={{ animationDelay: "0.54s" }}>PLATFORM</span>
          </h1>

          <p className="hero-desc">
            An engineered soft-industrial Edge AI platform deployed on public transit fleets.
            Continuously analyzing road surface defects, measuring multi-class vehicle flow, and recording forensic
            telematics with high-precision CRNN OCR license plate recognition.
          </p>

          <div className="hero-action-row">
            <button className="launch-btn" style={{ padding: "14px 28px", fontSize: "14px" }} onClick={onLaunchDashboard}>
              <span>GIS DASHBOARD</span>
              <span>→</span>
            </button>
            <button
              className="button button-dark"
              style={{ padding: "14px 24px", fontSize: "14px" }}
              onClick={onLaunchDashboard}
            >
              <span>Explore Architecture</span>
            </button>
          </div>
        </div>

        <div style={{ position: "relative", zIndex: 2, display: "flex", justifyContent: "center" }}>
          <HeroInteractiveMapBox onVideoLoop={handleVideoLoop} />
        </div>
      </section>



      {/* Technical Modules Section with Cool 3D Scroll Reveal */}
      <section className="landing-section">
        <AnimatedSection variant="3d" delay={50}>
          <div className="section-tag">Core Operational Engines</div>
          <h2 className="section-heading">Four Operational Engines. One Shared Intelligence Layer.</h2>
          <p className="section-sub">
            A single municipal transit video feed and telemetry stream powers road maintenance, traffic optimization, emergency dispatch, and passenger demand intelligence simultaneously.
          </p>
        </AnimatedSection>

        <div className="landing-cards-grid">
          {/* Module 1 */}
          <AnimatedSection variant="3d-card" delay={120}>
            <Interactive3DCard className="landing-module-card" onClick={onLaunchDashboard}>
              <div className="card-top-row">
                <span className="card-tag">MODULE 01</span>
                <span className="card-icon">🛠️</span>
              </div>
              <h3 className="card-title">Road Surface & Defect Intelligence</h3>
              <p className="card-desc">
                Custom-trained YOLOv8s on RDD2022 detecting potholes, cracks, and fissures. Multi-frame temporal tracking eliminates false positives and saves geolocated photographic evidence.
              </p>
              <div className="card-chips">
                <span>YOLOv8s</span>
                <span>PotholeTracker</span>
                <span>WAL SQLite</span>
                <span>GPS Fix</span>
              </div>
              <div className="card-btn-hint">Open Defect Operations →</div>
            </Interactive3DCard>
          </AnimatedSection>

          {/* Module 2 */}
          <AnimatedSection variant="3d-card" delay={240}>
            <Interactive3DCard className="landing-module-card" onClick={onLaunchDashboard}>
              <div className="card-top-row">
                <span className="card-tag">MODULE 02</span>
                <span className="card-icon">🚦</span>
              </div>
              <h3 className="card-title">Traffic Flow & Density Telematics</h3>
              <p className="card-desc">
                ByteTrack-powered multi-class vehicle counting across private, commercial, and public transit categories. Real-time corridor congestion scoring and spatial heatmap generation.
              </p>
              <div className="card-chips">
                <span>ByteTrack</span>
                <span>Virtual Lines</span>
                <span>Density Heatmap</span>
                <span>Corridor Triage</span>
              </div>
              <div className="card-btn-hint">Open Traffic Operations →</div>
            </Interactive3DCard>
          </AnimatedSection>

          {/* Module 3 */}
          <AnimatedSection variant="3d-card" delay={360}>
            <Interactive3DCard className="landing-module-card" onClick={onLaunchDashboard}>
              <div className="card-top-row">
                <span className="card-tag">MODULE 03</span>
                <span className="card-icon">🚨</span>
              </div>
              <h3 className="card-title">Incident Response & ANPR OCR</h3>
              <p className="card-desc">
                Accident monitoring, collision triage, and reckless driving tracking linked with CRNN character recognition on Indian vehicle number plates. Two-tier incident dispatch workflows.
              </p>
              <div className="card-chips">
                <span>CRNN CTC</span>
                <span>Emergency Dispatch</span>
                <span>Accident Triage</span>
                <span>Traffic Bureau</span>
              </div>
              <div className="card-btn-hint">Open Incident Command →</div>
            </Interactive3DCard>
          </AnimatedSection>

          {/* Module 4 */}
          <AnimatedSection variant="3d-card" delay={480}>
            <Interactive3DCard className="landing-module-card" onClick={onLaunchDashboard}>
              <div className="card-top-row">
                <span className="card-tag">MODULE 04</span>
                <span className="card-icon">👥</span>
              </div>
              <h3 className="card-title">Passenger Demand Intelligence</h3>
              <p className="card-desc">
                Data-driven boarding telemetry merging ticket transactions and conductor physical bus-pass validations. Stop-level load factor forecasting and fleet frequency recommendations without passenger cameras.
              </p>
              <div className="card-chips">
                <span>Pass Registry</span>
                <span>ETM Boarding</span>
                <span>Peak Detector</span>
                <span>Decision Support</span>
              </div>
              <div className="card-btn-hint">Open Demand Telematics →</div>
            </Interactive3DCard>
          </AnimatedSection>
        </div>
      </section>

      {/* Editorial Footer */}
      <footer style={{ borderTop: "1px solid var(--line)", padding: "48px 32px", maxWidth: "1280px", margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <img
            src="/brand/circular_logo_transparent.png"
            alt="DRISHTI"
            style={{ width: "28px", height: "28px", objectFit: "contain", flexShrink: 0 }}
          />
          <img
            src="/brand/brand_name_transparent.png"
            alt="DRISHTI"
            style={{ height: "18px", width: "auto", objectFit: "contain" }}
          />
          <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--muted)" }}>| Smart Urban Monitoring</span>
          <span style={{ fontSize: "12px", color: "var(--muted)" }}>© 2026 DRISHTI Platform. Engineered for precision.</span>
        </div>
        <div style={{ display: "flex", gap: "24px", fontSize: "13px", color: "var(--muted)" }}>
          <span style={{ cursor: "pointer", color: "#111111", fontWeight: 500 }} onClick={onLaunchDashboard}>Command Center</span>
          <span style={{ cursor: "pointer", color: "#111111", fontWeight: 500 }} onClick={onLaunchDashboard}>GIS Maps</span>
          <span style={{ cursor: "pointer", color: "#111111", fontWeight: 500 }} onClick={onLaunchDashboard}>Telemetry Specs</span>
        </div>
      </footer>
    </div>
  );
}
