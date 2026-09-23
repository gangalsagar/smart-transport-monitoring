from abc import ABC, abstractmethod
from shared.gps.gps_fix import GPSFix


class GPSProvider(ABC):
    """
    Abstract interface for location providers.
    All location backends (Windows Laptop, Mobile Bridge, Serial GNSS)
    must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g. 'laptop', 'mobile', 'simulated')."""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Origin label for alert telemetry metadata."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Initialize and start the provider resources."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Release provider resources cleanly."""
        pass

    @abstractmethod
    def get_location(self) -> GPSFix:
        """
        Query or retrieve the latest location fix from the hardware/service.
        Must return a structured GPSFix and NEVER raise uncaught exceptions.
        """
        pass
