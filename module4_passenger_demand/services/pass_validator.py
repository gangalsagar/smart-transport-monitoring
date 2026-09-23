import logging
from datetime import datetime, date
from typing import Optional

from module4_passenger_demand.models.passenger_models import PassRecord, ValidationResult
from module4_passenger_demand.providers.pass_registry import PassRegistry

logger = logging.getLogger(__name__)


class PassValidator:
    """
    Validates physical bus-pass numbers against the PassRegistry.
    
    Checks performed:
    1. Pass existence in registry (pass_not_found)
    2. Pass status (active vs suspended/cancelled)
    3. Pass temporal validity range (pass_expired / pass_not_yet_active)
    4. Route entitlement checks (route_not_allowed)
    """
    def __init__(
        self,
        registry: PassRegistry,
        strict_route_validation: bool = True,
        strict_date_validation: bool = True,
    ):
        self.registry = registry
        self.strict_route_validation = strict_route_validation
        self.strict_date_validation = strict_date_validation

    def validate_pass(
        self,
        pass_id: str,
        current_route_id: Optional[str] = None,
        check_time: Optional[datetime] = None,
    ) -> ValidationResult:
        if not pass_id or not pass_id.strip():
            return ValidationResult(
                status="invalid",
                reason="pass_not_found"
            )

        clean_id = pass_id.strip().upper()
        record: Optional[PassRecord] = self.registry.lookup(clean_id)

        # STEP 1: Pass exists in registry
        if not record:
            return ValidationResult(
                status="invalid",
                reason="pass_not_found"
            )

        # Status check
        if record.status.lower() in ("cancelled", "suspended"):
            return ValidationResult(
                status="invalid",
                reason=f"pass_{record.status.lower()}",
                pass_record=record
            )

        # STEP 2: Temporal validity checks
        effective_date = (check_time or datetime.now()).date()

        if self.strict_date_validation:
            if record.valid_from and effective_date < record.valid_from:
                return ValidationResult(
                    status="invalid",
                    reason="pass_not_yet_active",
                    pass_record=record
                )
            if record.valid_until and effective_date > record.valid_until:
                return ValidationResult(
                    status="invalid",
                    reason="pass_expired",
                    pass_record=record
                )

        # STEP 3: Route eligibility check
        if self.strict_route_validation and current_route_id and record.allowed_routes:
            allowed_upper = [r.strip().upper() for r in record.allowed_routes]
            if current_route_id.strip().upper() not in allowed_upper:
                return ValidationResult(
                    status="invalid",
                    reason="route_not_allowed",
                    pass_record=record
                )

        # STEP 4: All checks passed
        return ValidationResult(
            status="valid",
            reason="pass_verified",
            pass_record=record
        )
