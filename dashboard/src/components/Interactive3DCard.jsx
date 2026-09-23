import React, { useRef, useState, useEffect } from "react";

/**
 * Interactive3DCard:
 * Provides subtle, hardware-accelerated 3D tilt with dynamic specular border glow.
 * Small tilt angle (max 3-4 deg) respecting the Stitch warm-neutral design.
 * Automatically disables when reduced motion is preferred or on touch/mobile devices.
 */
export default function Interactive3DCard({
  children,
  className = "",
  style = {},
  maxTilt = 3.5,
  onClick,
}) {
  const cardRef = useRef(null);
  const [transformStyle, setTransformStyle] = useState("");
  const [glarePos, setGlarePos] = useState({ x: 50, y: 50, opacity: 0 });
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Detect touch screen or mobile viewport to save battery & GPU
    const checkMobile = () => {
      const isTouch = window.matchMedia("(pointer: coarse)").matches || window.innerWidth < 768;
      const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      setIsMobile(isTouch || prefersReduced);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const handleMouseMove = (e) => {
    if (isMobile || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const xPercent = (x / rect.width) * 100;
    const yPercent = (y / rect.height) * 100;

    const rotateX = ((yPercent - 50) / 50) * -maxTilt;
    const rotateY = ((xPercent - 50) / 50) * maxTilt;

    setTransformStyle(
      `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-2px)`
    );
    setGlarePos({ x: xPercent, y: yPercent, opacity: 0.08 });
  };

  const handleMouseLeave = () => {
    if (isMobile) return;
    setTransformStyle("perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)");
    setGlarePos((prev) => ({ ...prev, opacity: 0 }));
  };

  return (
    <div
      ref={cardRef}
      className={className}
      onClick={onClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        ...style,
        transform: transformStyle,
        transition: transformStyle ? "transform 0.15s ease-out, box-shadow 0.2s ease" : "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        transformStyle: "preserve-3d",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Specular Glare Highlight */}
      {!isMobile && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            background: `radial-gradient(circle at ${glarePos.x}% ${glarePos.y}%, rgba(14, 165, 233, ${glarePos.opacity}), transparent 60%)`,
            transition: "opacity 0.25s ease",
            zIndex: 1,
          }}
        />
      )}
      <div style={{ position: "relative", zIndex: 2 }}>{children}</div>
    </div>
  );
}
