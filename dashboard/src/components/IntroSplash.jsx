import React, { useState, useEffect, useRef } from "react";

/**
 * IntroSplash Component
 * 
 * Implements a premium full-screen intro / splash experience based on Scene.mp4
 * with a seamless FLIP animation moving the logo and brand name to their exact
 * place in the landing page navbar during the exit transition.
 * 
 * Flow:
 * Phase 1: Initial state (subtle central dot).
 * Phase 2: Logo expands smoothly to center stage.
 * Phase 3: Brand name "DRISHTI" slides out horizontally next to the logo.
 * Phase 4: Brief hold of the complete horizontal lockup (~1400ms - 2200ms).
 * Phase 5: Smooth FLIP glide — the logo and brand name smoothly glide and scale
 *          from the center of the screen directly into the navbar brand position,
 *          while the white background softly dissolves into the landing page.
 */
export default function IntroSplash({ onComplete }) {
  // 'initial' | 'logo_reveal' | 'brand_reveal' | 'hold' | 'morphing' | 'done'
  const [animStage, setAnimStage] = useState("initial");
  const [isFadingBg, setIsFadingBg] = useState(false);
  const [morphStyle, setMorphStyle] = useState({});
  const lockupRef = useRef(null);

  useEffect(() => {
    // Check reduced motion preference
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      const timer = setTimeout(() => {
        setIsFadingBg(true);
        setTimeout(() => onComplete && onComplete(), 300);
      }, 600);
      return () => clearTimeout(timer);
    }

    // Sequence timing
    // 0ms - 60ms: Initial state
    // 60ms: Logo expands smoothly from center
    const t1 = setTimeout(() => {
      setAnimStage("logo_reveal");
    }, 60);

    // 720ms: Brand name slides out and reveals horizontally
    const t2 = setTimeout(() => {
      setAnimStage("brand_reveal");
    }, 720);

    // 1400ms: Complete lockup holds in perfect equilibrium
    const t3 = setTimeout(() => {
      setAnimStage("hold");
    }, 1400);

    // 2150ms: Trigger smooth FLIP movement towards the landing page navbar location
    const t4 = setTimeout(() => {
      triggerGlideToLanding();
    }, 2150);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, []);

  const triggerGlideToLanding = () => {
    const lockupEl = lockupRef.current;
    const destEl = document.getElementById("landing-brand-target");

    if (lockupEl && destEl) {
      const startRect = lockupEl.getBoundingClientRect();
      const destRect = destEl.getBoundingClientRect();

      // Calculate translation offset and scale factor
      const deltaX = destRect.left - startRect.left;
      const deltaY = destRect.top - startRect.top;
      // Target logo size is ~38px, lockup initial logo is 130px -> scale ratio ~ 0.36
      const scale = destRect.height > 0 ? (destRect.height / startRect.height) * 0.95 : 0.36;

      setAnimStage("morphing");
      setIsFadingBg(true);

      // Start position (fixed in place)
      setMorphStyle({
        transformOrigin: "top left",
        transform: "translate(0px, 0px) scale(1)",
        transition: "transform 0.9s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.85s ease",
        opacity: 1,
      });

      // Animate smoothly to destination in next frame
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setMorphStyle({
            transformOrigin: "top left",
            transform: `translate(${deltaX}px, ${deltaY}px) scale(${scale})`,
            transition: "transform 0.9s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.85s ease",
            opacity: 0.95,
          });
        });
      });

      // Complete transition
      setTimeout(() => {
        setAnimStage("done");
        if (onComplete) onComplete();
      }, 920);
    } else {
      // Fallback if destination element is not yet in DOM
      setIsFadingBg(true);
      setTimeout(() => {
        setAnimStage("done");
        if (onComplete) onComplete();
      }, 600);
    }
  };

  if (animStage === "done") return null;

  return (
    <div
      className={`intro-splash-screen ${isFadingBg ? "intro-fading-out" : ""}`}
      aria-hidden="true"
    >
      <div
        ref={lockupRef}
        className="intro-lockup-container"
        style={animStage === "morphing" ? morphStyle : {}}
      >
        {/* Official Logo */}
        <div className={`intro-logo-wrapper stage-${animStage}`}>
          <img
            src="/brand/circular_logo_transparent.png"
            alt="Drishti Logo"
            className="intro-logo-img"
          />
        </div>

        {/* Official Brand Name "DRISHTI" */}
        <div className={`intro-brand-name-wrapper stage-${animStage}`}>
          <img
            src="/brand/brand_name_transparent.png"
            alt="DRISHTI"
            className="intro-brand-name-img"
          />
        </div>
      </div>
    </div>
  );
}
