import React, { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * HeroCorridor3D:
 * A lightweight, engineered 3D transit wireframe ribbon and spatial sensor constellation.
 * Uses Three.js with hardware acceleration, low particle count, and mouse-parallax.
 * Stays visually subordinate to the Stitch editorial typography.
 */
export default function HeroCorridor3D() {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Check device capability
    const isMobile = window.innerWidth < 768;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Set up Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.set(0, 3, 12);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    container.appendChild(renderer.domElement);

    // Subtle Road Corridor Plane / Grid
    const gridHelper = new THREE.GridHelper(24, 24, 0x111111, 0xE7E7E4);
    gridHelper.position.y = -1.5;
    scene.add(gridHelper);

    // Floating Sensor Wave Nodes (Subtle, low count)
    const particleCount = isMobile ? 25 : 60;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    const color1 = new THREE.Color(0x0EA5E9); // cyan
    const color2 = new THREE.Color(0x10B981); // emerald
    const color3 = new THREE.Color(0x6366F1); // indigo

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 14;
      positions[i * 3 + 1] = Math.random() * 4 - 1;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 10;

      const chosenColor = i % 3 === 0 ? color1 : i % 3 === 1 ? color2 : color3;
      colors[i * 3] = chosenColor.r;
      colors[i * 3 + 1] = chosenColor.g;
      colors[i * 3 + 2] = chosenColor.b;
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 0.12,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // Mouse Interaction
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const onMouseMove = (e) => {
      if (prefersReduced) return;
      mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    };

    window.addEventListener("mousemove", onMouseMove);

    // Handle Resize
    const onResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener("resize", onResize);

    // Animation Loop
    let animId;
    let clock = new THREE.Clock();

    const animate = () => {
      const delta = clock.getDelta();

      if (!prefersReduced) {
        // Slow continuous forward motion on the grid to simulate vehicle corridor progression
        gridHelper.position.z = (gridHelper.position.z + delta * 1.5) % 1;

        // Smooth camera dampening to mouse
        targetX += (mouseX * 0.8 - targetX) * 0.04;
        targetY += (-mouseY * 0.5 - targetY) * 0.04;
        camera.position.x = targetX;
        camera.position.y = 3 + targetY;
        camera.lookAt(0, 0, 0);

        // Gentle undulating particle drift
        const posArray = geometry.attributes.position.array;
        for (let i = 0; i < particleCount; i++) {
          posArray[i * 3 + 1] += Math.sin(clock.getElapsedTime() + i) * 0.002;
        }
        geometry.attributes.position.needsUpdate = true;
      }

      renderer.render(scene, camera);
      animId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onResize);
      if (renderer.domElement && renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute",
        top: 0,
        right: 0,
        width: "55%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 1,
        opacity: 0.65,
        overflow: "hidden",
      }}
    />
  );
}
