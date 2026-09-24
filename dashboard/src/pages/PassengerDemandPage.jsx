import React, { useState } from "react";
import Interactive3DCard from "../components/Interactive3DCard";

// ============================================================================
// CENTRALIZED CALCULATION & CLASSIFICATION ENGINES
// ============================================================================

/**
 * Centralized Occupancy Calculation:
 * Formula: occupancy = (passengers / capacity) * 100
 * CRITICAL: NEVER clamped with Math.min(x, 100).
 */
export function calculateOccupancy(passengers, capacity) {
  if (!capacity || capacity <= 0) return 0;
  return Math.round((passengers / capacity) * 100);
}

/**
 * Centralized Classification Engine:
 * if passengers === 0: NO DEMAND
 * else if occupancy < 80: NORMAL
 * else if occupancy <= 100: HIGH DEMAND
 * else: OVERCAPACITY
 */
export function getDemandStatus(passengers, capacity) {
  if (passengers === 0) {
    return "NO DEMAND";
  }
  const occ = calculateOccupancy(passengers, capacity);
  if (occ < 80) {
    return "NORMAL";
  } else if (occ <= 100) {
    return "HIGH DEMAND";
  } else {
    return "OVERCAPACITY";
  }
}

/**
 * Centralized Bus Requirement Engine:
 * requiredBuses = Math.ceil(passengers / busCapacity)
 * additionalBuses = Math.max(0, requiredBuses - currentBuses)
 * NEVER round down.
 */
export function calculateBusRequirement(passengers, busCapacity, currentBuses) {
  if (passengers <= 0) {
    return { requiredBuses: 0, additionalBuses: 0 };
  }
  const cap = busCapacity > 0 ? busCapacity : 50;
  const requiredBuses = Math.ceil(passengers / cap);
  const additionalBuses = Math.max(0, requiredBuses - (currentBuses || 0));
  return { requiredBuses, additionalBuses };
}

// Styling helper for status badges and colors
export function getStatusTheme(status) {
  switch (status) {
    case "NO DEMAND":
      return {
        badgeClass: "badge-neutral",
        textColor: "var(--muted)",
        badgeBg: "rgba(107, 114, 128, 0.12)",
        badgeBorder: "rgba(107, 114, 128, 0.3)",
        accentColor: "#6B7280",
        bgTint: "rgba(107, 114, 128, 0.05)",
      };
    case "NORMAL":
      return {
        badgeClass: "badge-low",
        textColor: "#059669",
        badgeBg: "rgba(16, 185, 129, 0.12)",
        badgeBorder: "rgba(16, 185, 129, 0.3)",
        accentColor: "#10B981",
        bgTint: "rgba(16, 185, 129, 0.05)",
      };
    case "HIGH DEMAND":
      return {
        badgeClass: "badge-high",
        textColor: "#D97706",
        badgeBg: "rgba(245, 158, 11, 0.12)",
        badgeBorder: "rgba(245, 158, 11, 0.3)",
        accentColor: "#F59E0B",
        bgTint: "rgba(245, 158, 11, 0.05)",
      };
    case "OVERCAPACITY":
      return {
        badgeClass: "badge-critical",
        textColor: "#DC2626",
        badgeBg: "rgba(239, 68, 68, 0.12)",
        badgeBorder: "rgba(239, 68, 68, 0.3)",
        accentColor: "#EF4444",
        bgTint: "rgba(239, 68, 68, 0.05)",
      };
    default:
      return {
        badgeClass: "badge-neutral",
        textColor: "var(--text)",
        badgeBg: "var(--section-bg)",
        badgeBorder: "var(--line)",
        accentColor: "#3B82F6",
        bgTint: "var(--section-bg)",
      };
  }
}

// ============================================================================
// DEMO / MOCK DATA (Progressive Route & Hourly Telemetry)
// ============================================================================

// Operating hours surveyed: 06:00 to 20:00
const OPERATING_HOURS = [
  "06:00–07:00",
  "07:00–08:00",
  "08:00–09:00",
  "09:00–10:00",
  "10:00–11:00",
  "11:00–12:00",
  "12:00–13:00",
  "13:00–14:00",
  "14:00–15:00",
  "15:00–16:00",
  "16:00–17:00",
  "17:00–18:00",
  "18:00–19:00",
  "19:00–20:00",
  "20:00–21:00",
];

// Route Definitions ensuring coverage of all 4 categories:
// 1. NO DEMAND (passengers = 0)
// 2. NORMAL (occupancy < 80%)
// 3. HIGH DEMAND (80% <= occupancy <= 100%)
// 4. OVERCAPACITY (occupancy > 100%)
// Explicit example: Route 25A 08:00-09:00 has 100 passengers, 50 capacity, 1 current bus -> 200% occupancy, 2 required buses, 1 additional bus!
// ============================================================================
// DATE-WISE DATA STORE (Multi-date historical & live telemetry storage)
// ============================================================================

