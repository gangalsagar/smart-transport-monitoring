import React from "react";

export default function TransportLogo({ size = 36 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 44 44"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ display: "inline-block", verticalAlign: "middle", flexShrink: 0 }}
    >
      <defs>
        <linearGradient id="auralisShield" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#111111" />
          <stop offset="100%" stopColor="#2A2A2A" />
        </linearGradient>
      </defs>

      {/* Octagonal Soft-Industrial Shield */}
      <polygon
        points="14,3 30,3 41,14 41,30 30,41 14,41 3,30 3,14"
        stroke="#E7E7E4"
        strokeWidth="1.5"
        fill="#FCFCFB"
      />

      {/* Subtle Grid Guides */}
      <circle cx="22" cy="22" r="13" stroke="#F1EDEC" strokeWidth="1" strokeDasharray="2 3" />
      <line x1="22" y1="9" x2="22" y2="35" stroke="#E7E7E4" strokeWidth="1" strokeDasharray="2 2" />
      <line x1="9" y1="22" x2="35" y2="22" stroke="#E7E7E4" strokeWidth="1" strokeDasharray="2 2" />

      {/* Artery Vector Paths */}
      <path
        d="M14 30L22 22L30 14"
        stroke="#111111"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M14 14L22 22L30 30"
        stroke="#747878"
        strokeWidth="1.5"
        strokeLinecap="round"
      />

      {/* Core Node */}
      <circle cx="22" cy="22" r="3.5" fill="#111111" />
      <circle cx="22" cy="22" r="1.5" fill="#FFFFFF" />

      {/* Active Sensory Beacons */}
      <circle cx="22" cy="3" r="1.5" fill="#10B981" />
      <circle cx="41" cy="22" r="1.5" fill="#0EA5E9" />
      <circle cx="22" cy="41" r="1.5" fill="#8B5CF6" />
      <circle cx="3" cy="22" r="1.5" fill="#F59E0B" />
    </svg>
  );
}
