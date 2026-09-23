import json
from pathlib import Path

from shared.schemas.alert_schema import Alert


class AlertStore:
    """
    Persists validated Alert objects as JSON Lines.

    One alert = one JSON object per line.
    """

    def __init__(self, output_path=None):

        project_root = Path(__file__).resolve().parents[2]

        if output_path is None:
            output_path = (
                project_root
                / "module1_road_defect"
                / "data"
                / "alerts"
                / "alerts.jsonl"
            )

        self.output_path = Path(output_path)

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    def save(self, alert: Alert):

        if not isinstance(alert, Alert):
            raise TypeError(
                "alert must be an Alert object"
            )

        with self.output_path.open(
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                alert.model_dump_json()
            )

            file.write("\n")

    def save_many(self, alerts):

        for alert in alerts:
            self.save(alert)

    def count(self):

        if not self.output_path.exists():
            return 0

        with self.output_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            return sum(
                1
                for line in file
                if line.strip()
            )

    def read_all(self):

        if not self.output_path.exists():
            return []

        alerts = []

        with self.output_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                if not line.strip():
                    continue

                data = json.loads(line)

                alerts.append(
                    Alert.model_validate(data)
                )

        return alerts


def main():

    print("=" * 60)
    print("ALERT STORE TEST")
    print("=" * 60)

    store = AlertStore()

    print(
        f"\nAlert file:\n"
        f"{store.output_path}"
    )

    print(
        f"\nExisting alerts: "
        f"{store.count()}"
    )

    print(
        "\nAlert store initialized successfully."
    )


if __name__ == "__main__":
    main()