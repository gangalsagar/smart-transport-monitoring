import pytest
from datetime import datetime, date, timedelta

from module4_passenger_demand.models.passenger_models import PassRecord, BoardingEvent
from module4_passenger_demand.providers.pass_registry import PassRegistry, FilePassDataProvider
from module4_passenger_demand.services.pass_validator import PassValidator
from module4_passenger_demand.services.data_quality_service import DataQualityService
from module4_passenger_demand.services.boarding_service import BoardingService
from module4_passenger_demand.analytics.demand_analyzer import DemandAnalyzer
from module4_passenger_demand.analytics.frequency_recommender import FrequencyRecommender


@pytest.fixture
def sample_registry(tmp_path):
    csv_file = tmp_path / "test_passes.csv"
    csv_file.write_text(
        "pass_id,passenger_category,valid_from,valid_until,allowed_routes,status\n"
        "P458721,general,2026-01-01,2026-12-31,\"25A,25B\",active\n"
        "EXP-001,general,2024-01-01,2024-12-31,\"25A\",active\n"
        "FUTURE-002,student,2027-01-01,2027-12-31,\"25A\",active\n"
        "RTE-LIMITED,general,2026-01-01,2026-12-31,\"ROUTE-99\",active\n"
        "CANCELLED-003,general,2026-01-01,2026-12-31,\"25A\",cancelled\n",
        encoding="utf-8"
    )
    provider = FilePassDataProvider(csv_file)
    return PassRegistry(provider=provider)


def test_1_valid_pass(sample_registry):
    validator = PassValidator(sample_registry)
    res = validator.validate_pass("P458721", current_route_id="25A", check_time=datetime(2026, 5, 10))
    assert res.status == "valid"
    assert res.reason == "pass_verified"
    assert res.pass_record.pass_id == "P458721"


def test_2_unknown_pass(sample_registry):
    validator = PassValidator(sample_registry)
    res = validator.validate_pass("NON_EXISTENT_999", current_route_id="25A")
    assert res.status == "invalid"
    assert res.reason == "pass_not_found"


def test_3_expired_pass(sample_registry):
    validator = PassValidator(sample_registry)
    res = validator.validate_pass("EXP-001", current_route_id="25A", check_time=datetime(2026, 5, 10))
    assert res.status == "invalid"
    assert res.reason == "pass_expired"


def test_4_not_yet_active_pass(sample_registry):
    validator = PassValidator(sample_registry)
    res = validator.validate_pass("FUTURE-002", current_route_id="25A", check_time=datetime(2026, 5, 10))
    assert res.status == "invalid"
    assert res.reason == "pass_not_yet_active"


def test_5_route_restricted_pass(sample_registry):
    validator = PassValidator(sample_registry)
    res = validator.validate_pass("RTE-LIMITED", current_route_id="25A", check_time=datetime(2026, 5, 10))
    assert res.status == "invalid"
    assert res.reason == "route_not_allowed"


def test_6_duplicate_pass_submission(sample_registry):
    validator = PassValidator(sample_registry)
    dq = DataQualityService(duplicate_window_seconds=15.0)
    service = BoardingService(validator=validator, data_quality=dq)

    t0 = datetime(2026, 5, 10, 8, 15, 0)
    ev1 = service.process_pass_entry("P458721", bus_id="BUS-102", route_id="25A", timestamp=t0)
    assert ev1.validation_status == "valid"

    # Rapid re-entry 3 seconds later on same bus/trip
    t1 = datetime(2026, 5, 10, 8, 15, 3)
    ev2 = service.process_pass_entry("P458721", bus_id="BUS-102", route_id="25A", timestamp=t1)
    assert ev2.validation_status == "suspicious"
    assert ev2.validation_reason == "possible_duplicate_submission"


def test_7_same_pass_on_separate_legitimate_trips(sample_registry):
    validator = PassValidator(sample_registry)
    dq = DataQualityService(duplicate_window_seconds=15.0)
    service = BoardingService(validator=validator, data_quality=dq)

    # Morning trip
    t_morning = datetime(2026, 5, 10, 8, 15, 0)
    ev1 = service.process_pass_entry("P458721", bus_id="BUS-102", route_id="25A", timestamp=t_morning)
    assert ev1.validation_status == "valid"

    # Evening trip (separate trip / hours later)
    t_evening = datetime(2026, 5, 10, 17, 30, 0)
    ev2 = service.process_pass_entry("P458721", bus_id="BUS-108", route_id="25B", timestamp=t_evening)
    assert ev2.validation_status == "valid"


def test_8_abnormal_pass_entry_rate(sample_registry):
    validator = PassValidator(sample_registry)
    # Threshold = 3 entries in 10 seconds
    dq = DataQualityService(abnormal_submission_window_seconds=10.0, abnormal_submission_threshold=3)
    service = BoardingService(validator=validator, data_quality=dq)

    base = datetime(2026, 5, 10, 8, 0, 0)
    for i in range(3):
        service.process_pass_entry(f"P_{i}", bus_id="BUS-102", route_id="25A", timestamp=base + timedelta(seconds=i))

    # 4th rapid entry exceeds threshold
    burst_ev = service.process_pass_entry("P458721", bus_id="BUS-102", route_id="25A", timestamp=base + timedelta(seconds=4))
    assert burst_ev.validation_status == "suspicious"
    assert burst_ev.validation_reason == "abnormal_submission_rate"


def test_9_demand_aggregation_and_peaks():
    analyzer = DemandAnalyzer(bus_capacity=60)
    events = []

    # Add 40 tickets and 20 passes at 08:00
    for i in range(40):
        events.append(BoardingEvent(
            event_id=f"t_{i}", bus_id="BUS-102", route_id="25A",
            timestamp=datetime(2026, 5, 10, 8, 10), passenger_type="ticket", validation_status="valid"
        ))
    for i in range(20):
        events.append(BoardingEvent(
            event_id=f"p_{i}", bus_id="BUS-102", route_id="25A",
            timestamp=datetime(2026, 5, 10, 8, 20), passenger_type="pass", validation_status="valid"
        ))

    # Add 10 boardings at 11:00
    for i in range(10):
        events.append(BoardingEvent(
            event_id=f"t2_{i}", bus_id="BUS-102", route_id="25A",
            timestamp=datetime(2026, 5, 10, 11, 15), passenger_type="ticket", validation_status="valid"
        ))

    summary = analyzer.analyze_events(events)
    assert summary["total_boardings"] == 70
    assert summary["ticket_boardings"] == 50
    assert summary["pass_boardings"] == 20

    h8 = next(h for h in summary["hourly_demand"] if h["hour"] == 8)
    assert h8["boardings"] == 60
    assert h8["is_peak"] is True

    h11 = next(h for h in summary["hourly_demand"] if h["hour"] == 11)
    assert h11["boardings"] == 10
    assert h11["is_peak"] is False


def test_10_frequency_recommender():
    recommender = FrequencyRecommender()
    
    # Route 25A has 176 passengers for 2 buses (capacity = 120, load factor = 1.47 -> critical)
    crit = recommender.evaluate_route_demand(
        route_id="25A",
        hourly_boardings=176,
        nominal_bus_capacity=60,
        current_trips_per_hour=2
    )
    assert crit["demand_status"] == "critical"
    assert crit["recommended_trips_per_hour"] == 4
    assert "Increase frequency" in crit["recommendation"]
    assert crit["automated_dispatch"] is False
