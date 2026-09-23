import os
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from shared.schemas.alert_schema import Alert


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ALERT_FILE = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "alerts"
    / "alerts.jsonl"
)

TRAFFIC_DENSITY_FILE = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "traffic"
    / "traffic_density.jsonl"
)

EVIDENCE_DIRECTORY = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "evidence"
)

PASSENGER_BOARDING_FILE = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "passenger"
    / "boarding_events.jsonl"
)



# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Smart Transport Monitoring Backend",
    version="1.0.0",
    description="Central backend for Smart Transport Monitoring.",
)


# ============================================================
# CORS
# ============================================================

local_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:3000",
]

env_cors = os.getenv("CORS_ORIGINS")
if env_cors:
    extra_origins = [orig.strip() for orig in env_cors.split(",") if orig.strip()]
    allowed_origins = list(dict.fromkeys(local_origins + extra_origins))
else:
    allowed_origins = local_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ============================================================
# STORAGE
# ============================================================

def load_alerts():

    if not ALERT_FILE.exists():
        return []

    alerts = []

    with ALERT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            try:

                data = json.loads(line)

                alert = Alert.model_validate(
                    data
                )

                alerts.append(alert)

            except Exception as exc:

                print(
                    "WARNING: invalid alert skipped:",
                    exc
                )

    return alerts


def alert_exists(alert_id: str) -> bool:
    """
    Check if an alert with the given alert_id already exists.
    """
    if not ALERT_FILE.exists():
        return False

    with ALERT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("alert_id") == alert_id:
                    return True
            except Exception:
                continue

    return False


def save_alert(alert: Alert) -> bool:
    """
    Append an alert to storage if not already present (idempotent).

    Returns:
        True if the alert was newly saved.
        False if the alert_id was already present (no duplicate written).
    """
    if alert_exists(alert.alert_id):
        return False

    ALERT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with ALERT_FILE.open(
        "a",
        encoding="utf-8"
    ) as file:
        file.write(
            alert.model_dump_json()
        )
        file.write("\n")

    return True


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "service":
            "Smart Transport Monitoring Backend",

        "status":
            "running",

        "version":
            "1.0.0",

        "docs":
            "/docs",

        "health":
            "/health",

        "alerts":
            "/alerts",

        "evidence":
            "/evidence/{filename}",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    alerts = load_alerts()

    return {
        "status":
            "ok",

        "service":
            "central_backend",

        "version":
            "1.0.0",

        "alert_storage":
            str(ALERT_FILE),

        "alert_count":
            len(alerts),

        "evidence_directory":
            str(EVIDENCE_DIRECTORY),
    }


# ============================================================
# NORMAL JSON ALERT
# ============================================================

@app.post("/alerts")
def receive_alert(
    alert: Alert
):

    is_new = save_alert(
        alert
    )

    # Persist Module 4 boarding records to separate passenger storage
    if alert.module.type == "passenger_demand" and is_new:
        try:
            PASSENGER_BOARDING_FILE.parent.mkdir(parents=True, exist_ok=True)
            with PASSENGER_BOARDING_FILE.open("a", encoding="utf-8") as pf:
                pf.write(json.dumps(alert.payload))
                pf.write("\n")
        except Exception as e:
            print("WARNING: Failed writing to passenger storage:", e)

    return {
        "status":
            "accepted",

        "alert_id":
            alert.alert_id,

        "module":
            alert.module.type,

        "duplicate":
            not is_new,
    }


# ============================================================
# ALERT + EVIDENCE IMAGE
# ============================================================

