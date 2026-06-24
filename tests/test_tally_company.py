"""
Tests for Tally Company Management
Company locking, fingerprinting, and backup restore detection
"""
import pytest
import tempfile
from pathlib import Path
from tallybridge_agent.core.config import ConfigManager
from tallybridge_agent.tally.company import (
    Company,
    CompanyFingerprint,
    CompanyManager,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_company.db"
        yield str(db_path)


@pytest.fixture
def config_manager(temp_db):
    """Create a ConfigManager instance"""
    config = ConfigManager(temp_db)
    yield config
    config.close()


@pytest.fixture
def company_manager(config_manager):
    """Create a CompanyManager instance"""
    return CompanyManager(config_manager)


# ============= CompanyFingerprint Tests =============

def test_company_fingerprint_creation():
    """Test fingerprint creation"""
    fp = CompanyFingerprint(
        name="National Traders",
        pan="ABCD1234E",
        gstin="27ABCD1234E1Z5",
        currency="INR",
        start_date="2020-04-01"
    )
    assert fp.name == "National Traders"
    assert fp.pan == "ABCD1234E"


def test_company_fingerprint_to_dict():
    """Test fingerprint to_dict conversion"""
    fp = CompanyFingerprint(
        name="National Traders",
        pan="ABCD1234E",
        gstin="27ABCD1234E1Z5"
    )
    fp_dict = fp.to_dict()
    assert fp_dict["name"] == "National Traders"
    assert fp_dict["pan"] == "ABCD1234E"


def test_company_fingerprint_high_confidence_match():
    """Test HIGH confidence matching (all 5 fields)"""
    fp1 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2020-01-01"
    )
    fp2 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2020-01-01"
    )
    assert fp1.matches(fp2, confidence_level="HIGH") is True


def test_company_fingerprint_high_confidence_no_match_date_diff():
    """Test HIGH confidence fails when date differs"""
    fp1 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2020-01-01"
    )
    fp2 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2021-01-01"  # Different date
    )
    assert fp1.matches(fp2, confidence_level="HIGH") is False


def test_company_fingerprint_medium_confidence_match():
    """Test MEDIUM confidence (PAN + GSTIN + name, date can differ)"""
    fp1 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2020-01-01"
    )
    fp2 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2021-01-01"  # Different date
    )
    assert fp1.matches(fp2, confidence_level="MEDIUM") is True


def test_company_fingerprint_low_confidence_match():
    """Test LOW confidence (name only)"""
    fp1 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001"
    )
    fp2 = CompanyFingerprint(
        name="Company A",
        pan="PAN999",  # Different PAN
        gstin="GSTIN999"  # Different GSTIN
    )
    assert fp1.matches(fp2, confidence_level="LOW") is True


def test_company_fingerprint_no_match():
    """Test when fingerprints don't match"""
    fp1 = CompanyFingerprint(name="Company A", pan="PAN001")
    fp2 = CompanyFingerprint(name="Company B", pan="PAN002")
    assert fp1.matches(fp2, confidence_level="LOW") is False


# ============= Company Class Tests =============

def test_company_creation():
    """Test company creation"""
    company = Company(
        name="National Traders",
        guid="550e8400-e29b-41d4-a716-446655440000",
        is_tally_prime=True
    )
    assert company.name == "National Traders"
    assert company.guid == "550e8400-e29b-41d4-a716-446655440000"
    assert company.is_tally_prime is True


def test_company_to_dict():
    """Test company to_dict conversion"""
    fp = CompanyFingerprint(name="Company A", pan="PAN001")
    company = Company(
        name="Company A",
        guid="guid-123",
        is_tally_prime=True,
        fingerprint=fp,
        tally_version="PRIME_4X"
    )
    company_dict = company.to_dict()
    assert company_dict["name"] == "Company A"
    assert company_dict["guid"] == "guid-123"
    assert company_dict["is_tally_prime"] is True
    assert company_dict["tally_version"] == "PRIME_4X"


# ============= CompanyManager Tests =============

def test_surrogate_guid_generation(company_manager):
    """Test surrogate GUID generation for ERP 9 companies"""
    guid1 = company_manager.generate_surrogate_guid("National Traders", "ABCD1234E")
    guid2 = company_manager.generate_surrogate_guid("National Traders", "ABCD1234E")

    # Should be same for same input (deterministic)
    assert guid1 == guid2

    # Should be UUID format
    assert len(guid1) == 36
    assert guid1.count("-") == 4


