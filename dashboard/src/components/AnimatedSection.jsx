import React, { useEffect, useRef, useState } from "react";

/**
 * AnimatedSection / 3D Scroll Reveal:
 * Smooth, hardware-accelerated 3D perspective entrance upon scrolling into viewport.
 * Features 3D tilt-up perspective, depth translation, subtle zoom, and fluid cubic-bezier easing.
 * Respects prefers-reduced-motion.
 */
export default function AnimatedSection({
  children,
  className = "",
  style = {},
  delay = 0,
  variant = "3d", // '3d' | '3d-card' | 'up' | 'fade'
}) {
  const domRef = useRef(null);
  const [isVisible, setVisible] = useState(false);

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
        } else {
          // Reset when scrolling away so it animates again when scrolling back
          setVisible(false);
        }
      },
      {
        threshold: 0.12,
        rootMargin: "0px 0px -40px 0px",
      }
    );

    const current = domRef.current;
    if (current) observer.observe(current);

    return () => {
      if (current) observer.unobserve(current);
    };
  }, []);

  // 3D Perspective transformations
  let initialTransform = "perspective(1200px) rotateX(14deg) translateY(45px) translateZ(-40px) scale(0.96)";
  let activeTransform = "perspective(1200px) rotateX(0deg) translateY(0px) translateZ(0px) scale(1)";

  if (variant === "3d-card") {
    initialTransform = "perspective(1000px) rotateX(18deg) translateY(55px) scale(0.94)";
    activeTransform = "perspective(1000px) rotateX(0deg) translateY(0px) scale(1)";
  } else if (variant === "up") {
    initialTransform = "translateY(30px)";
    activeTransform = "translateY(0px)";
  } else if (variant === "fade") {
    initialTransform = "none";
    activeTransform = "none";
  }

  return (
    <div
      ref={domRef}
      className={className}
      style={{
        ...style,
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? activeTransform : initialTransform,
        transformOrigin: "center top",
        transition: `opacity 0.85s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms, transform 0.95s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms`,
        willChange: "opacity, transform",
      }}
    >
      {children}
    </div>
  );
}
