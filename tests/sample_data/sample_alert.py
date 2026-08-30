
from datetime import datetime,timezone
from shared.schemas.alert_schema import Alert

sample = Alert(
    alert_id="ALT-0001",
    bus_id="BUS-12",
    timestamp=datetime.now(timezone.utc),

    gps={
        "latitude": 12.9716,
        "longitude": 77.5946,
        "accuracy_m": 3.5
    },

    module={
        "type": "road_defect",
        "version": "1.0"
    },

    severity="high",

    payload={
        "defect_type": "pothole",
        "confidence": 0.92,
        "area_pixels": 28500
    },

    source={
        "device_id": "EDGE-01",
        "camera_id": "FRONT_CAM"
    }
)

print(sample.model_dump_json(indent=4))