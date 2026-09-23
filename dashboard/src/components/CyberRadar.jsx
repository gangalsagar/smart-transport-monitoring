import React, { useEffect, useRef } from "react";

export default function CyberRadar({ size = 180 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let angle = 0;
    canvas.width = size;
    canvas.height = size;
    const cx = size / 2;
    const cy = size / 2;
    const r = size / 2 - 10;

    const blips = [
      { r: r * 0.38, angle: 0.85, color: "#0EA5E9", size: 3, label: "CAM-01" },
      { r: r * 0.72, angle: 2.3, color: "#EF4444", size: 3.5, label: "INCIDENT" },
      { r: r * 0.52, angle: 4.15, color: "#F59E0B", size: 3, label: "DEFECT" },
      { r: r * 0.84, angle: 5.4, color: "#10B981", size: 3, label: "CONVOY" },
    ];

    let animId;
    const draw = () => {
      ctx.clearRect(0, 0, size, size);

      // Outer bezel ring
      ctx.beginPath();
      ctx.arc(cx, cy, r + 4, 0, Math.PI * 2);
      ctx.strokeStyle = "#E7E7E4";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Concentric telemetry range rings
      const rings = [1, 0.75, 0.5, 0.25];
      rings.forEach((scale, idx) => {
        ctx.beginPath();
        ctx.arc(cx, cy, r * scale, 0, Math.PI * 2);
        ctx.strokeStyle = idx === 0 ? "#D6D6D2" : "#EAEAE6";
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      // Axis crosshairs
      ctx.beginPath();
      ctx.moveTo(cx - r, cy);
      ctx.lineTo(cx + r, cy);
      ctx.moveTo(cx, cy - r);
      ctx.lineTo(cx, cy + r);
      ctx.strokeStyle = "#E5E5E0";
      ctx.lineWidth = 0.75;
      ctx.stroke();

      // Sweeper cone gradient (Muted luminous sweep)
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, angle - 0.7, angle, false);
      ctx.closePath();
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
      grad.addColorStop(0, "rgba(17, 17, 17, 0.15)");
      grad.addColorStop(0.7, "rgba(14, 165, 233, 0.08)");
      grad.addColorStop(1, "rgba(247, 247, 245, 0)");
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.restore();

      // Scanning leading beam
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(angle) * r, cy + Math.sin(angle) * r);
      ctx.strokeStyle = "rgba(17, 17, 17, 0.6)";
      ctx.lineWidth = 1.25;
      ctx.stroke();

      // Center antenna core
      ctx.beginPath();
      ctx.arc(cx, cy, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#111111";
      ctx.fill();

      // Target blips with ping fade
      blips.forEach((b) => {
        const bx = cx + Math.cos(b.angle) * b.r;
        const by = cy + Math.sin(b.angle) * b.r;
        const diff = (angle - b.angle + Math.PI * 2) % (Math.PI * 2);
        const alpha = Math.max(0.15, 1 - diff / (Math.PI * 2));

        ctx.save();
        ctx.beginPath();
        ctx.arc(bx, by, b.size, 0, Math.PI * 2);
        ctx.fillStyle = b.color;
        ctx.globalAlpha = alpha;
        ctx.fill();

        if (alpha > 0.75) {
          ctx.font = "600 8.5px 'JetBrains Mono', monospace";
          ctx.fillStyle = "#111111";
          ctx.fillText(b.label, bx + 6, by - 2);
        }
        ctx.restore();
      });

      angle = (angle + 0.024) % (Math.PI * 2);
      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => cancelAnimationFrame(animId);
  }, [size]);

  return (
    <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
      <canvas ref={canvasRef} style={{ width: `${size}px`, height: `${size}px`, borderRadius: "50%" }} />
    </div>
  );
}
