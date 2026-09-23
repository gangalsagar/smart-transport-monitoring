import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, date

from module4_passenger_demand.models.passenger_models import PassRecord

logger = logging.getLogger(__name__)


class PassDataProvider(ABC):
    """
    Abstract interface for retrieving registered bus pass records.
    Decouples the system so user-provided CSV/JSON datasets, mock registries,
    or real municipal Transport Authority databases/REST APIs can be plugged in seamlessly.
    """
    @abstractmethod
    def get_pass(self, pass_id: str) -> Optional[PassRecord]:
        pass

    @abstractmethod
    def all_passes(self) -> List[PassRecord]:
        pass


class FilePassDataProvider(PassDataProvider):
    """
    Loads bus passes from a user-provided CSV or JSON file without modifying source files.
    """
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self._cache: Dict[str, PassRecord] = {}
        self.load()

    def load(self):
        if not self.file_path.exists():
            logger.warning(f"[PassDataProvider] Pass dataset file not found at {self.file_path}. Creating fallback entries.")
            self._load_fallbacks()
            return

        suffix = self.file_path.suffix.lower()
        if suffix == ".csv":
            self._load_csv()
        elif suffix == ".json":
            self._load_json()
        else:
            logger.error(f"[PassDataProvider] Unsupported dataset format: {suffix}. Loading fallbacks.")
            self._load_fallbacks()

    def _load_csv(self):
        try:
            with open(self.file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    # Clean keys
                    clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                    
                    # Extract pass ID
                    pass_id = (
                        clean_row.get("pass_id") or
                        clean_row.get("pass_number") or
                        clean_row.get("passid") or
                        clean_row.get("id") or
                        clean_row.get("card_id")
                    )
                    if not pass_id:
                        continue

                    # Dates
                    valid_from = self._parse_date(clean_row.get("valid_from") or clean_row.get("start_date") or clean_row.get("issue_date"))
                    valid_until = self._parse_date(clean_row.get("valid_until") or clean_row.get("expiry_date") or clean_row.get("end_date"))
                    
                    # Allowed routes
                    routes_raw = clean_row.get("allowed_routes") or clean_row.get("routes") or clean_row.get("route_id")
                    allowed_routes = [r.strip().upper() for r in routes_raw.split(",")] if routes_raw else None

                    rec = PassRecord(
                        pass_id=pass_id.strip().upper(),
                        passenger_category=clean_row.get("category", "general"),
                        valid_from=valid_from,
                        valid_until=valid_until,
                        allowed_routes=allowed_routes,
                        status=clean_row.get("status", "active").lower(),
                    )
                    self._cache[rec.pass_id] = rec
                    count += 1
                logger.info(f"[PassDataProvider] Loaded {count} bus passes from {self.file_path}")
        except Exception as e:
            logger.error(f"[PassDataProvider] Failed reading CSV {self.file_path}: {e}")
            self._load_fallbacks()

    def _load_json(self):
        import json
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("passes", [])
                for item in items:
                    rec = PassRecord(**item)
                    self._cache[rec.pass_id.strip().upper()] = rec
        except Exception as e:
            logger.error(f"[PassDataProvider] Failed reading JSON {self.file_path}: {e}")
            self._load_fallbacks()

    def _load_fallbacks(self):
        """
        Initial representative set for immediate testing until user provides real dataset.
        """
        sample_passes = [
            PassRecord(pass_id="P458721", passenger_category="general", valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31), allowed_routes=["25A", "25B", "335E"]),
            PassRecord(pass_id="STU-9081", passenger_category="student", valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31), allowed_routes=["25A", "G4"]),
            PassRecord(pass_id="SNR-3312", passenger_category="senior", valid_from=date(2025, 1, 1), valid_until=date(2027, 1, 1)),
            PassRecord(pass_id="EMP-1044", passenger_category="employee", valid_from=date(2026, 1, 1), valid_until=date(2026, 6, 30), allowed_routes=["25A"]),
            PassRecord(pass_id="EXP-2024", passenger_category="general", valid_from=date(2024, 1, 1), valid_until=date(2024, 12, 31)), # Expired for testing
            PassRecord(pass_id="RTE-RESTRICT", passenger_category="general", valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31), allowed_routes=["ROUTE-999"]), # Invalid for 25A
        ]
        for p in sample_passes:
            self._cache[p.pass_id.upper()] = p

    def _parse_date(self, val: Optional[str]) -> Optional[date]:
        if not val:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(val.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def get_pass(self, pass_id: str) -> Optional[PassRecord]:
        return self._cache.get(pass_id.strip().upper())

    def all_passes(self) -> List[PassRecord]:
        return list(self._cache.values())


class PassRegistry:
    """
    Source of Truth for Bus Pass data.
    Provides singleton or pluggable access to pass records.
    """
    def __init__(self, provider: Optional[PassDataProvider] = None):
        self.provider = provider or FilePassDataProvider("data/passenger/bus_passes.csv")

    def lookup(self, pass_id: str) -> Optional[PassRecord]:
        if not pass_id:
            return None
        return self.provider.get_pass(pass_id)

    def set_provider(self, provider: PassDataProvider):
        self.provider = provider
