from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class RoutePoint:
    latitude: float
    longitude: float


class MockRouteGPSProvider:
    """
    Deterministic mock GPS route provider for Module 2 Traffic Monitoring.
    Generates sequential GPS coordinates along a realistic continuous road route.
    """

    def __init__(
        self,
        waypoints: List[Tuple[float, float]] = None,
        total_steps: int = 100,
    ):
        # Default route: Continuous urban arterial road segment (e.g. Bangalore MG Road / Residency Rd)
        if waypoints is None:
            self.waypoints = [
                (12.971598, 77.594562),
                (12.972850, 77.596820),
                (12.974200, 77.599150),
                (12.975650, 77.601520),
                (12.977100, 77.603950),
                (12.978580, 77.606410),
                (12.980120, 77.608920),
            ]
        else:
            self.waypoints = waypoints

        self.total_steps = max(1, total_steps)
        self.current_step = 0
        self._route_points = self._interpolate_route()

    def _interpolate_route(self) -> List[RoutePoint]:
        """Linearly interpolates between waypoints to build a dense continuous polyline."""
        if len(self.waypoints) == 1:
            lat, lon = self.waypoints[0]
            return [RoutePoint(latitude=lat, longitude=lon) for _ in range(self.total_steps)]

        num_segments = len(self.waypoints) - 1
        points_per_segment = max(1, self.total_steps // num_segments)

        points = []
        for i in range(num_segments):
            start_lat, start_lon = self.waypoints[i]
            end_lat, end_lon = self.waypoints[i + 1]

            for s in range(points_per_segment):
                t = s / float(points_per_segment)
                lat = start_lat + t * (end_lat - start_lat)
                lon = start_lon + t * (end_lon - start_lon)
                points.append(RoutePoint(latitude=round(lat, 6), longitude=round(lon, 6)))

        # Ensure last point matches last waypoint
        end_lat, end_lon = self.waypoints[-1]
        points.append(RoutePoint(latitude=round(end_lat, 6), longitude=round(end_lon, 6)))
        return points

    def get_next_position(self) -> RoutePoint:
        """Get the next sequential coordinate along the mock route."""
        if not self._route_points:
            return RoutePoint(latitude=12.971598, longitude=77.594562)

        idx = min(self.current_step, len(self._route_points) - 1)
        self.current_step += 1
        return self._route_points[idx]

    def reset(self):
        """Reset sequence to beginning of route."""
        self.current_step = 0