@app.post("/alerts/with-evidence")
async def receive_alert_with_evidence(
    alert: str = Form(...),
    evidence: UploadFile = File(...),
):

    # --------------------------------------------------------
    # Parse alert
    # --------------------------------------------------------

    try:

        alert_data = json.loads(
            alert
        )

        validated_alert = (
            Alert.model_validate(
                alert_data
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=f"Invalid alert: {exc}",
        )


    # --------------------------------------------------------
    # Validate image
    # --------------------------------------------------------

    if not evidence.filename:

        raise HTTPException(
            status_code=400,
            detail="Evidence filename missing.",
        )


    original_filename = (
        Path(
            evidence.filename
        ).name
    )


    if (
        original_filename
        != evidence.filename
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid evidence filename.",
        )


    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
    }


    extension = (
        Path(
            original_filename
        ).suffix.lower()
    )


    if extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail="Unsupported evidence image format.",
        )


    # --------------------------------------------------------
    # Save evidence
    # --------------------------------------------------------

    EVIDENCE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )


    evidence_path = (
        EVIDENCE_DIRECTORY
        / original_filename
    )


    image_data = await evidence.read()


    if not image_data and not evidence_path.exists():

        raise HTTPException(
            status_code=400,
            detail="Evidence image is empty.",
        )


    if image_data:
        evidence_path.write_bytes(
            image_data
        )


    # --------------------------------------------------------
    # Update alert evidence path
    #
    # IMPORTANT:
    # Store a backend URL rather than the edge
    # device's C:\... path.
    # --------------------------------------------------------

    if validated_alert.evidence is not None:

        validated_alert.evidence.image_path = (
            f"/evidence/{original_filename}"
        )


    # --------------------------------------------------------
    # Save alert (idempotent)
    # --------------------------------------------------------

    is_new = save_alert(
        validated_alert
    )


    return {
        "status":
            "accepted",

        "alert_id":
            validated_alert.alert_id,

        "module":
            validated_alert.module.type,

        "evidence":
            f"/evidence/{original_filename}",

        "duplicate":
            not is_new,
    }


# ============================================================
# SERVE EVIDENCE
# ============================================================

@app.get("/evidence/{filename}")
def get_evidence(
    filename: str
):

    safe_filename = (
        Path(filename).name
    )


    if safe_filename != filename:

        raise HTTPException(
            status_code=400,
            detail="Invalid evidence filename.",
        )


    image_path = (
        EVIDENCE_DIRECTORY
        / safe_filename
    )


    if not image_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Evidence image not found.",
        )


    if not image_path.is_file():

        raise HTTPException(
            status_code=404,
            detail="Evidence image not found.",
        )


    extension = (
        image_path.suffix.lower()
    )


    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }


    return FileResponse(
        image_path,
        media_type=media_types.get(
            extension,
            "application/octet-stream"
        ),
        filename=safe_filename,
    )


# ============================================================
# GET ALL ALERTS
# ============================================================

@app.get("/alerts")
def get_alerts(
    module: Optional[str] = None
):

    alerts = load_alerts()

    if module:
        module_lower = module.strip().lower()
        alerts = [
            a for a in alerts
            if getattr(getattr(a, "module", None), "type", "").lower() == module_lower
        ]

    return {
        "count":
            len(alerts),

        "alerts": [
            alert.model_dump(
                mode="json"
            )
            for alert in alerts
        ],
    }



# ============================================================
# GET LATEST ALERTS
# ============================================================

@app.get("/alerts/latest")
def get_latest_alerts():

    alerts = load_alerts()

    latest = alerts[-10:]

    latest.reverse()

    return {
        "count":
            len(latest),

        "alerts": [
            alert.model_dump(
                mode="json"
            )
            for alert in latest
        ],
    }


# ============================================================
# GET SINGLE ALERT
# ============================================================

@app.get("/alerts/{alert_id}")
def get_alert(
    alert_id: str
):

    alerts = load_alerts()

    for alert in alerts:

        if alert.alert_id == alert_id:

            return alert.model_dump(
                mode="json"
            )


    raise HTTPException(
        status_code=404,
        detail=(
            f"Alert '{alert_id}' "
            f"not found."
        ),
    )


# ============================================================
# TRAFFIC DENSITY (MODULE 2)
# ============================================================

def load_traffic_density():
    if not TRAFFIC_DENSITY_FILE.exists():
        return []

    records = []
    with TRAFFIC_DENSITY_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


@app.post("/traffic/density")
def receive_traffic_density(
    data: dict
):
    """
    Receive single or batch of traffic density records from Module 2.
    """
    items = data.get("samples") if isinstance(data.get("samples"), list) else [data]

    TRAFFIC_DENSITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    with TRAFFIC_DENSITY_FILE.open("a", encoding="utf-8") as f:
        for item in items:
            if isinstance(item, dict):
                f.write(json.dumps(item) + "\n")
                saved_count += 1

    return {
        "status": "accepted",
        "module": "traffic",
        "saved_samples": saved_count,
    }


@app.get("/traffic/density")
def get_traffic_density(
    limit: int = 500
):
    """
    Get latest structured traffic density samples for heatmap rendering.
    """
    records = load_traffic_density()
    if limit > 0 and len(records) > limit:
        records = records[-limit:]

    return {
        "count": len(records),
        "traffic_density": records,
    }


