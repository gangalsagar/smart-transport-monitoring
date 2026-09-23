from datetime import datetime, timezone
from threading import Lock

from flask import Flask, jsonify, request


app = Flask(__name__)

# Latest GPS position received from the phone.
latest_gps = {
    "latitude": None,
    "longitude": None,
    "accuracy_m": None,
    "timestamp": None,
    "source": "phone",
}

gps_lock = Lock()


@app.get("/")
def root():
    return {
        "service": "Smart Transport Phone GPS Bridge",
        "status": "running",
        "gps": "/gps",
        "update": "/gps/update",
    }


@app.get("/gps")
def get_gps():

    with gps_lock:
        position = dict(latest_gps)

    if position["latitude"] is None:
        return jsonify({
            "status": "waiting",
            "message": "No GPS position received from phone yet.",
        }), 503

    return jsonify(position)


@app.post("/gps/update")
def update_gps():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "JSON body required"
        }), 400

    try:
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])

        accuracy = float(
            data.get(
                "accuracy_m",
                data.get("accuracy", 0.0)
            )
        )

    except (KeyError, TypeError, ValueError):

        return jsonify({
            "error": (
                "latitude, longitude and "
                "accuracy_m are required"
            )
        }), 400

    timestamp = data.get(
        "timestamp"
    )

    if not timestamp:
        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

    position = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_m": accuracy,
        "timestamp": timestamp,
        "source": "phone",
    }

    with gps_lock:
        latest_gps.update(position)

    print(
        "\n[PHONE GPS]"
        f"\n  Latitude  : {latitude:.6f}"
        f"\n  Longitude : {longitude:.6f}"
        f"\n  Accuracy  : {accuracy:.2f} m"
        f"\n  Timestamp : {timestamp}"
    )

    return jsonify({
        "status": "accepted",
        "gps": position,
    })


if __name__ == "__main__":

    print("=" * 60)
    print("SMART TRANSPORT PHONE GPS BRIDGE")
    print("=" * 60)

    print("\nListening on:")
    print("  http://0.0.0.0:9000")

    print("\nPhone GPS update:")
    print("  POST /gps/update")

    print("\nModule 1 GPS endpoint:")
    print("  GET /gps")

    app.run(
        host="0.0.0.0",
        port=9000,
        debug=False,
    )