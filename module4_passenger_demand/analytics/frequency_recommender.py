import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class FrequencyRecommender:
    """
    Decision-support advisor for Municipal Transit Authorities.
    
    Principles:
    - Analyzes load_factor = predicted_demand / available_capacity
    - Categorizes intervals: LOW | NORMAL | HIGH | CRITICAL
    - Generates actionable frequency suggestions.
    - STRICTLY DECISION SUPPORT: Never dispatches or modifies bus timetables automatically.
    """
    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
    ):
        self.thresholds = thresholds or {
            "low": 0.50,
            "normal": 0.85,
            "high": 1.15,
            "critical": 1.40,
        }

    def evaluate_route_demand(
        self,
        route_id: str,
        hourly_boardings: int,
        nominal_bus_capacity: int = 60,
        current_trips_per_hour: int = 2,
    ) -> Dict[str, Any]:
        total_capacity = nominal_bus_capacity * max(1, current_trips_per_hour)
        load_factor = round(hourly_boardings / total_capacity, 2) if total_capacity > 0 else 0.0

        if load_factor >= self.thresholds["critical"]:
            status = "critical"
            recommended_trips = current_trips_per_hour + 2
            recommendation_text = (
                f"Severe passenger crowding detected (Load factor {load_factor:.2f}). "
                f"Authority action recommended: Increase frequency by +2 trips/hr (+{nominal_bus_capacity * 2} capacity) during this interval."
            )
        elif load_factor >= self.thresholds["high"]:
            status = "high"
            recommended_trips = current_trips_per_hour + 1
            recommendation_text = (
                f"High passenger demand exceeding seating capacity (Load factor {load_factor:.2f}). "
                f"Consider increasing route frequency by +1 trip/hr."
            )
        elif load_factor <= self.thresholds["low"] and hourly_boardings > 0:
            status = "low"
            recommended_trips = max(1, current_trips_per_hour - 1)
            recommendation_text = (
                f"Low vehicle utilization observed (Load factor {load_factor:.2f}). "
                f"Authority option: Reallocate surplus fleet capacity to higher-demand corridors."
            )
        else:
            status = "normal"
            recommended_trips = current_trips_per_hour
            recommendation_text = (
                f"Optimal capacity equilibrium (Load factor {load_factor:.2f}). "
                f"Current schedule matches passenger boarding volumes."
            )

        return {
            "route_id": route_id,
            "hourly_boardings": hourly_boardings,
            "total_capacity": total_capacity,
            "load_factor": load_factor,
            "demand_status": status,
            "current_trips_per_hour": current_trips_per_hour,
            "recommended_trips_per_hour": recommended_trips,
            "recommendation": recommendation_text,
            "automated_dispatch": False,
        }

    def generate_fleet_recommendations(
        self,
        route_summaries: List[Dict[str, Any]],
        nominal_bus_capacity: int = 60,
    ) -> List[Dict[str, Any]]:
        results = []
        for r in route_summaries:
            r_id = r.get("route_id", "UNKNOWN")
            tot = r.get("total_boardings", 0)
            res = self.evaluate_route_demand(
                route_id=r_id,
                hourly_boardings=tot,
                nominal_bus_capacity=nominal_bus_capacity,
                current_trips_per_hour=2,
            )
            results.append(res)
        return results
