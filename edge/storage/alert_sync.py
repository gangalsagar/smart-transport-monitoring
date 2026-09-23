import json
import mimetypes
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from edge.storage.alert_queue import AlertQueue
from shared.schemas.alert_schema import Alert


class AlertSync:
    """
    Offline-first synchronization of edge alerts.

    Each queued alert may contain an evidence.image_path.

    When synchronized:
        Alert JSON + evidence JPEG
            -> central backend

    If synchronization fails:
        alert remains in SQLite as FAILED
        and can be retried later.
    """

    def __init__(
        self,
        backend_url="http://127.0.0.1:8001",
        queue=None,
        timeout=5,
    ):

        self.backend_url = backend_url.rstrip("/")

        self.queue = (
            queue
            if queue is not None
            else AlertQueue()
        )

        self.timeout = timeout

    # ========================================================
    # MULTIPART BODY
    # ========================================================

    @staticmethod
    def _build_multipart(
        alert: Alert,
        evidence_path: Path,
    ):

        boundary = (
            "----SmartTransportBoundary"
            "7MA4YWxkTrZu0gW"
        )

        payload = alert.model_dump(
            mode="json"
        )

        json_body = json.dumps(
            payload
        ).encode("utf-8")

        filename = evidence_path.name

        mime_type = (
            mimetypes.guess_type(filename)[0]
            or "image/jpeg"
        )

        image_data = evidence_path.read_bytes()

        parts = []

        # ----------------------------------------------------
        # ALERT JSON
        # ----------------------------------------------------

        parts.append(
            (
                f"--{boundary}\r\n"
                "Content-Disposition: form-data; "
                'name="alert"\r\n'
                "Content-Type: application/json\r\n"
                "\r\n"
            ).encode("utf-8")
        )

        parts.append(
            json_body
        )

        parts.append(
            b"\r\n"
        )

        # ----------------------------------------------------
        # EVIDENCE IMAGE
        # ----------------------------------------------------

        parts.append(
            (
                f"--{boundary}\r\n"
                "Content-Disposition: form-data; "
                f'name="evidence"; filename="{filename}"\r\n'
                f"Content-Type: {mime_type}\r\n"
                "\r\n"
            ).encode("utf-8")
        )

        parts.append(
            image_data
        )

        parts.append(
            b"\r\n"
        )

        # ----------------------------------------------------
        # END
        # ----------------------------------------------------

        parts.append(
            (
                f"--{boundary}--\r\n"
            ).encode("utf-8")
        )

        body = b"".join(parts)

        content_type = (
            f"multipart/form-data; boundary={boundary}"
        )

        return body, content_type

    # ========================================================
    # SEND ONE ALERT
    # ========================================================

    def send_alert(
        self,
        alert: Alert,
    ) -> bool:

        if not isinstance(
            alert,
            Alert,
        ):

            raise TypeError(
                "alert must be an Alert object"
            )

        # ----------------------------------------------------
        # Find evidence
        # ----------------------------------------------------

        evidence_path = None

        if alert.evidence is not None:

            image_path = getattr(
                alert.evidence,
                "image_path",
                None,
            )

            if image_path:

                evidence_path = Path(
                    image_path
                )

        # ----------------------------------------------------
        # If evidence exists, upload alert + image
        # ----------------------------------------------------

        if (
            evidence_path is not None
            and evidence_path.exists()
            and evidence_path.is_file()
        ):

            return self._send_alert_with_evidence(
                alert,
                evidence_path,
            )

        # ----------------------------------------------------
        # Otherwise send normal JSON alert
        # ----------------------------------------------------

        return self._send_alert_json(
            alert
        )

    # ========================================================
    # SEND ALERT + EVIDENCE
    # ========================================================

    def _send_alert_with_evidence(
        self,
        alert: Alert,
        evidence_path: Path,
    ) -> bool:

        url = (
            f"{self.backend_url}"
            "/alerts/with-evidence"
        )

        try:

            body, content_type = (
                self._build_multipart(
                    alert,
                    evidence_path,
                )
            )

            request = Request(
                url,
                data=body,
                headers={
                    "Content-Type":
                        content_type,

                    "Accept":
                        "application/json",
                },
                method="POST",
            )

            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                response_body = (
                    response.read()
                    .decode("utf-8")
                )

                result = json.loads(
                    response_body
                )

                return (
                    response.status == 200
                    and result.get("status")
                    == "accepted"
                )

        except (
            HTTPError,
            URLError,
            TimeoutError,
            ConnectionError,
        ):

            return False

        except Exception:

            return False

    # ========================================================
    # SEND JSON ALERT ONLY
    # ========================================================

    def _send_alert_json(
        self,
        alert: Alert,
    ) -> bool:

        url = (
            f"{self.backend_url}/alerts"
        )

        payload = alert.model_dump(
            mode="json"
        )

        body = json.dumps(
            payload
        ).encode("utf-8")

        request = Request(
            url,
            data=body,
            headers={
                "Content-Type":
                    "application/json",

                "Accept":
                    "application/json",
            },
            method="POST",
        )

        try:

            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                response_body = (
                    response.read()
                    .decode("utf-8")
                )

                result = json.loads(
                    response_body
                )

                return (
                    response.status == 200
                    and result.get("status")
                    == "accepted"
                )

        except (
            HTTPError,
            URLError,
            TimeoutError,
            ConnectionError,
        ):

            return False

        except Exception:

            return False

    # ========================================================
    # SYNCHRONIZE QUEUE
    # ========================================================

    def sync(
        self,
        limit=20,
    ):

        queued = (
            self.queue.get_pending(
                limit=limit
            )
        )

        results = {
            "attempted": 0,
            "sent": 0,
            "failed": 0,
        }

        for alert_id, alert in queued:

            results["attempted"] += 1

            success = self.send_alert(
                alert
            )

            if success:

                self.queue.mark_sent(
                    alert_id
                )

                results["sent"] += 1

            else:

                self.queue.mark_failed(
                    alert_id,
                    "Backend unavailable "
                    "or evidence upload failed",
                )

                results["failed"] += 1

        return results

    # ========================================================
    # BACKEND CONNECTIVITY
    # ========================================================

    def backend_available(self):

        try:

            url = (
                f"{self.backend_url}/health"
            )

            request = Request(
                url,
                method="GET",
            )

            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                return (
                    response.status == 200
                )

        except Exception:

            return False
