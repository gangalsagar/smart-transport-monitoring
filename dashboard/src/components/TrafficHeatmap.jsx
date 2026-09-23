import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";

/**
 * TrafficHeatmap component for Module 2 Traffic Density.
 * Accepts Module 2 traffic observation alerts (and trafficDensity records)
 * and maps deterministic congestion levels into normalized intensities:
 *   - low      -> 0.25
 *   - medium   -> 0.50
 *   - high     -> 0.75
 *   - critical -> 1.00
 */
export default function TrafficHeatmap({ alerts = [], trafficDensity = [] }) {
  const map = useMap();
  const heatLayerRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    let points = [];

    // 1. Primary: Extract from Module 2 traffic observation alerts (GET /alerts?module=traffic)
    if (Array.isArray(alerts) && alerts.length > 0) {
      const trafficAlerts = alerts.filter((alert) => {
        const isTraffic = alert?.module?.type === "traffic";
        const lat = Number(alert?.gps?.latitude);
        const lng = Number(alert?.gps?.longitude);
        return (
          isTraffic &&
          !Number.isNaN(lat) &&
          !Number.isNaN(lng) &&
          (lat !== 0 || lng !== 0)
        );
      });

      if (trafficAlerts.length > 0) {
        points = trafficAlerts.map((alert) => {
          const lat = Number(alert.gps.latitude);
          const lng = Number(alert.gps.longitude);

          // Map congestion level to normalized intensity
          const congestion = String(
            alert.payload?.congestion_level ||
            alert.payload?.analysis?.congestion_level ||
            alert.severity ||
            "low"
          ).toLowerCase();

          let intensity = 0.25;
          if (congestion === "critical") {
            intensity = 1.00;
          } else if (congestion === "high") {
            intensity = 0.75;
          } else if (congestion === "medium") {
            intensity = 0.50;
          } else {
            intensity = 0.25;
          }

          return [lat, lng, intensity];
        });
      }
    }

    // 2. Secondary fallback: Use structured traffic density samples if available
    if (points.length === 0 && Array.isArray(trafficDensity) && trafficDensity.length > 0) {
      points = trafficDensity
        .filter((sample) => {
          const lat = Number(sample?.latitude);
          const lng = Number(sample?.longitude);
          return (
            !Number.isNaN(lat) &&
            !Number.isNaN(lng) &&
            (lat !== 0 || lng !== 0)
          );
        })
        .map((sample) => {
          const lat = Number(sample.latitude);
          const lng = Number(sample.longitude);
          const level = String(sample.traffic_level || "").toLowerCase();

          let intensity = 0.25;
          if (level === "critical") intensity = 1.00;
          else if (level === "high") intensity = 0.75;
          else if (level === "medium") intensity = 0.50;
          else intensity = 0.25;

          return [lat, lng, intensity];
        });
    }

    // Heatmap appearance configuration
    const options = {
      radius: 40,
      blur: 30,
      maxZoom: 18,
      max: 1.0,
      minOpacity: 0.35,
      gradient: {
        0.25: "#3b82f6", // Blue (Low)
        0.50: "#10b981", // Green (Medium)
        0.75: "#f59e0b", // Orange (High)
        1.00: "#ef4444", // Red (Critical)
      },
    };

    if (!heatLayerRef.current) {
      if (L.heatLayer) {
        heatLayerRef.current = L.heatLayer(points, options).addTo(map);
      }
    } else {
      heatLayerRef.current.setLatLngs(points);
      heatLayerRef.current.setOptions(options);
    }

    return () => {
      if (heatLayerRef.current && map) {
        map.removeLayer(heatLayerRef.current);
        heatLayerRef.current = null;
      }
    };
  }, [map, alerts, trafficDensity]);

  return null;
}