def test_surrogate_guid_different_for_different_companies(company_manager):
    """Test that different companies get different GUIDs"""
    guid1 = company_manager.generate_surrogate_guid("Company A", "PAN001")
    guid2 = company_manager.generate_surrogate_guid("Company B", "PAN002")

    assert guid1 != guid2


def test_lock_company(company_manager, config_manager):
    """Test locking a company"""
    company = Company(
        name="National Traders",
        guid="550e8400-e29b-41d4-a716-446655440000",
        is_tally_prime=True
    )
    fingerprint = CompanyFingerprint(
        name="National Traders",
        pan="ABCD1234E",
        gstin="27ABCD1234E1Z5",
        currency="INR",
        start_date="2020-04-01"
    )

    result = company_manager.lock_company(company, fingerprint, "PRIME_4X")
    assert result is True

    # Verify it was stored
    assert config_manager.company_guid == "550e8400-e29b-41d4-a716-446655440000"
    assert config_manager.tally_version == "PRIME_4X"


def test_get_locked_company(company_manager):
    """Test retrieving a locked company"""
    # Lock a company
    company = Company(
        name="National Traders",
        guid="550e8400-e29b-41d4-a716-446655440000",
        is_tally_prime=True
    )
    fingerprint = CompanyFingerprint(
        name="National Traders",
        pan="ABCD1234E",
        gstin="27ABCD1234E1Z5"
    )
    company_manager.lock_company(company, fingerprint, "PRIME_4X")

    # Retrieve it
    locked = company_manager.get_locked_company()
    assert locked is not None
    assert locked.name == "National Traders"
    assert locked.guid == "550e8400-e29b-41d4-a716-446655440000"
    assert locked.is_tally_prime is True


def test_no_locked_company_initially(company_manager):
    """Test that no company is locked initially"""
    locked = company_manager.get_locked_company()
    assert locked is None


def test_detect_guid_migration_no_change(company_manager):
    """Test migration detection when fingerprint hasn't changed"""
    # Lock company
    fp1 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2020-01-01"
    )
    company = Company(name="Company A", guid="guid-1")
    company_manager.lock_company(company, fp1, "PRIME_4X")

    # Check again with same fingerprint
    fp2 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2020-01-01"
    )
    migration = company_manager.detect_guid_migration(fp2)
    assert migration is None  # No migration needed


def test_detect_guid_migration_medium_confidence(company_manager):
    """Test migration detection with MEDIUM confidence (date changed)"""
    # Lock company
    fp1 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2020-01-01"
    )
    company = Company(name="Company A", guid="guid-1")
    company_manager.lock_company(company, fp1)

    # Check with different date
    fp2 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001",
        currency="INR",
        start_date="2021-01-01"  # Date changed (possible backup restore)
    )
    migration = company_manager.detect_guid_migration(fp2)
    assert migration is not None
    assert migration["migration_confidence"] == "MEDIUM"
    assert migration["auto_migrate"] is True


def test_detect_guid_migration_low_confidence(company_manager):
    """Test migration detection with LOW confidence (only name matches)"""
    # Lock company
    fp1 = CompanyFingerprint(
        name="Company A",
        pan="PAN001",
        gstin="GSTIN001"
    )
    company = Company(name="Company A", guid="guid-1")
    company_manager.lock_company(company, fp1)

    # Check with completely different PAN/GSTIN
    fp2 = CompanyFingerprint(
        name="Company A",
        pan="PAN999",
        gstin="GSTIN999"
    )
    migration = company_manager.detect_guid_migration(fp2)
    assert migration is not None
    assert migration["migration_confidence"] == "LOW"
    assert migration["auto_migrate"] is False
    assert migration["requires_manual_review"] is True


def test_enumerate_companies(company_manager):
    """Test enumerating companies from Tally response"""
    companies_data = [
        {
            "name": "National Traders",
            "guid": "550e8400-e29b-41d4-a716-446655440000"
        },
        {
            "name": "ABC Traders",
            # No GUID (ERP 9)
        }
    ]

    companies = company_manager.enumerate_companies(companies_data)
    assert len(companies) == 2

    # First company (TallyPrime)
    assert companies[0].name == "National Traders"
    assert companies[0].guid == "550e8400-e29b-41d4-a716-446655440000"
    assert companies[0].is_tally_prime is True

    # Second company (ERP 9 with surrogate GUID)
    assert companies[1].name == "ABC Traders"
    assert len(companies[1].guid) == 36  # UUID format
    assert companies[1].is_tally_prime is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