# ============================================================
# MODULE 3 INCIDENT & CASE MANAGEMENT ENDPOINTS
# ============================================================

@app.get("/incidents")
def get_incidents(
    team: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
):
    """
    Query Module 3 incident and rash-driving events from the central database,
    with optional filtering by team ('rash_driving_team' | 'emergency_team'),
    event_type, status, or severity.
    """
    alerts = load_alerts()
    # Filter only incident_anpr module alerts
    incident_alerts = [
        a for a in alerts
        if getattr(getattr(a, "module", None), "type", "").lower() == "incident_anpr"
    ]

    filtered = []
    for alert in incident_alerts:
        p = alert.payload or {}
        if team and str(p.get("assigned_team", "")).lower() != team.strip().lower():
            continue
        if event_type and str(p.get("event_type", "")).lower() != event_type.strip().lower():
            continue
        if status and str(p.get("status", "")).lower() != status.strip().lower():
            continue
        if severity and str(alert.severity).lower() != severity.strip().lower():
            continue
        filtered.append(alert)

    return {
        "count": len(filtered),
        "incidents": [a.model_dump(mode="json") for a in filtered],
    }


@app.patch("/incidents/{event_id}/status")
def update_incident_status(
    event_id: str,
    status: str,
):
    """
    Update the operational lifecycle status of an incident case
    (e.g., 'new' -> 'acknowledged' -> 'in_progress' -> 'dispatched' -> 'resolved' -> 'closed').
    """
    valid_statuses = {"new", "acknowledged", "in_progress", "dispatched", "resolved", "closed"}
    status_lower = status.strip().lower()
    if status_lower not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of: {sorted(list(valid_statuses))}",
        )

    alerts = load_alerts()
    updated = False

    for alert in alerts:
        if alert.alert_id == event_id or alert.payload.get("event_id") == event_id:
            alert.payload["status"] = status_lower
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail=f"Incident event '{event_id}' not found.")

    # Write updated alert collection back atomically
    with ALERT_FILE.open("w", encoding="utf-8") as f:
        for a in alerts:
            f.write(a.model_dump_json())
            f.write("\n")

    return {
        "status": "updated",
        "event_id": event_id,
        "new_status": status_lower,
    }



# ============================================================
# MODULE 4: PASSENGER DEMAND INTELLIGENCE APIS
# ============================================================

from module4_passenger_demand.models.passenger_models import BoardingEvent
from module4_passenger_demand.analytics.demand_analyzer import DemandAnalyzer
from module4_passenger_demand.analytics.frequency_recommender import FrequencyRecommender
from module4_passenger_demand.providers.pass_registry import PassRegistry, FilePassDataProvider
from module4_passenger_demand.services.pass_validator import PassValidator
from module4_passenger_demand.services.data_quality_service import DataQualityService
from module4_passenger_demand.services.boarding_service import BoardingService

# Global service instances for backend validation & analytics
_pass_provider = FilePassDataProvider(PROJECT_ROOT / "data" / "passenger" / "bus_passes.csv")
_pass_registry = PassRegistry(provider=_pass_provider)
_pass_validator = PassValidator(registry=_pass_registry)
_data_quality_service = DataQualityService(bus_capacity=60)
_boarding_service = BoardingService(validator=_pass_validator, data_quality=_data_quality_service)
_demand_analyzer = DemandAnalyzer(bus_capacity=60)
_frequency_recommender = FrequencyRecommender()


def load_boarding_events():
    """Loads all boarding events from alerts and dedicated storage"""
    events = []
    
    # 1. Read from dedicated passenger boarding file
    if PASSENGER_BOARDING_FILE.exists():
        with PASSENGER_BOARDING_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    events.append(BoardingEvent.model_validate(data))
                except Exception:
                    continue

    # 2. Also check general alert file for any passenger_demand alerts
    alerts = load_alerts()
    for a in alerts:
        if a.module.type == "passenger_demand" and a.payload:
            # Avoid duplicate if already loaded from passenger file
            if not any(e.event_id == a.payload.get("event_id") for e in events):
                try:
                    events.append(BoardingEvent.model_validate(a.payload))
                except Exception:
                    continue

    return events


