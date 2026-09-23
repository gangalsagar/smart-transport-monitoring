import React, { useState, useEffect } from "react";

/**
 * HeroInteractiveMapBox:
 * Realistic large-scale city cartography simulation (based on Bengaluru radial-concentric layout).
 * - Exact 5:3 aspect ratio container.
 * - Header text ("Metropolitan Road Network Map" & "SECTOR 07 · 5 ARTERIES ACTIVE") removed completely.
 * - Pure static cartographic base with intricate arterial highways, inner ring road, outer ring road,
 *   expressway corridors, secondary street mesh, water bodies (lakes), and green forest reserves.
 * - Popups appear strictly ONE AFTER ANOTHER in a continuous looping sequence (not shown simultaneously).
 * - Each popup highlights a distinct real-world traffic phenomenon across different roads.
 */
export default function HeroInteractiveMapBox({ onVideoLoop }) {
  const videoSrc = "/so_i_want_you_to_use_the_given (1).mp4?v=2";
  const videoRef = React.useRef(null);
  const lastTimeRef = React.useRef(0);

  const handleTimeUpdate = (e) => {
    const video = e.target;
    // Detect when video loops back to start (currentTime < lastTime)
    if (video.currentTime < lastTimeRef.current - 0.5 && lastTimeRef.current > 1.0) {
      if (onVideoLoop) {
        onVideoLoop();
      }
    }
    lastTimeRef.current = video.currentTime;
  };

  const handleEnded = () => {
    if (onVideoLoop) {
      onVideoLoop();
    }
  };

  return (
    <div
      style={{
        width: "100%",
        maxWidth: "760px",
        aspectRatio: "16 / 9",
        background: "#FCFCFB",
        border: "1px solid #E7E7E4",
        borderRadius: "26px",
        padding: "10px",
        boxShadow: "0 24px 60px -12px rgba(0, 0, 0, 0.12)",
        position: "relative",
        overflow: "hidden",
        display: "flex",
      }}
    >
      {/* Video Canvas Container */}
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#000000",
          borderRadius: "18px",
          border: "1px solid #E3E2DC",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <video
          ref={videoRef}
          src={videoSrc}
          autoPlay
          loop
          muted
          playsInline
          onTimeUpdate={handleTimeUpdate}
          onEnded={handleEnded}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
            borderRadius: "18px",
          }}
        />
      </div>
    </div>
  );
}
