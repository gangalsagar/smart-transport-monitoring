import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class GPSCoordinate:
    latitude: float
    longitude: float
    accuracy_m: float = 3.0


class MockGPSRoute:
    """
    Deterministic Mock GPS generator for Module 2 Traffic Monitoring.
    Simulates a vehicle travelling forward along Bangalore's Outer Ring Road / MG Road corridor.
    
    Starting Point: Anil Kumble Circle / MG Road (12.975220, 77.609450)
    Direction (Bearing): 75.0 degrees (Eastbound towards Trinity Circle / Indiranagar)
    """

    def __init__(
        self,
        start_latitude: float = 12.975220,
        start_longitude: float = 77.609450,
        bearing_degrees: float = 75.0,
        meters_per_step: float = 65.0,
    ):
        """
        :param start_latitude: Starting latitude of Bangalore MG Road corridor (12.975220 N)
        :param start_longitude: Starting longitude (77.609450 E)
        :param bearing_degrees: Forward road bearing heading East towards Trinity
        :param meters_per_step: Distance covered in meters per 10-second observation
        """
        self.start_latitude = start_latitude
        self.start_longitude = start_longitude
        self.bearing_degrees = bearing_degrees
        self.meters_per_step = meters_per_step
        self.current_step = 0

    def get_position_at_step(self, step_index: int) -> GPSCoordinate:
        """
        Calculates deterministic GPS coordinate at step_index moving forward.
        Uses spherical geodesy forward formula. Earth radius = 6,378,137m.
        """
        earth_radius = 6378137.0
        distance = step_index * self.meters_per_step
        bearing_rad = math.radians(self.bearing_degrees)

        lat_rad = math.radians(self.start_latitude)
        lon_rad = math.radians(self.start_longitude)

        new_lat_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance / earth_radius)
            + math.cos(lat_rad) * math.sin(distance / earth_radius) * math.cos(bearing_rad)
        )

        new_lon_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance / earth_radius) * math.cos(lat_rad),
            math.cos(distance / earth_radius) - math.sin(lat_rad) * math.sin(new_lat_rad),
        )

        return GPSCoordinate(
            latitude=round(math.degrees(new_lat_rad), 6),
            longitude=round(math.degrees(new_lon_rad), 6),
            accuracy_m=3.0,
        )

    def get_next_position(self) -> GPSCoordinate:
        """
        Retrieve the next sequential GPS coordinate along the road.
        """
        coord = self.get_position_at_step(self.current_step)
        self.current_step += 1
        return coord

    def reset(self):
        """
        Reset route back to starting position.
        """
        self.current_step = 0