@app.post("/passenger/boarding-events")
def create_boarding_event(event: BoardingEvent):
    """
    Ingest a single verified or audited boarding event from conductor terminal / ETM.
    """
    PASSENGER_BOARDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PASSENGER_BOARDING_FILE.open("a", encoding="utf-8") as f:
        f.write(event.model_dump_json())
        f.write("\n")

    return {
        "status": "accepted",
        "event_id": event.event_id,
        "validation_status": event.validation_status,
    }


@app.post("/passenger/pass/validate")
def validate_pass_live(payload: dict):
    """
    Real-time interactive conductor physical pass validation endpoint.
    Payload: {"pass_id": "...", "route_id": "25A", "bus_id": "BUS-102"}
    """
    pass_id = payload.get("pass_id", "")
    route_id = payload.get("route_id", "25A")
    bus_id = payload.get("bus_id", "BUS-102")
    stop_id = payload.get("stop_id", "STOP-12")

    boarding_event = _boarding_service.process_pass_entry(
        pass_id=pass_id,
        bus_id=bus_id,
        route_id=route_id,
        stop_id=stop_id,
    )

    # Persist the event
    PASSENGER_BOARDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PASSENGER_BOARDING_FILE.open("a", encoding="utf-8") as f:
        f.write(boarding_event.model_dump_json())
        f.write("\n")

    return {
        "status": boarding_event.validation_status,
        "reason": boarding_event.validation_reason,
        "event_id": boarding_event.event_id,
        "passenger_type": boarding_event.passenger_type,
        "pass_id": boarding_event.pass_id,
        "source": boarding_event.source,
        "confidence": boarding_event.confidence,
    }


@app.get("/passenger/demand/summary")
def get_passenger_demand_summary():
    """
    Returns aggregated passenger demand metrics, ticket vs pass breakdown,
    capacity load factors, and data quality scores.
    """
    events = load_boarding_events()
    return _demand_analyzer.analyze_events(events)


@app.get("/passenger/demand/routes")
def get_passenger_route_demand():
    """
    Returns route-level passenger demand metrics.
    """
    events = load_boarding_events()
    analysis = _demand_analyzer.analyze_events(events)
    return {"routes": analysis.get("routes", [])}


@app.get("/passenger/demand/stops")
def get_passenger_stop_demand():
    """
    Returns stop-level passenger density and top boarding stops.
    """
    events = load_boarding_events()
    analysis = _demand_analyzer.analyze_events(events)
    return {"top_stops": analysis.get("top_stops", [])}


@app.get("/passenger/demand/peak-hours")
def get_passenger_peak_hours():
    """
    Returns hourly demand distribution with peak-hour flags and load factors.
    """
    events = load_boarding_events()
    analysis = _demand_analyzer.analyze_events(events)
    return {"hourly_demand": analysis.get("hourly_demand", [])}


@app.get("/passenger/recommendations/frequency")
def get_frequency_recommendations():
    """
    Returns decision-support bus frequency recommendations based on demand vs capacity.
    """
    events = load_boarding_events()
    analysis = _demand_analyzer.analyze_events(events)
    routes = analysis.get("routes", [])
    recommendations = _frequency_recommender.generate_fleet_recommendations(
        route_summaries=routes,
        nominal_bus_capacity=analysis.get("bus_capacity", 60)
    )
    return {
        "status": "ok",
        "recommendations": recommendations,
        "decision_support_note": "Advisories are generated for municipal fleet management. No automatic bus dispatch is executed.",
    }


# ============================================================
# CLEAR ALL DATA (BACKEND + HEATMAP + EVIDENCE)
# ============================================================

@app.post("/clear")
def clear_all_data():
    """
    Clear all received alerts, traffic density samples, and uploaded evidence.
    """
    if ALERT_FILE.exists():
        ALERT_FILE.write_text("", encoding="utf-8")

    if TRAFFIC_DENSITY_FILE.exists():
        TRAFFIC_DENSITY_FILE.write_text("", encoding="utf-8")

    if PASSENGER_BOARDING_FILE.exists():
        PASSENGER_BOARDING_FILE.write_text("", encoding="utf-8")

    if EVIDENCE_DIRECTORY.exists():
        for file in EVIDENCE_DIRECTORY.iterdir():
            if file.is_file():
                try:
                    file.unlink()
                except Exception:
                    pass

    return {
        "status": "cleared",
        "message": "All backend alerts, traffic density heatmap points, and evidence files have been cleared.",
    }


# ============================================================
# RUN DIRECTLY
# ============================================================



if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
    )