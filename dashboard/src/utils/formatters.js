export const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";

/**
 * Normalizes an evidence image file path and constructs the proper backend stream URL.
 */
export function getEvidenceUrl(alertOrEvent) {
  if (!alertOrEvent) return null;
  const imagePath =
    alertOrEvent?.evidence?.image_path ||
    alertOrEvent?.payload?.evidence_image_path ||
    alertOrEvent?.evidence_image_path;

  if (!imagePath) return null;

  // Handles Windows vs POSIX paths
  const normalized = String(imagePath).replace(/\\/g, "/");
  const filename = normalized.split("/").pop();

  if (!filename) return null;
  return `${API_BASE_URL}/evidence/${encodeURIComponent(filename)}`;
}

/**
 * Format ISO datetime string to a crisp readable timestamp.
 */
export function formatTimestamp(isoString) {
  if (!isoString) return "N/A";
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return isoString;
  return d.toLocaleTimeString([], { hour12: false }) + " · " + d.toLocaleDateString([], { month: "short", day: "numeric" });
}

/**
 * Format decimal confidence to percentage string.
 */
export function formatConfidence(conf) {
  if (typeof conf !== "number" || Number.isNaN(conf)) return "N/A";
  return `${Math.round(conf * 100)}%`;
}

/**
 * Format GPS coordinates cleanly.
 */
export function formatGPS(gps) {
  if (!gps || typeof gps.latitude !== "number" || typeof gps.longitude !== "number") {
    return "GPS Unavailable";
  }
  return `${gps.latitude.toFixed(5)}, ${gps.longitude.toFixed(5)}`;
}

/**
 * Map severity string to standardized badge class.
 */
export function getSeverityBadgeClass(severity) {
  const s = String(severity || "info").toLowerCase();
  if (s === "critical") return "badge-critical";
  if (s === "high") return "badge-high";
  if (s === "medium") return "badge-medium";
  if (s === "low") return "badge-low";
  return "badge-info";
}