export const DATE_ARCHIVE_STORAGE = {
  "2026-09-24": {
    label: "Today (Sep 24, 2026)",
    kpis: {
      total_passengers: "12,480",
      total_trips: "186",
      avg_occupancy: "87%",
      peak_demand_hour: "08:00–09:00",
      overcapacity_trips: "14",
    },
    routes: {
      "25A": {
        route: "25A",
        corridor: "Central Railway Stn ⇄ Cyber Tech Park",
        busCapacity: 50,
        trips: 12,
        passengers: 642,
        capacity: 600,
        hourlySchedule: [
          { hour: "06:00–07:00", hourLabel: "06:00", passengers: 22, currentBuses: 1 },
          { hour: "07:00–08:00", hourLabel: "07:00", passengers: 48, currentBuses: 1 },
          { hour: "08:00–09:00", hourLabel: "08:00", passengers: 100, currentBuses: 1 }, // 200%
          { hour: "09:00–10:00", hourLabel: "09:00", passengers: 72, currentBuses: 1 },  // 144%
          { hour: "10:00–11:00", hourLabel: "10:00", passengers: 42, currentBuses: 1 },
          { hour: "11:00–12:00", hourLabel: "11:00", passengers: 31, currentBuses: 1 },
          { hour: "12:00–13:00", hourLabel: "12:00", passengers: 38, currentBuses: 1 },
          { hour: "13:00–14:00", hourLabel: "13:00", passengers: 34, currentBuses: 1 },
          { hour: "14:00–15:00", hourLabel: "14:00", passengers: 30, currentBuses: 1 },
          { hour: "15:00–16:00", hourLabel: "15:00", passengers: 41, currentBuses: 1 },
          { hour: "16:00–17:00", hourLabel: "16:00", passengers: 55, currentBuses: 1 },
          { hour: "17:00–18:00", hourLabel: "17:00", passengers: 88, currentBuses: 1 }, // 176%
          { hour: "18:00–19:00", hourLabel: "18:00", passengers: 24, currentBuses: 1 },
          { hour: "19:00–20:00", hourLabel: "19:00", passengers: 17, currentBuses: 0 },
          { hour: "20:00–21:00", hourLabel: "20:00", passengers: 0, currentBuses: 0 },
        ],
        buses: [
          { bus: "BUS-101", trip: "08:00", passengers: 48, capacity: 50 },
          { bus: "BUS-102", trip: "08:00", passengers: 52, capacity: 50 },
          { bus: "BUS-108", trip: "08:00", passengers: 100, capacity: 50 },
          { bus: "BUS-112", trip: "09:00", passengers: 72, capacity: 50 },
          { bus: "BUS-114", trip: "17:00", passengers: 88, capacity: 50 },
        ],
      },
      "42C": {
        route: "42C",
        corridor: "South Terminal ⇄ University Campus",
        busCapacity: 50,
        trips: 11,
        passengers: 517,
        capacity: 550,
        hourlySchedule: [
          { hour: "06:00–07:00", hourLabel: "06:00", passengers: 18, currentBuses: 1 },
          { hour: "07:00–08:00", hourLabel: "07:00", passengers: 39, currentBuses: 1 },
          { hour: "08:00–09:00", hourLabel: "08:00", passengers: 59, currentBuses: 1 }, // 118%
          { hour: "09:00–10:00", hourLabel: "09:00", passengers: 48, currentBuses: 1 },
          { hour: "10:00–11:00", hourLabel: "10:00", passengers: 44, currentBuses: 1 },
          { hour: "11:00–12:00", hourLabel: "11:00", passengers: 32, currentBuses: 1 },
          { hour: "12:00–13:00", hourLabel: "12:00", passengers: 36, currentBuses: 1 },
          { hour: "13:00–14:00", hourLabel: "13:00", passengers: 31, currentBuses: 1 },
          { hour: "14:00–15:00", hourLabel: "14:00", passengers: 29, currentBuses: 1 },
          { hour: "15:00–16:00", hourLabel: "15:00", passengers: 42, currentBuses: 1 },
          { hour: "16:00–17:00", hourLabel: "16:00", passengers: 47, currentBuses: 1 },
          { hour: "17:00–18:00", hourLabel: "17:00", passengers: 52, currentBuses: 1 },
          { hour: "18:00–19:00", hourLabel: "18:00", passengers: 20, currentBuses: 0 },
          { hour: "19:00–20:00", hourLabel: "19:00", passengers: 0, currentBuses: 0 },
          { hour: "20:00–21:00", hourLabel: "20:00", passengers: 0, currentBuses: 0 },
        ],
        buses: [
          { bus: "BUS-201", trip: "08:00", passengers: 59, capacity: 50 },
          { bus: "BUS-204", trip: "09:00", passengers: 48, capacity: 50 },
          { bus: "BUS-207", trip: "17:00", passengers: 52, capacity: 50 },
        ],
      },
      "17B": {
        route: "17B",
        corridor: "Metro Gate 4 ⇄ Outer Industrial Zone",
        busCapacity: 50,
        trips: 9,
        passengers: 381,
        capacity: 450,
        hourlySchedule: [
          { hour: "06:00–07:00", hourLabel: "06:00", passengers: 25, currentBuses: 1 },
          { hour: "07:00–08:00", hourLabel: "07:00", passengers: 44, currentBuses: 1 },
          { hour: "08:00–09:00", hourLabel: "08:00", passengers: 46, currentBuses: 1 },
          { hour: "09:00–10:00", hourLabel: "09:00", passengers: 42, currentBuses: 1 },
          { hour: "10:00–11:00", hourLabel: "10:00", passengers: 31, currentBuses: 1 },
          { hour: "11:00–12:00", hourLabel: "11:00", passengers: 27, currentBuses: 1 },
          { hour: "12:00–13:00", hourLabel: "12:00", passengers: 29, currentBuses: 1 },
          { hour: "13:00–14:00", hourLabel: "13:00", passengers: 32, currentBuses: 1 },
          { hour: "14:00–15:00", hourLabel: "14:00", passengers: 31, currentBuses: 1 },
          { hour: "15:00–16:00", hourLabel: "15:00", passengers: 35, currentBuses: 1 },
          { hour: "16:00–17:00", hourLabel: "16:00", passengers: 39, currentBuses: 0 },
          { hour: "17:00–18:00", hourLabel: "17:00", passengers: 0, currentBuses: 0 },
          { hour: "18:00–19:00", hourLabel: "18:00", passengers: 0, currentBuses: 0 },
          { hour: "19:00–20:00", hourLabel: "19:00", passengers: 0, currentBuses: 0 },
          { hour: "20:00–21:00", hourLabel: "20:00", passengers: 0, currentBuses: 0 },
        ],
        buses: [
          { bus: "BUS-301", trip: "08:00", passengers: 46, capacity: 50 },
          { bus: "BUS-305", trip: "14:00", passengers: 31, capacity: 50 },
        ],
      },
      "18D": {
        route: "18D",
        corridor: "Suburban Junction ⇄ Civic Center",
        busCapacity: 50,
        trips: 8,
        passengers: 290,
        capacity: 400,
        hourlySchedule: [
          { hour: "06:00–07:00", hourLabel: "06:00", passengers: 15, currentBuses: 1 },
          { hour: "07:00–08:00", hourLabel: "07:00", passengers: 36, currentBuses: 1 },
          { hour: "08:00–09:00", hourLabel: "08:00", passengers: 39, currentBuses: 1 },
          { hour: "09:00–10:00", hourLabel: "09:00", passengers: 35, currentBuses: 1 },
          { hour: "10:00–11:00", hourLabel: "10:00", passengers: 28, currentBuses: 1 },
          { hour: "11:00–12:00", hourLabel: "11:00", passengers: 24, currentBuses: 1 },
          { hour: "12:00–13:00", hourLabel: "12:00", passengers: 27, currentBuses: 1 },
          { hour: "13:00–14:00", hourLabel: "13:00", passengers: 29, currentBuses: 1 },
          { hour: "14:00–15:00", hourLabel: "14:00", passengers: 26, currentBuses: 0 },
          { hour: "15:00–16:00", hourLabel: "15:00", passengers: 31, currentBuses: 0 },
          { hour: "16:00–17:00", hourLabel: "16:00", passengers: 0, currentBuses: 0 },
          { hour: "17:00–18:00", hourLabel: "17:00", passengers: 0, currentBuses: 0 },
          { hour: "18:00–19:00", hourLabel: "18:00", passengers: 0, currentBuses: 0 },
          { hour: "19:00–20:00", hourLabel: "19:00", passengers: 0, currentBuses: 0 },
          { hour: "20:00–21:00", hourLabel: "20:00", passengers: 0, currentBuses: 0 },
        ],
        buses: [
          { bus: "BUS-401", trip: "08:00", passengers: 39, capacity: 50 },
          { bus: "BUS-403", trip: "12:00", passengers: 27, capacity: 50 },
        ],
      },
      "31K": {
        route: "31K",
        corridor: "North Interchange ⇄ Medical City",
        busCapacity: 50,
        trips: 10,
        passengers: 580,
        capacity: 500,
        hourlySchedule: [
          { hour: "06:00–07:00", hourLabel: "06:00", passengers: 20, currentBuses: 1 },
          { hour: "07:00–08:00", hourLabel: "07:00", passengers: 45, currentBuses: 1 },
          { hour: "08:00–09:00", hourLabel: "08:00", passengers: 75, currentBuses: 1 }, // 150%
          { hour: "09:00–10:00", hourLabel: "09:00", passengers: 62, currentBuses: 1 },
          { hour: "10:00–11:00", hourLabel: "10:00", passengers: 49, currentBuses: 1 },
          { hour: "11:00–12:00", hourLabel: "11:00", passengers: 38, currentBuses: 1 },
          { hour: "12:00–13:00", hourLabel: "12:00", passengers: 41, currentBuses: 1 },
          { hour: "13:00–14:00", hourLabel: "13:00", passengers: 37, currentBuses: 1 },
          { hour: "14:00–15:00", hourLabel: "14:00", passengers: 35, currentBuses: 1 },
          { hour: "15:00–16:00", hourLabel: "15:00", passengers: 43, currentBuses: 1 },
          { hour: "16:00–17:00", hourLabel: "16:00", passengers: 58, currentBuses: 0 },
          { hour: "17:00–18:00", hourLabel: "17:00", passengers: 77, currentBuses: 0 },
          { hour: "18:00–19:00", hourLabel: "18:00", passengers: 0, currentBuses: 0 },
          { hour: "19:00–20:00", hourLabel: "19:00", passengers: 0, currentBuses: 0 },
          { hour: "20:00–21:00", hourLabel: "20:00", passengers: 0, currentBuses: 0 },
        ],
        buses: [
          { bus: "BUS-501", trip: "08:00", passengers: 75, capacity: 50 },
          { bus: "BUS-503", trip: "09:00", passengers: 62, capacity: 50 },
        ],
      },
      "09X": {
        route: "09X",
        corridor: "Exhibition Grounds ⇄ Sports Complex (Weekend Only)",
        busCapacity: 50,
        trips: 0,
        passengers: 0,
        capacity: 0,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 0,
          currentBuses: 0,
        })),
        buses: [],
      },
    },
  },
  "2026-09-23": {
    label: "Yesterday (Sep 23, 2026)",
    kpis: {
      total_passengers: "11,890",
      total_trips: "182",
      avg_occupancy: "82%",
      peak_demand_hour: "08:00–09:00",
      overcapacity_trips: "11",
    },
    routes: {
      "25A": {
        route: "25A",
        corridor: "Central Railway Stn ⇄ Cyber Tech Park",
        busCapacity: 50,
        trips: 12,
        passengers: 590,
        capacity: 600,
        hourlySchedule: [
          { hour: "06:00–07:00", hourLabel: "06:00", passengers: 20, currentBuses: 1 },
          { hour: "07:00–08:00", hourLabel: "07:00", passengers: 42, currentBuses: 1 },
          { hour: "08:00–09:00", hourLabel: "08:00", passengers: 92, currentBuses: 1 }, // 184%
          { hour: "09:00–10:00", hourLabel: "09:00", passengers: 68, currentBuses: 1 },
          { hour: "10:00–11:00", hourLabel: "10:00", passengers: 38, currentBuses: 1 },
          { hour: "11:00–12:00", hourLabel: "11:00", passengers: 29, currentBuses: 1 },
          { hour: "12:00–13:00", hourLabel: "12:00", passengers: 35, currentBuses: 1 },
          { hour: "13:00–14:00", hourLabel: "13:00", passengers: 30, currentBuses: 1 },
          { hour: "14:00–15:00", hourLabel: "14:00", passengers: 28, currentBuses: 1 },
          { hour: "15:00–16:00", hourLabel: "15:00", passengers: 39, currentBuses: 1 },
          { hour: "16:00–17:00", hourLabel: "16:00", passengers: 51, currentBuses: 1 },
          { hour: "17:00–18:00", hourLabel: "17:00", passengers: 82, currentBuses: 1 },
          { hour: "18:00–19:00", hourLabel: "18:00", passengers: 22, currentBuses: 1 },
          { hour: "19:00–20:00", hourLabel: "19:00", passengers: 14, currentBuses: 0 },
          { hour: "20:00–21:00", hourLabel: "20:00", passengers: 0, currentBuses: 0 },
        ],
        buses: [
          { bus: "BUS-101", trip: "08:00", passengers: 44, capacity: 50 },
          { bus: "BUS-108", trip: "08:00", passengers: 92, capacity: 50 },
        ],
      },
      "42C": {
        route: "42C",
        corridor: "South Terminal ⇄ University Campus",
        busCapacity: 50,
        trips: 11,
        passengers: 485,
        capacity: 550,
        hourlySchedule: [
          { hour: "06:00–07:00", hourLabel: "06:00", passengers: 16, currentBuses: 1 },
          { hour: "07:00–08:00", hourLabel: "07:00", passengers: 35, currentBuses: 1 },
          { hour: "08:00–09:00", hourLabel: "08:00", passengers: 55, currentBuses: 1 },
          { hour: "09:00–10:00", hourLabel: "09:00", passengers: 45, currentBuses: 1 },
          { hour: "10:00–11:00", hourLabel: "10:00", passengers: 41, currentBuses: 1 },
          { hour: "11:00–12:00", hourLabel: "11:00", passengers: 30, currentBuses: 1 },
          { hour: "12:00–13:00", hourLabel: "12:00", passengers: 33, currentBuses: 1 },
          { hour: "13:00–14:00", hourLabel: "13:00", passengers: 28, currentBuses: 1 },
          { hour: "14:00–15:00", hourLabel: "14:00", passengers: 27, currentBuses: 1 },
          { hour: "15:00–16:00", hourLabel: "15:00", passengers: 40, currentBuses: 1 },
          { hour: "16:00–17:00", hourLabel: "16:00", passengers: 45, currentBuses: 1 },
          { hour: "17:00–18:00", hourLabel: "17:00", passengers: 49, currentBuses: 1 },
          { hour: "18:00–19:00", hourLabel: "18:00", passengers: 21, currentBuses: 0 },
          { hour: "19:00–20:00", hourLabel: "19:00", passengers: 0, currentBuses: 0 },
          { hour: "20:00–21:00", hourLabel: "20:00", passengers: 0, currentBuses: 0 },
        ],
        buses: [{ bus: "BUS-201", trip: "08:00", passengers: 55, capacity: 50 }],
      },
      "17B": {
        route: "17B",
        corridor: "Metro Gate 4 ⇄ Outer Industrial Zone",
        busCapacity: 50,
        trips: 9,
        passengers: 360,
        capacity: 450,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 24,
          currentBuses: 1,
        })),
        buses: [],
      },
      "18D": {
        route: "18D",
        corridor: "Suburban Junction ⇄ Civic Center",
        busCapacity: 50,
        trips: 8,
        passengers: 280,
        capacity: 400,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 18,
          currentBuses: 1,
        })),
        buses: [],
      },
      "31K": {
        route: "31K",
        corridor: "North Interchange ⇄ Medical City",
        busCapacity: 50,
        trips: 10,
        passengers: 550,
        capacity: 500,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 36,
          currentBuses: 1,
        })),
        buses: [],
      },
      "09X": {
        route: "09X",
        corridor: "Exhibition Grounds ⇄ Sports Complex (Weekend Only)",
        busCapacity: 50,
        trips: 0,
        passengers: 0,
        capacity: 0,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 0,
          currentBuses: 0,
        })),
        buses: [],
      },
    },
  },
  "2026-09-22": {
    label: "2 Days Ago (Sep 22, 2026)",
    kpis: {
      total_passengers: "13,110",
      total_trips: "190",
      avg_occupancy: "91%",
      peak_demand_hour: "08:00–09:00",
      overcapacity_trips: "18",
    },
    routes: {
      "25A": {
        route: "25A",
        corridor: "Central Railway Stn ⇄ Cyber Tech Park",
        busCapacity: 50,
        trips: 12,
        passengers: 690,
        capacity: 600,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: h.includes("08:00") ? 105 : 42,
          currentBuses: 1,
        })),
        buses: [{ bus: "BUS-108", trip: "08:00", passengers: 105, capacity: 50 }],
      },
      "42C": {
        route: "42C",
        corridor: "South Terminal ⇄ University Campus",
        busCapacity: 50,
        trips: 11,
        passengers: 540,
        capacity: 550,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 36,
          currentBuses: 1,
        })),
        buses: [],
      },
      "17B": {
        route: "17B",
        corridor: "Metro Gate 4 ⇄ Outer Industrial Zone",
        busCapacity: 50,
        trips: 9,
        passengers: 405,
        capacity: 450,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 27,
          currentBuses: 1,
        })),
        buses: [],
      },
      "18D": {
        route: "18D",
        corridor: "Suburban Junction ⇄ Civic Center",
        busCapacity: 50,
        trips: 8,
        passengers: 310,
        capacity: 400,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 20,
          currentBuses: 1,
        })),
        buses: [],
      },
      "31K": {
        route: "31K",
        corridor: "North Interchange ⇄ Medical City",
        busCapacity: 50,
        trips: 10,
        passengers: 610,
        capacity: 500,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: h.includes("08:00") ? 82 : 38,
          currentBuses: 1,
        })),
        buses: [],
      },
      "09X": {
        route: "09X",
        corridor: "Exhibition Grounds ⇄ Sports Complex (Weekend Only)",
        busCapacity: 50,
        trips: 0,
        passengers: 0,
        capacity: 0,
        hourlySchedule: OPERATING_HOURS.map((h) => ({
          hour: h,
          hourLabel: h.slice(0, 5),
          passengers: 0,
          currentBuses: 0,
        })),
        buses: [],
      },
    },
  },
};

