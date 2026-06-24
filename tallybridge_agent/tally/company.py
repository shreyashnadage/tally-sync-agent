"""
Tally Company Management
Handle company enumeration, GUID locking, fingerprinting, and multi-company scenarios
"""
import hashlib
import json
from typing import Optional, Dict, List
from datetime import datetime
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CompanyFingerprint:
    """
    Fingerprint for detecting backup restores and company identity changes.
    Used to determine if a GUID migration is needed.
    """
    name: str
    pan: Optional[str] = None
    gstin: Optional[str] = None
    currency: str = "INR"
    start_date: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON"""
        return json.dumps(self.to_dict())

    def matches(self, other: "CompanyFingerprint", confidence_level: str = "HIGH") -> bool:
        """
        Check if another fingerprint matches this one

        Args:
            other: Another CompanyFingerprint to compare
            confidence_level: "HIGH" (all 5 fields match), "MEDIUM" (PAN + GSTIN + name),
                             "LOW" (only name)

        Returns:
            True if fingerprints match at specified confidence level
        """
        if confidence_level == "HIGH":
            # All 5 fields must match
            return (
                self.name == other.name and
                self.pan == other.pan and
                self.gstin == other.gstin and
                self.currency == other.currency and
                self.start_date == other.start_date
            )
        elif confidence_level == "MEDIUM":
            # PAN + GSTIN + name match, date can differ
            return (
                self.name == other.name and
                self.pan == other.pan and
                self.gstin == other.gstin
            )
        elif confidence_level == "LOW":
            # Only name matches
            return self.name == other.name
        else:
            return False


@dataclass
class Company:
    """Represents a Tally company"""
    name: str
    guid: str  # Company GUID (from TallyPrime) or generated surrogate key
    is_tally_prime: bool = False
    fingerprint: Optional[CompanyFingerprint] = None
    tally_version: Optional[str] = None
    locked_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary (safe for JSON serialization)"""
        data = {
            "name": self.name,
            "guid": self.guid,
            "is_tally_prime": self.is_tally_prime,
            "tally_version": self.tally_version,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "fingerprint": self.fingerprint.to_dict() if self.fingerprint else None,
        }
        return data


class CompanyManager:
    """
    Manage company identity, locking, and fingerprinting.
    Handles GUID stability detection and backup restore scenarios.
    """

    def __init__(self, config_manager):
        """
        Initialize company manager

        Args:
            config_manager: ConfigManager instance for persisting company info
        """
        self.config = config_manager

    def generate_surrogate_guid(self, company_name: str, pan: Optional[str] = None) -> str:
        """
        Generate a surrogate GUID for ERP 9 companies (which don't have native GUIDs).
        Uses company name and PAN to create a deterministic UUID-like string.

        Args:
            company_name: Company name
            pan: PAN (optional, for better uniqueness)

        Returns:
            Surrogate GUID in UUID format
        """
        # Combine name and PAN for hash
        identifier = f"{company_name}:{pan or 'NO_PAN'}"
        hash_obj = hashlib.sha256(identifier.encode())
        hash_hex = hash_obj.hexdigest()

        # Format as UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        guid = f"{hash_hex[0:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"
        return guid

    def lock_company(
        self,
        company: Company,
        fingerprint: CompanyFingerprint,
        tally_version: Optional[str] = None
    ) -> bool:
        """
        Lock a company for exclusive syncing.
        This creates a fingerprint that allows us to detect backup restores.

        Args:
            company: Company to lock
            fingerprint: Company fingerprint for GUID stability checking
            tally_version: Detected Tally version (e.g., "ERP9_R6", "PRIME_4X")

        Returns:
            True if lock successful
        """
        try:
            # Store company info
            self.config.set_company_guid(company.guid)
            self.config.set("company_name", company.name)
            self.config.set("is_tally_prime", company.is_tally_prime, value_type="bool")

            # Store fingerprint
            self.config.set_company_fingerprint(fingerprint.to_dict())

            # Store Tally version
            if tally_version:
                self.config.set_tally_version(tally_version)

            logger.info(f"Locked company: {company.name} (GUID: {company.guid})")
            return True

        except Exception as e:
            logger.error(f"Failed to lock company: {e}")
            return False

    def get_locked_company(self) -> Optional[Company]:
        """
        Get currently locked company

        Returns:
            Company object if one is locked, None otherwise
        """
        guid = self.config.company_guid
        if not guid:
            return None

        name = self.config.get("company_name", expected_type="string")
        is_prime = self.config.get("is_tally_prime", default=False, expected_type="bool")
        tally_version = self.config.tally_version
        fingerprint_dict = self.config.get_company_fingerprint()

        fingerprint = CompanyFingerprint(**fingerprint_dict) if fingerprint_dict else None

        return Company(
            name=name or "Unknown",
            guid=guid,
            is_tally_prime=is_prime,
            fingerprint=fingerprint,
            tally_version=tally_version
        )

    def detect_guid_migration(self, current_fingerprint: CompanyFingerprint) -> Optional[Dict]:
        """
        Detect if a backup restore or company change occurred.
        Returns migration details if a change is detected.

        Args:
            current_fingerprint: Current company fingerprint from Tally

        Returns:
            Dict with migration info if change detected, None if no change
        """
        stored_fingerprint_dict = self.config.get_company_fingerprint()
        if not stored_fingerprint_dict:
            # No stored fingerprint, this is first lock
            return None

        stored_fingerprint = CompanyFingerprint(**stored_fingerprint_dict)

        # Check confidence levels in descending order
        if current_fingerprint.matches(stored_fingerprint, confidence_level="HIGH"):
            # High confidence match - no migration needed
            return None

        elif current_fingerprint.matches(stored_fingerprint, confidence_level="MEDIUM"):
            # Medium confidence - auto-migrate
            return {
                "migration_confidence": "MEDIUM",
                "change_detected": "Date or currency changed",
                "auto_migrate": True
            }

        elif current_fingerprint.matches(stored_fingerprint, confidence_level="LOW"):
            # Low confidence - requires manual review
            return {
                "migration_confidence": "LOW",
                "change_detected": "Only name matches; PAN/GSTIN differ",
                "auto_migrate": False,
                "requires_manual_review": True
            }

        else:
            # No match at any level
            return {
                "migration_confidence": "NONE",
                "change_detected": "Company appears to be different (no matching fields)",
                "auto_migrate": False,
                "requires_manual_review": True
            }

    def enumerate_companies(self, companies_data: List[Dict]) -> List[Company]:
        """
        Parse and enumerate companies from Tally response.

        Args:
            companies_data: List of company dictionaries from Tally XML response
                           Format: [{"name": "...", "guid": "..."}, ...]

        Returns:
            List of Company objects
        """
        companies = []

        for company_data in companies_data:
            name = company_data.get("name", "Unknown")
            guid = company_data.get("guid")

            # For ERP 9 (no native GUID), generate surrogate
            if not guid:
                pan = company_data.get("pan")
                guid = self.generate_surrogate_guid(name, pan)

            company = Company(
                name=name,
                guid=guid,
                is_tally_prime=bool(company_data.get("guid")),  # If has GUID, it's TallyPrime
            )
            companies.append(company)

        return companies
