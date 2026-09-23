import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from shared.gps.gps_fix import GPSFix
from shared.gps.gps_provider import GPSProvider
from shared.gps.laptop_provider import LaptopGPSProvider
from shared.gps.mobile_provider import MobileGPSProvider
from shared.config import Config


class SharedGPSService:
    """
    Centralized, thread-safe Shared GPS Service.
    
    Responsibilities:
    1. Runs a background poll worker independent of video FPS.
    2. Maintains the single latest GPSFix in memory with thread safety.
    3. Handles stale location detection and provider failure gracefully.
    4. Serves all vision modules (Module 1, Module 2) without duplicate hardware polling.
    """

    _instance: Optional["SharedGPSService"] = None
    _singleton_lock = threading.Lock()

    def __init__(
        self,
        provider: Optional[GPSProvider] = None,
        provider_type: Optional[str] = None,
        poll_interval_seconds: float = 1.0,
        stale_threshold_seconds: float = 15.0,
        config: Optional[Config] = None,
    ):
        self.config = config or Config()
        self.poll_interval = poll_interval_seconds
        self.stale_threshold = stale_threshold_seconds

        # Determine provider
        if provider is not None:
            self.provider = provider
        else:
            p_type = (provider_type or self.config.get("gps", "provider", default="laptop")).lower()
            if p_type == "laptop":
                self.provider = LaptopGPSProvider()
            elif p_type == "mobile":
                self.provider = MobileGPSProvider(endpoint=self.config.phone_gps_endpoint)
            else:
                self.provider = LaptopGPSProvider()

        self._lock = threading.Lock()
        self._latest_fix: GPSFix = GPSFix(
            source=self.provider.source_name,
            provider=self.provider.name,
            status="uninitialized",
        )

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    @classmethod
    def get_instance(cls, **kwargs) -> "SharedGPSService":
        """Singleton accessor to ensure ONE GPS service instance across the process."""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls(**kwargs)
            return cls._instance

    def start(self) -> None:
        """Start the GPS provider and background polling worker."""
        with self._lock:
            if self._is_running:
                return

            self._is_running = True
            self._stop_event.clear()
            self.provider.start()

            # Immediate first reading
            initial_fix = self.provider.get_location()
            self._latest_fix = initial_fix

            self._thread = threading.Thread(
                target=self._poll_loop,
                name="SharedGPSService-Worker",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Stop background worker and release provider resources."""
        with self._lock:
            if not self._is_running:
                return

            self._is_running = False
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        self.provider.stop()

    def _poll_loop(self) -> None:
        """Background loop continuously updating the latest GPSFix."""
        while not self._stop_event.is_set():
            try:
                fix = self.provider.get_location()
                with self._lock:
                    if fix.valid:
                        self._latest_fix = fix
                    else:
                        # If current fix failed but we had a previous valid fix, keep it but let age increase
                        if not self._latest_fix.valid:
                            self._latest_fix = fix
            except Exception as e:
                with self._lock:
                    if not self._latest_fix.valid:
                        self._latest_fix = GPSFix(
                            source=self.provider.source_name,
                            valid=False,
                            provider=self.provider.name,
                            status="error",
                            error_message=str(e),
                        )

            self._stop_event.wait(self.poll_interval)

    def get_latest_fix(self) -> GPSFix:
        """
        Retrieve the latest GPS fix in a non-blocking, thread-safe manner.
        Checks and sets the stale flag if age exceeds the threshold.
        """
        with self._lock:
            fix = self._latest_fix

            if fix.valid:
                age = fix.age_seconds
                is_stale = age > self.stale_threshold
                # Return updated copy with current age and stale status
                return GPSFix(
                    latitude=fix.latitude,
                    longitude=fix.longitude,
                    altitude=fix.altitude,
                    accuracy_m=fix.accuracy_m,
                    timestamp=fix.timestamp,
                    source=fix.source,
                    valid=fix.valid,
                    stale=is_stale,
                    provider=fix.provider,
                    status="stale" if is_stale else fix.status,
                    error_message=fix.error_message,
                    extra=fix.extra,
                )
            return fix

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def active_provider_name(self) -> str:
        return self.provider.name