export default function PassengerDemandPage() {
  // Date selection state with persistence/archive lookup
  const [selectedDate, setSelectedDate] = useState("2026-09-24");

  // Navigation & Filtering State
  const [selectedDemandGroup, setSelectedDemandGroup] = useState(null);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [expandedBusView, setExpandedBusView] = useState(true);

  // Active date's dataset
  const activeDateRecord = DATE_ARCHIVE_STORAGE[selectedDate] || DATE_ARCHIVE_STORAGE["2026-09-24"];
  const activeRouteDatabase = activeDateRecord.routes;

  // Compute all routes for the selected date with dynamic occupancy & classification
  const allRoutesList = Object.values(activeRouteDatabase).map((r) => {
    const occupancy = calculateOccupancy(r.passengers, r.capacity);
    const status = getDemandStatus(r.passengers, r.capacity);
    return {
      ...r,
      occupancy,
      status,
    };
  });

  // Calculate Demand Group Counts dynamically for the active date
  const demandGroupCounts = {
    "NO DEMAND": allRoutesList.filter((r) => r.status === "NO DEMAND").length,
    NORMAL: allRoutesList.filter((r) => r.status === "NORMAL").length,
    "HIGH DEMAND": allRoutesList.filter((r) => r.status === "HIGH DEMAND").length,
    OVERCAPACITY: allRoutesList.filter((r) => r.status === "OVERCAPACITY").length,
  };

  // Filter routes based on selectedDemandGroup
  const visibleRoutes = selectedDemandGroup
    ? allRoutesList.filter((r) => r.status === selectedDemandGroup)
    : allRoutesList;

  // Selected route data object for active date
  const activeRouteData = selectedRoute ? activeRouteDatabase[selectedRoute] : null;

  // Compute hourly breakdown metrics for the selected route
  const routeHourlyAnalysis = activeRouteData
    ? activeRouteData.hourlySchedule.map((slot) => {
        const busCap = activeRouteData.busCapacity || 50;
        const totalHourCap = (slot.currentBuses || 0) * busCap;
        const hourlyOccupancy =
          slot.currentBuses > 0
            ? calculateOccupancy(slot.passengers, totalHourCap)
            : slot.passengers > 0
            ? calculateOccupancy(slot.passengers, busCap)
            : 0;
        const { requiredBuses, additionalBuses } = calculateBusRequirement(
          slot.passengers,
          busCap,
          slot.currentBuses
        );
        const hourStatus = getDemandStatus(
          slot.passengers,
          slot.currentBuses > 0 ? totalHourCap : busCap
        );

        return {
          ...slot,
          busCap,
          hourlyOccupancy,
          requiredBuses,
          additionalBuses,
          hourStatus,
        };
      })
    : [];

  // High-demand & Overcapacity periods for the selected route
  const routeHighDemandPeriods = routeHourlyAnalysis.filter(
    (slot) => slot.hourlyOccupancy >= 80 && slot.passengers > 0
  );

  // Recommendations for the selected route
  const routeRecommendations = routeHighDemandPeriods.map((slot) => {
    let actionText = "";
    let recommendationType = "";
    let badgeColor = "#059669";

    if (slot.additionalBuses > 0) {
      actionText = `Increase service frequency during ${slot.hour} by ${slot.additionalBuses} bus${
        slot.additionalBuses > 1 ? "es" : ""
      }.`;
      recommendationType = "Increase service frequency";
      badgeColor = "#DC2626";
    } else if (slot.hourlyOccupancy >= 80 && slot.hourlyOccupancy <= 100) {
      actionText = `Consider additional service during this peak window (${slot.hour}).`;
      recommendationType = "Consider additional service";
      badgeColor = "#D97706";
    } else {
      actionText = "No additional service indicated.";
      recommendationType = "No additional service indicated";
      badgeColor = "#059669";
    }

    return {
      hour: slot.hour,
      passengers: slot.passengers,
      currentBuses: slot.currentBuses,
      requiredBuses: slot.requiredBuses,
      additionalBuses: slot.additionalBuses,
      occupancy: slot.hourlyOccupancy,
      actionText,
      recommendationType,
      badgeColor,
    };
  });

  // KPI Card values derived from the active date record
  const kpis = [
    {
      id: "total_passengers",
      title: "TOTAL PASSENGERS",
      value: activeDateRecord.kpis.total_passengers,
      subtext: `Ridership on ${selectedDate}`,
      icon: "👥",
      badge: selectedDate === "2026-09-24" ? "LIVE TELEMETRY" : "HISTORICAL ARCHIVE",
      badgeColor: "rgba(14, 165, 233, 0.12)",
      textColor: "var(--text-bright)",
    },
    {
      id: "total_trips",
      title: "TOTAL TRIPS",
      value: activeDateRecord.kpis.total_trips,
      subtext: "Operated across monitored routes",
      icon: "🚌",
      badge: "SCHEDULED & DISPATCHED",
      badgeColor: "rgba(99, 102, 241, 0.12)",
      textColor: "var(--text-bright)",
    },
    {
      id: "avg_occupancy",
      title: "AVERAGE OCCUPANCY",
      value: activeDateRecord.kpis.avg_occupancy,
      subtext: "Corridor aggregate load factor",
      icon: "📊",
      badge: parseInt(activeDateRecord.kpis.avg_occupancy) >= 85 ? "ELEVATED" : "BALANCED",
      badgeColor: "rgba(245, 158, 11, 0.12)",
      textColor: "#B45309",
    },
    {
      id: "peak_demand_hour",
      title: "PEAK DEMAND HOUR",
      value: activeDateRecord.kpis.peak_demand_hour,
      subtext: "Highest hourly corridor volume",
      icon: "⏰",
      badge: "SURGE WINDOW",
      badgeColor: "rgba(239, 68, 68, 0.12)",
      textColor: "#DC2626",
    },
    {
      id: "overcapacity_trips",
      title: "OVERCAPACITY TRIPS",
      value: activeDateRecord.kpis.overcapacity_trips,
      subtext: "Trips operating over 100% capacity",
      icon: "⚠️",
      badge: "REQUIRES AUGMENTATION",
      badgeColor: "rgba(239, 68, 68, 0.15)",
      textColor: "#EF4444",
    },
  ];

  // Helper for occupancy color
  const getOccupancyColor = (pct) => {
    if (pct >= 150) return "#DC2626";
    if (pct > 100) return "#EF4444";
    if (pct >= 80) return "#F59E0B";
    if (pct === 0) return "var(--muted)";
    return "#10B981";
  };

  // Helper for Demand Status card style
  const getGroupCardBorder = (groupName) => {
    const isSelected = selectedDemandGroup === groupName;
    if (isSelected) {
      if (groupName === "OVERCAPACITY") return "2px solid #EF4444";
      if (groupName === "HIGH DEMAND") return "2px solid #F59E0B";
      if (groupName === "NORMAL") return "2px solid #10B981";
      return "2px solid var(--text-bright)";
    }
    return "1px solid var(--line)";
  };

  return (
    <div className="page-container page-fade-enter">
      {/* ====================================================================
          HEADER WITH DATE-WISE RECORD SELECTOR
          ==================================================================== */}
      <div className="page-header-row" style={{ marginBottom: "20px", flexWrap: "wrap", gap: "16px" }}>
        <div className="page-header-text">
          <h1>Passenger Demand &amp; Service Intelligence</h1>
          <p>
            Monitor passenger demand, occupancy and service requirements across routes with date-wise historical storage.
          </p>
        </div>

        {/* Date Selector & Storage Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "#FFFFFF",
              border: "1px solid var(--line)",
              padding: "4px 12px",
              borderRadius: "var(--radius-full)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <span style={{ fontSize: "14px" }}>📅</span>
            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
              DATE:
            </span>
            <select
              value={selectedDate}
              onChange={(e) => {
                setSelectedDate(e.target.value);
                setSelectedRoute(null);
                setSelectedDemandGroup(null);
              }}
              style={{
                border: "none",
                background: "transparent",
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                fontWeight: 700,
                color: "var(--text-bright)",
                cursor: "pointer",
                outline: "none",
                padding: "2px 4px",
              }}
            >
              <option value="2026-09-24">Today — Sep 24, 2026</option>
              <option value="2026-09-23">Yesterday — Sep 23, 2026</option>
              <option value="2026-09-22">Archive — Sep 22, 2026</option>
            </select>
          </div>

          <div className="page-header-badges">
            <span className="badge badge-info">
              <span className="pulse-dot green" style={{ width: "6px", height: "6px" }} />
              {selectedDate === "2026-09-24" ? "LIVE TELEMETRY" : "ARCHIVE RECORD"}
            </span>
            <span className="badge badge-neutral">STORED IN DB</span>
          </div>
        </div>
      </div>

      {/* ====================================================================
          VIEW SWITCHING:
          1. SELECTED ROUTE VIEW (Deep-dive detail analysis)
          2. INITIAL MAIN DASHBOARD (High-level overview)
          ==================================================================== */}
      {selectedRoute && activeRouteData ? (
        /* ==================================================================
           7. ROUTE DETAIL VIEW (For Selected Route Only)
           ================================================================== */
        <div>
          {/* Back button */}
          <div style={{ marginBottom: "20px" }}>
            <button
              className="button button-secondary"
              onClick={() => {
                setSelectedRoute(null);
                setSelectedDemandGroup(null);
              }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                fontWeight: 600,
                padding: "8px 18px",
              }}
            >
              <span>← Back to All Routes</span>
            </button>
          </div>

          {/* Route Identification Title Banner */}
          <div
            className="panel"
            style={{
              padding: "20px 24px",
              marginBottom: "24px",
              background: "var(--panel-bg)",
              border: "1px solid var(--line)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "4px" }}>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "20px",
                      fontWeight: 800,
                      padding: "4px 12px",
                      borderRadius: "var(--radius-sm)",
                      background: "rgba(14, 165, 233, 0.12)",
                      color: "#0369A1",
                      border: "1px solid rgba(14, 165, 233, 0.3)",
                    }}
                  >
                    Route {activeRouteData.route}
                  </span>
                  <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "var(--text-bright)" }}>
                    {activeRouteData.corridor}
                  </h2>
                </div>
                <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>
                  Corridor-specific intelligence: hour-by-hour ridership, uncapped load factors, and tactical bus dispatch recommendations.
                </p>
              </div>

              <span
                className={`badge ${getStatusTheme(activeRouteData.status).badgeClass}`}
                style={{ fontSize: "12px", padding: "6px 12px" }}
              >
                {activeRouteData.status}
              </span>
            </div>
          </div>

          {/* 7. ROUTE SUMMARY KPI CARDS */}
          {(() => {
            const occ = calculateOccupancy(activeRouteData.passengers, activeRouteData.capacity);
            const excess = Math.max(0, activeRouteData.passengers - activeRouteData.capacity);
            const { requiredBuses, additionalBuses } = calculateBusRequirement(
              activeRouteData.passengers,
              activeRouteData.busCapacity,
              activeRouteData.trips
            );

            return (
              <div
                className="metric-grid"
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "14px",
                  marginBottom: "28px",
                }}
              >
                {/* Total Passengers */}
                <Interactive3DCard className="metric-card">
                  <div className="metric-header">
                    <span className="metric-title">TOTAL PASSENGERS</span>
                    <span className="metric-icon">👥</span>
                  </div>
                  <div className="metric-value-row">
                    <div className="metric-value">{activeRouteData.passengers.toLocaleString()}</div>
                  </div>
                  <div className="metric-footer"><span>Total boardings observed</span></div>
                </Interactive3DCard>

                {/* Current Buses / Trips */}
                <Interactive3DCard className="metric-card">
                  <div className="metric-header">
                    <span className="metric-title">CURRENT BUSES / TRIPS</span>
                    <span className="metric-icon">🚌</span>
                  </div>
                  <div className="metric-value-row">
                    <div className="metric-value">{activeRouteData.trips}</div>
                  </div>
                  <div className="metric-footer"><span>Scheduled operations</span></div>
                </Interactive3DCard>

                {/* Bus Capacity */}
                <Interactive3DCard className="metric-card">
                  <div className="metric-header">
                    <span className="metric-title">BUS CAPACITY</span>
                    <span className="metric-icon">💺</span>
                  </div>
                  <div className="metric-value-row">
                    <div className="metric-value">{activeRouteData.busCapacity}</div>
                  </div>
                  <div className="metric-footer"><span>Nominal seats/bus</span></div>
                </Interactive3DCard>

                {/* Total Available Capacity */}
                <Interactive3DCard className="metric-card">
                  <div className="metric-header">
                    <span className="metric-title">TOTAL CAPACITY</span>
                    <span className="metric-icon">📊</span>
                  </div>
                  <div className="metric-value-row">
                    <div className="metric-value">{activeRouteData.capacity.toLocaleString()}</div>
                  </div>
                  <div className="metric-footer"><span>Fleet seat aggregate</span></div>
                </Interactive3DCard>

                {/* Occupancy (Uncapped) */}
                <Interactive3DCard className="metric-card">
                  <div className="metric-header">
                    <span className="metric-title">OCCUPANCY</span>
                    <span className="metric-icon">⚡</span>
                  </div>
                  <div className="metric-value-row">
                    <div className="metric-value" style={{ color: getOccupancyColor(occ) }}>
                      {occ}%
                    </div>
                  </div>
                  <div className="metric-footer"><span>Uncapped load factor</span></div>
                </Interactive3DCard>

                {/* Capacity Excess */}
                <Interactive3DCard className="metric-card">
                  <div className="metric-header">
                    <span className="metric-title">CAPACITY EXCESS</span>
                    <span className="metric-icon">⚠️</span>
                  </div>
                  <div className="metric-value-row">
                    <div className="metric-value" style={{ color: excess > 0 ? "#DC2626" : "#059669" }}>
                      {excess > 0 ? `+${excess}` : "0"}
                    </div>
                  </div>
                  <div className="metric-footer"><span>Passengers above capacity</span></div>
                </Interactive3DCard>
              </div>
            );
          })()}

          {/* 11 & 12. ROUTE-SPECIFIC PASSENGER DEMAND & OCCUPANCY GRAPHS */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))",
              gap: "24px",
              marginBottom: "28px",
            }}
          >
            {/* 11. Route-Specific Passenger Demand Graph */}
            <div className="panel" style={{ margin: 0 }}>
              <div className="panel-header">
                <div className="panel-title-group">
                  <h2>Passenger Demand by Hour — Route {activeRouteData.route}</h2>
                  <p>Hourly passenger ridership volume (Route {activeRouteData.route} only).</p>
                </div>
              </div>
              <div className="panel-body" style={{ padding: "20px 24px" }}>
                {(() => {
                  const maxSlot = Math.max(
                    ...activeRouteData.hourlySchedule.map((s) => s.passengers),
                    1
                  );
                  return (
                    <div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: `repeat(${activeRouteData.hourlySchedule.length}, 1fr)`,
                          gap: "6px",
                          alignItems: "flex-end",
                          height: "170px",
                          borderBottom: "1px solid var(--line)",
                          paddingBottom: "8px",
                        }}
                      >
                        {activeRouteData.hourlySchedule.map((s) => {
                          const heightPct = Math.max(
                            8,
                            Math.round((s.passengers / maxSlot) * 100)
                          );
                          const isSurge = s.passengers >= 70;
                          return (
                            <div
                              key={s.hour}
                              title={`${s.hour}: ${s.passengers} passengers`}
                              style={{
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                height: "100%",
                                justifyContent: "flex-end",
                              }}
                            >
                              <span
                                style={{
                                  fontSize: "10px",
                                  fontFamily: "var(--font-mono)",
                                  fontWeight: isSurge ? 700 : 500,
                                  color: isSurge ? "#DC2626" : "var(--muted)",
                                  marginBottom: "4px",
                                }}
                              >
                                {s.passengers > 0 ? s.passengers : ""}
                              </span>
                              <div
                                style={{
                                  width: "100%",
                                  maxWidth: "32px",
                                  height: `${heightPct}%`,
                                  background: isSurge
                                    ? "linear-gradient(180deg, #EF4444 0%, #DC2626 100%)"
                                    : "linear-gradient(180deg, #38BDF8 0%, #0EA5E9 100%)",
                                  borderRadius: "4px 4px 0 0",
                                }}
                              />
                            </div>
                          );
                        })}
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: `repeat(${activeRouteData.hourlySchedule.length}, 1fr)`,
                          gap: "6px",
                          marginTop: "8px",
                        }}
                      >
                        {activeRouteData.hourlySchedule.map((s) => (
                          <div
                            key={s.hour}
                            style={{
                              textAlign: "center",
                              fontSize: "9.5px",
                              fontFamily: "var(--font-mono)",
                              color: "var(--muted)",
                            }}
                          >
                            {s.hourLabel}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* 12. Route-Specific Occupancy Graph (UNCAPPED - 100%, 150%, 200%) */}
            <div className="panel" style={{ margin: 0 }}>
              <div className="panel-header">
                <div className="panel-title-group">
                  <h2>Occupancy by Hour — Route {activeRouteData.route}</h2>
                  <p>Uncapped load factor across the day (displays actual 150%, 200%).</p>
                </div>
                <span
                  style={{
                    fontSize: "10.5px",
                    fontFamily: "var(--font-mono)",
                    background: "rgba(239, 68, 68, 0.1)",
                    color: "#DC2626",
                    padding: "3px 8px",
                    borderRadius: "4px",
                    fontWeight: 700,
                  }}
                >
                  PEAK: 200%
                </span>
              </div>
              <div className="panel-body" style={{ padding: "20px 24px" }}>
                {(() => {
                  const maxOcc = Math.max(
                    ...routeHourlyAnalysis.map((s) => s.hourlyOccupancy),
                    200
                  );
                  return (
                    <div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: `repeat(${routeHourlyAnalysis.length}, 1fr)`,
                          gap: "6px",
                          alignItems: "flex-end",
                          height: "170px",
                          borderBottom: "1px solid var(--line)",
                          paddingBottom: "8px",
                          position: "relative",
                        }}
                      >
                        {/* 100% Threshold Guideline */}
                        <div
                          style={{
                            position: "absolute",
                            bottom: `${(100 / maxOcc) * 100}%`,
                            left: 0,
                            right: 0,
                            borderTop: "1px dashed rgba(239, 68, 68, 0.4)",
                            pointerEvents: "none",
                          }}
                        >
                          <span
                            style={{
                              position: "absolute",
                              right: 2,
                              top: -8,
                              fontSize: "9px",
                              fontFamily: "var(--font-mono)",
                              color: "#DC2626",
                              fontWeight: 700,
                              background: "var(--panel-bg)",
                              padding: "0 4px",
                            }}
                          >
                            100% CAPACITY
                          </span>
                        </div>

                        {routeHourlyAnalysis.map((s) => {
                          const heightPct = Math.max(
                            8,
                            Math.round((s.hourlyOccupancy / maxOcc) * 100)
                          );
                          const isCritical = s.hourlyOccupancy > 100;
                          return (
                            <div
                              key={s.hour}
                              title={`${s.hour}: Occupancy ${s.hourlyOccupancy}%`}
                              style={{
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                                height: "100%",
                                justifyContent: "flex-end",
                              }}
                            >
                              <span
                                style={{
                                  fontSize: "10px",
                                  fontFamily: "var(--font-mono)",
                                  fontWeight: 700,
                                  color: getOccupancyColor(s.hourlyOccupancy),
                                  marginBottom: "4px",
                                }}
                              >
                                {s.hourlyOccupancy > 0 ? `${s.hourlyOccupancy}%` : ""}
                              </span>
                              <div
                                style={{
                                  width: "100%",
                                  maxWidth: "32px",
                                  height: `${heightPct}%`,
                                  background: isCritical
                                    ? "linear-gradient(180deg, #EF4444 0%, #B91C1C 100%)"
                                    : s.hourlyOccupancy >= 80
                                    ? "linear-gradient(180deg, #F59E0B 0%, #D97706 100%)"
                                    : "linear-gradient(180deg, #10B981 0%, #059669 100%)",
                                  borderRadius: "4px 4px 0 0",
                                }}
                              />
                            </div>
                          );
                        })}
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: `repeat(${routeHourlyAnalysis.length}, 1fr)`,
                          gap: "6px",
                          marginTop: "8px",
                        }}
                      >
                        {routeHourlyAnalysis.map((s) => (
                          <div
                            key={s.hour}
                            style={{
                              textAlign: "center",
                              fontSize: "9.5px",
                              fontFamily: "var(--font-mono)",
                              color: "var(--muted)",
                            }}
                          >
                            {s.hourLabel}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>

          {/* 10. BUS REQUIREMENT BY HOUR TABLE */}
          <div className="panel" style={{ marginBottom: "28px" }}>
            <div className="panel-header">
              <div className="panel-title-group">
                <h2>Bus Requirement by Hour — Route {activeRouteData.route}</h2>
                <p>
                  Time-specific capacity analysis: Required buses calculated with Math.ceil(passengers ÷ busCapacity). Additional buses required highlighted.
                </p>
              </div>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table className="event-table">
                <thead>
                  <tr>
                    <th style={{ width: "16%" }}>Hour</th>
                    <th style={{ width: "14%", textAlign: "center" }}>Passengers</th>
                    <th style={{ width: "14%", textAlign: "center" }}>Current Buses</th>
                    <th style={{ width: "14%", textAlign: "center" }}>Capacity / Bus</th>
                    <th style={{ width: "14%", textAlign: "center" }}>Occupancy</th>
                    <th style={{ width: "14%", textAlign: "center" }}>Required Buses</th>
                    <th style={{ width: "14%", textAlign: "center" }}>Additional Buses</th>
                  </tr>
                </thead>
                <tbody>
                  {routeHourlyAnalysis.map((row) => {
                    const isAddNeeded = row.additionalBuses > 0;
                    return (
                      <tr
                        key={row.hour}
                        style={{
                          background: isAddNeeded ? "rgba(239, 68, 68, 0.03)" : "transparent",
                        }}
                      >
                        <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                          {row.hour}
                        </td>
                        <td style={{ textAlign: "center", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                          {row.passengers}
                        </td>
                        <td style={{ textAlign: "center", fontFamily: "var(--font-mono)" }}>
                          {row.currentBuses}
                        </td>
                        <td style={{ textAlign: "center", fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                          {row.busCap}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "13.5px",
                              fontWeight: 700,
                              color: getOccupancyColor(row.hourlyOccupancy),
                            }}
                          >
                            {row.hourlyOccupancy}%
                          </span>
                        </td>
                        <td style={{ textAlign: "center", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                          {row.requiredBuses}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          {isAddNeeded ? (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                background: "#DC2626",
                                color: "#FFFFFF",
                                padding: "2px 8px",
                                borderRadius: "var(--radius-full)",
                                fontFamily: "var(--font-mono)",
                                fontSize: "12px",
                                fontWeight: 700,
                              }}
                            >
                              +{row.additionalBuses} BUS{row.additionalBuses > 1 ? "ES" : ""}
                            </span>
                          ) : (
                            <span style={{ fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                              0
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 13 & 14. HIGH-DEMAND PERIODS & SERVICE RECOMMENDATIONS (Route-specific) */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))",
              gap: "24px",
              marginBottom: "28px",
            }}
          >
            {/* 13. HIGH-DEMAND PERIODS */}
            <div className="panel" style={{ margin: 0 }}>
              <div className="panel-header">
                <div className="panel-title-group">
                  <h2>High-Demand Periods — Route {activeRouteData.route}</h2>
                  <p>Operating intervals where occupancy ≥ 80% on this route.</p>
                </div>
                <span
                  style={{
                    fontSize: "11px",
                    fontFamily: "var(--font-mono)",
                    background: "rgba(239, 68, 68, 0.1)",
                    color: "#DC2626",
                    padding: "3px 8px",
                    borderRadius: "var(--radius-full)",
                    fontWeight: 700,
                  }}
                >
                  {routeHighDemandPeriods.length} INTERVAL{routeHighDemandPeriods.length !== 1 ? "S" : ""}
                </span>
              </div>

              <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {routeHighDemandPeriods.length === 0 ? (
                  <div style={{ padding: "24px", textAlign: "center", color: "var(--muted)" }}>
                    No high-demand or overcapacity intervals recorded on Route {activeRouteData.route}.
                  </div>
                ) : (
                  routeHighDemandPeriods.map((period, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: period.hourlyOccupancy > 100 ? "rgba(239, 68, 68, 0.05)" : "rgba(245, 158, 11, 0.05)",
                        border: `1px solid ${period.hourlyOccupancy > 100 ? "rgba(239, 68, 68, 0.25)" : "rgba(245, 158, 11, 0.25)"}`,
                        borderRadius: "var(--radius-lg)",
                        padding: "16px 18px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "14px", color: "var(--text-bright)" }}>
                            {period.hour}
                          </span>
                        </div>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "var(--radius-full)",
                            background: period.hourlyOccupancy > 100 ? "#DC2626" : "#D97706",
                            color: "#FFFFFF",
                          }}
                        >
                          {period.hourlyOccupancy > 100 ? "CAPACITY EXCEEDED" : "HIGH DEMAND"}
                        </span>
                      </div>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(auto-fit, minmax(80px, 1fr))",
                          gap: "8px",
                          background: "#FFFFFF",
                          border: "1px solid var(--line)",
                          borderRadius: "var(--radius-md)",
                          padding: "10px 12px",
                        }}
                      >
                        <div>
                          <div style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase" }}>Passengers</div>
                          <div style={{ fontSize: "15px", fontWeight: 700, color: "#111111" }}>{period.passengers}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase" }}>Current Buses</div>
                          <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--muted)" }}>{period.currentBuses}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase" }}>Capacity</div>
                          <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--muted)" }}>{period.busCap}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase" }}>Occupancy</div>
                          <div style={{ fontSize: "16px", fontWeight: 800, fontFamily: "var(--font-mono)", color: getOccupancyColor(period.hourlyOccupancy) }}>
                            {period.hourlyOccupancy}%
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase" }}>Required</div>
                          <div style={{ fontSize: "15px", fontWeight: 700, color: "#111111" }}>{period.requiredBuses}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase" }}>Additional</div>
                          <div style={{ fontSize: "15px", fontWeight: 800, color: period.additionalBuses > 0 ? "#DC2626" : "var(--muted)" }}>
                            {period.additionalBuses > 0 ? `+${period.additionalBuses}` : "0"}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* 14. SERVICE RECOMMENDATIONS (Route-specific decision-support) */}
            <div className="panel" style={{ margin: 0 }}>
              <div className="panel-header">
                <div className="panel-title-group">
                  <h2>Service Recommendation — Route {activeRouteData.route}</h2>
                  <p>Advisory headway decisions for Route {activeRouteData.route}.</p>
                </div>
                <span
                  style={{
                    fontSize: "11px",
                    background: "rgba(16, 185, 129, 0.12)",
                    color: "#059669",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                    padding: "3px 8px",
                    borderRadius: "var(--radius-full)",
                    fontWeight: 600,
                  }}
                >
                  DECISION-SUPPORT ONLY
                </span>
              </div>

              <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {routeRecommendations.length === 0 ? (
                  <div
                    style={{
                      padding: "20px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--line)",
                      background: "rgba(16, 185, 129, 0.05)",
                      borderLeft: "4px solid #10B981",
                    }}
                  >
                    <div style={{ fontWeight: 700, color: "#059669", marginBottom: "4px" }}>
                      No additional service indicated.
                    </div>
                    <div style={{ fontSize: "12.5px", color: "var(--muted)" }}>
                      Current fleet allocation satisfies transit demand across all scheduled intervals.
                    </div>
                  </div>
                ) : (
                  routeRecommendations.map((rec, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "16px 18px",
                        borderRadius: "var(--radius-lg)",
                        border: "1px solid var(--line)",
                        borderLeft: `4px solid ${rec.badgeColor}`,
                        background:
                          rec.recommendationType === "Increase service frequency"
                            ? "rgba(254, 242, 242, 0.6)"
                            : "rgba(255, 251, 235, 0.6)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "13.5px" }}>
                          Route {activeRouteData.route} ({rec.hour})
                        </span>
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "12.5px",
                            fontWeight: 700,
                            color: getOccupancyColor(rec.occupancy),
                          }}
                        >
                          Occupancy: {rec.occupancy}%
                        </span>
                      </div>

                      <div style={{ fontSize: "12px", color: "var(--muted)", marginBottom: "8px" }}>
                        Demand: <strong>{rec.passengers} pax</strong> | Current: <strong>{rec.currentBuses} bus</strong> | Required: <strong>{rec.requiredBuses} buses</strong> | Additional Required: <strong style={{ color: rec.additionalBuses > 0 ? "#DC2626" : "inherit" }}>{rec.additionalBuses}</strong>
                      </div>

                      <div
                        style={{
                          background: "#FFFFFF",
                          border: "1px solid var(--line)",
                          borderRadius: "var(--radius-md)",
                          padding: "10px 12px",
                        }}
                      >
                        <div style={{ fontSize: "10.5px", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase" }}>
                          Recommendation:
                        </div>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: rec.badgeColor, marginTop: "2px" }}>
                          "{rec.actionText}"
                        </div>
                      </div>
                    </div>
                  ))
                )}

                <div
                  style={{
                    fontSize: "11.5px",
                    color: "var(--muted)",
                    background: "var(--section-bg)",
                    border: "1px solid var(--line)",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  ℹ️ <strong>Supervisory Discretion:</strong> The system provides tactical decision recommendations only. No automated bus dispatches are issued.
                </div>
              </div>
            </div>
          </div>

          {/* 15. BUS / TRIP DETAILS (Supporting details for Route 25A) */}
          <div className="panel" style={{ marginBottom: "20px" }}>
            <div className="panel-header">
              <div className="panel-title-group">
                <h2>Bus / Trip Details — Route {activeRouteData.route}</h2>
                <p>Supporting operational bus logs operating on Route {activeRouteData.route}.</p>
              </div>
              <button
                className="button button-secondary button-sm"
                onClick={() => setExpandedBusView(!expandedBusView)}
              >
                {expandedBusView ? "Hide Detailed Logs ▲" : "View Trip Breakdown ▼"}
              </button>
            </div>

            {expandedBusView && (
              <div style={{ overflowX: "auto" }}>
                <table className="event-table">
                  <thead>
                    <tr>
                      <th style={{ width: "20%" }}>Bus ID</th>
                      <th style={{ width: "20%" }}>Trip Time</th>
                      <th style={{ width: "20%", textAlign: "center" }}>Passengers</th>
                      <th style={{ width: "20%", textAlign: "center" }}>Capacity</th>
                      <th style={{ width: "20%", textAlign: "center" }}>Occupancy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeRouteData.buses.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: "center", padding: "24px", color: "var(--muted)" }}>
                          No specific bus unit logs recorded for Route {activeRouteData.route}.
                        </td>
                      </tr>
                    ) : (
                      activeRouteData.buses.map((b, idx) => {
                        const busOcc = calculateOccupancy(b.passengers, b.capacity);
                        return (
                          <tr key={idx}>
                            <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                              {b.bus}
                            </td>
                            <td style={{ fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                              {b.trip}
                            </td>
                            <td style={{ textAlign: "center", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                              {b.passengers}
                            </td>
                            <td style={{ textAlign: "center", fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                              {b.capacity}
                            </td>
                            <td style={{ textAlign: "center" }}>
                              <span
                                style={{
                                  fontFamily: "var(--font-mono)",
                                  fontSize: "13px",
                                  fontWeight: 700,
                                  color: getOccupancyColor(busOcc),
                                  padding: "2px 8px",
                                  borderRadius: "var(--radius-full)",
                                  background: busOcc >= 200 ? "rgba(220, 38, 38, 0.12)" : "var(--section-bg)",
                                }}
                              >
                                {busOcc}%
                              </span>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ==================================================================
           INITIAL MAIN DASHBOARD (When no route is selected)
           ================================================================== */
        <div>
          {/* 1. KPI CARDS (Redesigned & Cleanly Spaced) */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
              gap: "12px",
              marginBottom: "20px",
            }}
          >
            {kpis.map((kpi) => (
              <Interactive3DCard
                key={kpi.id}
                className="metric-card"
                style={{
                  minHeight: "92px",
                  padding: "12px 14px",
                  borderRadius: "var(--radius-lg)",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                {/* Header: Title + Icon */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px" }}>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      letterSpacing: "0.06em",
                      color: "var(--muted)",
                      textTransform: "uppercase",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                    title={kpi.title}
                  >
                    {kpi.title}
                  </span>
                  <span style={{ fontSize: "14px", flexShrink: 0 }}>{kpi.icon}</span>
                </div>

                {/* Primary Metric Value */}
                <div
                  style={{
                    color: kpi.textColor,
                    fontSize: kpi.value.length > 8 ? "19px" : "24px",
                    fontWeight: 800,
                    letterSpacing: "-0.03em",
                    lineHeight: 1.1,
                    margin: "3px 0 2px",
                  }}
                >
                  {kpi.value}
                </div>

                {/* Footer: Micro-badge and short contextual descriptor */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px" }}>
                  <span
                    style={{
                      fontSize: "9px",
                      fontWeight: 700,
                      letterSpacing: "0.03em",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      background: kpi.badgeColor,
                      color: kpi.textColor === "var(--text-bright)" ? "var(--muted)" : kpi.textColor,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {kpi.badge}
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      color: "var(--muted)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      textAlign: "right",
                    }}
                    title={kpi.subtext}
                  >
                    {kpi.subtext}
                  </span>
                </div>
              </Interactive3DCard>
            ))}
          </div>

          {/* 1 & 5. DEMAND STATUS OVERVIEW (Redesigned Non-Congested Category Cards) */}
          <div style={{ marginBottom: "22px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <div>
                <h2 style={{ fontSize: "15px", fontWeight: 700, color: "var(--text-bright)", margin: "0 0 2px 0" }}>
                  Demand Status Overview
                </h2>
                <p style={{ fontSize: "12px", color: "var(--muted)", margin: 0 }}>
                  Click any category to filter the route table below.
                </p>
              </div>

              {selectedDemandGroup && (
                <button
                  className="button button-secondary button-sm"
                  onClick={() => setSelectedDemandGroup(null)}
                  style={{ fontSize: "11px", padding: "3px 10px" }}
                >
                  Clear Filter (Show All)
                </button>
              )}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
                gap: "12px",
              }}
            >
              {/* NO DEMAND Card */}
              <div
                onClick={() =>
                  setSelectedDemandGroup(selectedDemandGroup === "NO DEMAND" ? null : "NO DEMAND")
                }
                style={{
                  background: "var(--panel-bg)",
                  border: getGroupCardBorder("NO DEMAND"),
                  borderRadius: "var(--radius-lg)",
                  padding: "12px 14px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  minHeight: "86px",
                  boxShadow: selectedDemandGroup === "NO DEMAND" ? "0 2px 10px rgba(0,0,0,0.06)" : "none",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.05em", color: "var(--muted)", textTransform: "uppercase" }}>
                    NO DEMAND
                  </span>
                  <span style={{ fontSize: "12px" }}>⚪</span>
                </div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--muted)", margin: "2px 0" }}>
                  {demandGroupCounts["NO DEMAND"]}{" "}
                  <span style={{ fontSize: "12px", fontWeight: 500, color: "var(--muted)" }}>Routes</span>
                </div>
                <div style={{ fontSize: "10.5px", color: "var(--muted)" }}>
                  0% Occupancy (idle)
                </div>
              </div>

              {/* NORMAL Card */}
              <div
                onClick={() =>
                  setSelectedDemandGroup(selectedDemandGroup === "NORMAL" ? null : "NORMAL")
                }
                style={{
                  background: "var(--panel-bg)",
                  border: getGroupCardBorder("NORMAL"),
                  borderRadius: "var(--radius-lg)",
                  padding: "12px 14px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  minHeight: "86px",
                  boxShadow: selectedDemandGroup === "NORMAL" ? "0 2px 10px rgba(16, 185, 129, 0.12)" : "none",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.05em", color: "#059669", textTransform: "uppercase" }}>
                    NORMAL
                  </span>
                  <span style={{ fontSize: "12px" }}>🟢</span>
                </div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "#059669", margin: "2px 0" }}>
                  {demandGroupCounts["NORMAL"]}{" "}
                  <span style={{ fontSize: "12px", fontWeight: 500, color: "var(--muted)" }}>Routes</span>
                </div>
                <div style={{ fontSize: "10.5px", color: "var(--muted)" }}>
                  1%–79% Occupancy
                </div>
              </div>

              {/* HIGH DEMAND Card */}
              <div
                onClick={() =>
                  setSelectedDemandGroup(selectedDemandGroup === "HIGH DEMAND" ? null : "HIGH DEMAND")
                }
                style={{
                  background: "var(--panel-bg)",
                  border: getGroupCardBorder("HIGH DEMAND"),
                  borderRadius: "var(--radius-lg)",
                  padding: "12px 14px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  minHeight: "86px",
                  boxShadow: selectedDemandGroup === "HIGH DEMAND" ? "0 2px 10px rgba(245, 158, 11, 0.12)" : "none",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.05em", color: "#D97706", textTransform: "uppercase" }}>
                    HIGH DEMAND
                  </span>
                  <span style={{ fontSize: "12px" }}>🟡</span>
                </div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "#D97706", margin: "2px 0" }}>
                  {demandGroupCounts["HIGH DEMAND"]}{" "}
                  <span style={{ fontSize: "12px", fontWeight: 500, color: "var(--muted)" }}>Routes</span>
                </div>
                <div style={{ fontSize: "10.5px", color: "var(--muted)" }}>
                  80%–100% Occupancy
                </div>
              </div>

              {/* OVERCAPACITY Card */}
              <div
                onClick={() =>
                  setSelectedDemandGroup(selectedDemandGroup === "OVERCAPACITY" ? null : "OVERCAPACITY")
                }
                style={{
                  background: "var(--panel-bg)",
                  border: getGroupCardBorder("OVERCAPACITY"),
                  borderRadius: "var(--radius-lg)",
                  padding: "12px 14px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  minHeight: "86px",
                  boxShadow: selectedDemandGroup === "OVERCAPACITY" ? "0 2px 10px rgba(239, 68, 68, 0.12)" : "none",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.05em", color: "#DC2626", textTransform: "uppercase" }}>
                    OVERCAPACITY
                  </span>
                  <span style={{ fontSize: "12px" }}>🔴</span>
                </div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "#DC2626", margin: "2px 0" }}>
                  {demandGroupCounts["OVERCAPACITY"]}{" "}
                  <span style={{ fontSize: "12px", fontWeight: 500, color: "var(--muted)" }}>Routes</span>
                </div>
                <div style={{ fontSize: "10.5px", color: "var(--muted)" }}>
                  &gt;100% Occupancy (Exceeded)
                </div>
              </div>
            </div>
          </div>

          {/* 4 & 6. ROUTE-WISE DEMAND ANALYSIS TABLE */}
          <div className="panel" style={{ marginBottom: "28px" }}>
            <div className="panel-header">
              <div className="panel-title-group">
                <h2>Route-wise Demand Analysis</h2>
                <p>
                  Click any route to drill down into time-specific ridership and bus dispatch recommendations. Occupancy is uncapped.
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {selectedDemandGroup && (
                  <span
                    style={{
                      fontSize: "11.5px",
                      fontWeight: 600,
                      background: "var(--section-bg)",
                      border: "1px solid var(--line)",
                      padding: "4px 10px",
                      borderRadius: "var(--radius-full)",
                    }}
                  >
                    Showing {selectedDemandGroup} only ({visibleRoutes.length})
                  </span>
                )}
              </div>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table className="event-table">
                <thead>
                  <tr>
                    <th style={{ width: "16%" }}>Route</th>
                    <th style={{ width: "26%" }}>Corridor Description</th>
                    <th style={{ width: "10%", textAlign: "center" }}>Trips</th>
                    <th style={{ width: "12%", textAlign: "center" }}>Passengers</th>
                    <th style={{ width: "12%", textAlign: "center" }}>Capacity</th>
                    <th style={{ width: "12%", textAlign: "center" }}>Occupancy</th>
                    <th style={{ width: "12%", textAlign: "center" }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRoutes.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: "center", padding: "32px", color: "var(--muted)" }}>
                        No routes match the selected demand filter.
                      </td>
                    </tr>
                  ) : (
                    visibleRoutes.map((row) => {
                      const theme = getStatusTheme(row.status);
                      const isOver = row.status === "OVERCAPACITY";
                      return (
                        <tr
                          key={row.route}
                          onClick={() => setSelectedRoute(row.route)}
                          style={{ cursor: "pointer" }}
                          title={`Click to view deep-dive analysis for Route ${row.route}`}
                        >
                          {/* Route */}
                          <td>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span
                                style={{
                                  fontFamily: "var(--font-mono)",
                                  fontSize: "13.5px",
                                  fontWeight: 700,
                                  padding: "3px 8px",
                                  borderRadius: "var(--radius-xs)",
                                  background: isOver ? "rgba(239, 68, 68, 0.12)" : "var(--section-bg)",
                                  color: isOver ? "#DC2626" : "var(--text-bright)",
                                  border: `1px solid ${isOver ? "rgba(239, 68, 68, 0.3)" : "var(--line)"}`,
                                }}
                              >
                                Route {row.route}
                              </span>
                              <span style={{ fontSize: "11px", color: "var(--muted)" }}>➔</span>
                            </div>
                          </td>

                          {/* Corridor Description */}
                          <td style={{ color: "var(--text)", fontSize: "12.5px" }}>
                            {row.corridor}
                          </td>

                          {/* Trips */}
                          <td style={{ textAlign: "center", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                            {row.trips}
                          </td>

                          {/* Passengers */}
                          <td
                            style={{
                              textAlign: "center",
                              fontFamily: "var(--font-mono)",
                              fontWeight: 700,
                              color: isOver ? "#DC2626" : "var(--text-bright)",
                            }}
                          >
                            {row.passengers.toLocaleString()}
                          </td>

                          {/* Capacity */}
                          <td style={{ textAlign: "center", fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                            {row.capacity.toLocaleString()}
                          </td>

                          {/* Occupancy (Uncapped) */}
                          <td style={{ textAlign: "center" }}>
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "14px",
                                fontWeight: 700,
                                color: getOccupancyColor(row.occupancy),
                              }}
                            >
                              {row.occupancy}%
                            </span>
                          </td>

                          {/* Status */}
                          <td style={{ textAlign: "center" }}>
                            <span className={`badge ${theme.badgeClass}`}>
                              {isOver && (
                                <span
                                  className="pulse-dot"
                                  style={{ background: "#EF4444", width: "5px", height: "5px" }}
                                />
                              )}
                              {row.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
