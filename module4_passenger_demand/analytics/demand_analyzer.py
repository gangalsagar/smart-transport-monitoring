import logging
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional

from module4_passenger_demand.models.passenger_models import BoardingEvent, HourlyDemandMetric

logger = logging.getLogger(__name__)


class DemandAnalyzer:
    """
    Central server and analytics engine for calculating passenger demand metrics:
    - Total boardings
    - Ticket vs Pass breakdown
    - Route-level and Bus-level aggregations
    - Stop-wise density telemetry
    - Hourly demand distribution and peak hours
    - Data quality / anomaly score
    """
    def __init__(self, bus_capacity: int = 60):
        self.bus_capacity = bus_capacity

    def analyze_events(self, events: List[BoardingEvent]) -> Dict[str, Any]:
        if not events:
            return self._empty_summary()

        total_count = len(events)
        ticket_count = sum(1 for e in events if e.passenger_type == "ticket" and e.validation_status != "invalid")
        pass_count = sum(1 for e in events if e.passenger_type == "pass" and e.validation_status != "invalid")
        suspicious_count = sum(1 for e in events if e.validation_status == "suspicious")
        invalid_count = sum(1 for e in events if e.validation_status == "invalid")
        valid_count = sum(1 for e in events if e.validation_status == "valid")

        # Data quality score: percentage of clean, valid submissions
        quality_score = round((valid_count / total_count) * 100, 1) if total_count > 0 else 100.0

        # Route aggregation
        route_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "ticket": 0, "pass": 0, "suspicious": 0})
        # Bus aggregation
        bus_stats: Dict[str, int] = defaultdict(int)
        # Stop aggregation
        stop_stats: Dict[str, int] = defaultdict(int)
        # Hourly aggregation
        hourly_counts: Dict[int, int] = defaultdict(int)

        for e in events:
            if e.validation_status == "invalid":
                continue

            r_id = e.route_id or "UNKNOWN"
            route_stats[r_id]["total"] += 1
            if e.passenger_type == "ticket":
                route_stats[r_id]["ticket"] += 1
            else:
                route_stats[r_id]["pass"] += 1

            if e.validation_status == "suspicious":
                route_stats[r_id]["suspicious"] += 1

            bus_stats[e.bus_id] += 1
            if e.boarding_stop_id:
                stop_stats[e.boarding_stop_id] += 1

            hour = e.timestamp.hour if hasattr(e.timestamp, "hour") else 8
            hourly_counts[hour] += 1

        # Calculate Hourly Metrics & detect peak hours
        hourly_metrics: List[Dict[str, Any]] = []
        max_hourly_boardings = max(hourly_counts.values()) if hourly_counts else 0
        peak_threshold = max(15, max_hourly_boardings * 0.75) if max_hourly_boardings > 0 else 20

        for h in range(24):
            cnt = hourly_counts.get(h, 0)
            is_peak = cnt >= peak_threshold and cnt > 0
            load_factor = round(cnt / self.bus_capacity, 2) if self.bus_capacity > 0 else 0.0
            hourly_metrics.append({
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "boardings": cnt,
                "is_peak": is_peak,
                "load_factor": load_factor,
            })

        # Routes summary
        routes_summary = []
        for r_id, data in route_stats.items():
            tot = data["total"]
            load_factor = round(tot / self.bus_capacity, 2) if self.bus_capacity > 0 else 0.0
            routes_summary.append({
                "route_id": r_id,
                "total_boardings": tot,
                "ticket_boardings": data["ticket"],
                "pass_boardings": data["pass"],
                "suspicious_boardings": data["suspicious"],
                "capacity": self.bus_capacity,
                "load_factor": load_factor,
            })

        # Stops summary
        stops_summary = [
            {"stop_id": stop, "boardings": count}
            for stop, count in sorted(stop_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return {
            "total_boardings": valid_count + suspicious_count,
            "ticket_boardings": ticket_count,
            "pass_boardings": pass_count,
            "suspicious_count": suspicious_count,
            "invalid_count": invalid_count,
            "quality_score": quality_score,
            "bus_capacity": self.bus_capacity,
            "routes": routes_summary,
            "buses": [{"bus_id": b, "boardings": c} for b, c in bus_stats.items()],
            "top_stops": stops_summary,
            "hourly_demand": hourly_metrics,
        }

    def _empty_summary(self) -> Dict[str, Any]:
        return {
            "total_boardings": 0,
            "ticket_boardings": 0,
            "pass_boardings": 0,
            "suspicious_count": 0,
            "invalid_count": 0,
            "quality_score": 100.0,
            "bus_capacity": self.bus_capacity,
            "routes": [],
            "buses": [],
            "top_stops": [],
            "hourly_demand": [
                {"hour": h, "hour_label": f"{h:02d}:00", "boardings": 0, "is_peak": False, "load_factor": 0.0}
                for h in range(24)
            ],
        }
