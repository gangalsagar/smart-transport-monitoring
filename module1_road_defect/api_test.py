import sys
from urllib.request import urlopen
import json


BASE_URL = "http://127.0.0.1:8000"


def request_json(path):
    """
    Send GET request and return parsed JSON.
    """

    url = BASE_URL + path

    try:

        with urlopen(
            url,
            timeout=5
        ) as response:

            status = response.status

            body = response.read().decode(
                "utf-8"
            )

            return status, json.loads(body)

    except Exception as exc:

        print(
            f"ERROR requesting {path}:"
        )

        print(exc)

        return None, None


def fail(message):

    print(
        f"[FAIL] {message}"
    )

    sys.exit(1)


def main():

    print("=" * 60)
    print("MODULE 1 API INTEGRATION TEST")
    print("=" * 60)

    # ========================================================
    # 1. Health
    # ========================================================

    print("\n[1] Testing /health...")

    status, health = request_json(
        "/health"
    )

    if status != 200:
        fail(
            f"/health returned HTTP {status}"
        )

    if health.get("status") != "ok":
        fail(
            "API health status is not 'ok'"
        )

    print(
        "[PASS] API health"
    )

    print(
        f"       Module: "
        f"{health.get('module')}"
    )

    print(
        f"       Version: "
        f"{health.get('version')}"
    )

    print(
        f"       Alerts: "
        f"{health.get('alert_count')}"
    )

    # ========================================================
    # 2. All alerts
    # ========================================================

    print("\n[2] Testing /alerts...")

    status, result = request_json(
        "/alerts"
    )

    if status != 200:
        fail(
            f"/alerts returned HTTP {status}"
        )

    alerts = result.get(
        "alerts",
        []
    )

    count = result.get(
        "count"
    )

    if count != len(alerts):
        fail(
            "Reported alert count does "
            "not match returned alerts"
        )

    if count == 0:
        fail(
            "No alerts returned"
        )

    print(
        f"[PASS] /alerts returned "
        f"{count} alerts"
    )

    # ========================================================
    # 3. Validate alert structure
    # ========================================================

    print(
        "\n[3] Validating alert contents..."
    )

    alert_ids = set()

    for index, alert in enumerate(
        alerts,
        start=1
    ):

        required_fields = [
            "alert_id",
            "bus_id",
            "timestamp",
            "gps",
            "module",
            "severity",
            "payload",
            "source",
            "evidence",
        ]

        for field in required_fields:

            if field not in alert:
                fail(
                    f"Alert {index} is missing "
                    f"field '{field}'"
                )

        # ----------------------------------------------------
        # Unique alert ID
        # ----------------------------------------------------

        alert_id = alert[
            "alert_id"
        ]

        if alert_id in alert_ids:
            fail(
                f"Duplicate alert ID: "
                f"{alert_id}"
            )

        alert_ids.add(
            alert_id
        )

        # ----------------------------------------------------
        # GPS
        # ----------------------------------------------------

        gps = alert["gps"]

        if not isinstance(
            gps.get("latitude"),
            (int, float)
        ):

            fail(
                f"{alert_id}: invalid latitude"
            )

        if not isinstance(
            gps.get("longitude"),
            (int, float)
        ):

            fail(
                f"{alert_id}: invalid longitude"
            )

        if not isinstance(
            gps.get("accuracy_m"),
            (int, float)
        ):

            fail(
                f"{alert_id}: invalid GPS accuracy"
            )

        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        evidence = alert[
            "evidence"
        ]

        if not evidence:
            fail(
                f"{alert_id}: evidence missing"
            )

        if not evidence.get(
            "image_path"
        ):

            fail(
                f"{alert_id}: evidence "
                f"image path missing"
            )

        # ----------------------------------------------------
        # Payload
        # ----------------------------------------------------

        payload = alert[
            "payload"
        ]

        if payload.get(
            "defect_type"
        ) != "pothole":

            fail(
                f"{alert_id}: unexpected "
                f"defect type"
            )

        if "confidence" not in payload:
            fail(
                f"{alert_id}: confidence missing"
            )

        if "track_id" not in payload:
            fail(
                f"{alert_id}: track_id missing"
            )

        if "frame_number" not in payload:
            fail(
                f"{alert_id}: frame_number missing"
            )

    print(
        f"[PASS] Validated "
        f"{len(alerts)} alerts"
    )

    # ========================================================
    # 4. Latest alerts
    # ========================================================

    print(
        "\n[4] Testing /alerts/latest..."
    )

    status, latest = request_json(
        "/alerts/latest"
    )

    if status != 200:
        fail(
            f"/alerts/latest returned "
            f"HTTP {status}"
        )

    latest_alerts = latest.get(
        "alerts",
        []
    )

    if len(latest_alerts) == 0:
        fail(
            "No latest alerts returned"
        )

    print(
        f"[PASS] Latest endpoint returned "
        f"{len(latest_alerts)} alerts"
    )

    # ========================================================
    # 5. Individual alert
    # ========================================================

    first_alert_id = alerts[0][
        "alert_id"
    ]

    print(
        f"\n[5] Testing "
        f"/alerts/{first_alert_id}..."
    )

    status, individual = request_json(
        f"/alerts/{first_alert_id}"
    )

    if status != 200:
        fail(
            f"Individual alert endpoint "
            f"returned HTTP {status}"
        )

    if individual.get(
        "alert_id"
    ) != first_alert_id:

        fail(
            "Individual alert ID does "
            "not match requested ID"
        )

    print(
        "[PASS] Individual alert endpoint"
    )

    # ========================================================
    # Final summary
    # ========================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "MODULE 1 API TEST PASSED"
    )

    print(
        "=" * 60
    )

    print(
        f"API endpoint : {BASE_URL}"
    )

    print(
        f"Alerts tested: {len(alerts)}"
    )

    print(
        "Health       : PASS"
    )

    print(
        "Alerts       : PASS"
    )

    print(
        "Alert schema : PASS"
    )

    print(
        "GPS          : PASS"
    )

    print(
        "Evidence     : PASS"
    )

    print(
        "Latest       : PASS"
    )

    print(
        "Individual    : PASS"
    )

    print(
        "\nModule 1 API integration is ready."
    )


if __name__ == "__main__":
    main()