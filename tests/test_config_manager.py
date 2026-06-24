"""
Tests for ConfigManager
Verifies typed configuration storage and retrieval
"""
import pytest
import tempfile
from pathlib import Path
from tallybridge_agent.core.config import ConfigManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_config.db"
        yield str(db_path)


@pytest.fixture
def config_manager(temp_db):
    """Create a ConfigManager instance with automatic cleanup"""
    config = ConfigManager(temp_db)
    yield config
    config.close()


def test_config_manager_initialization(config_manager):
    """Test that ConfigManager can be initialized"""
    assert config_manager.db_path is not None


def test_config_set_get_string(config_manager):
    """Test setting and getting string values"""
    config = config_manager

    # Set a string value
    config.set("test_key", "test_value")

    # Get it back
    value = config.get("test_key", expected_type="string")
    assert value == "test_value"


def test_config_set_get_int(config_manager):
    """Test setting and getting integer values"""
    config = config_manager

    # Set an integer
    config.set("port", 9000, value_type="int")

    # Get it back as int
    value = config.get("port", expected_type="int")
    assert value == 9000
    assert isinstance(value, int)


def test_config_set_get_bool(config_manager):
    """Test setting and getting boolean values"""
    config = config_manager

    config.set("is_active", True, value_type="bool")
    value = config.get("is_active", expected_type="bool")
    assert value is True

    config.set("is_active", False, value_type="bool")
    value = config.get("is_active", expected_type="bool")
    assert value is False


def test_config_set_get_json(config_manager):
    """Test setting and getting JSON (dict/list) values"""
    config = config_manager

    test_dict = {"name": "Company", "pan": "ABCD1234E", "gstin": "27ABCD1234E1Z5"}
    config.set("company_info", test_dict, value_type="json")

    value = config.get("company_info", expected_type="json")
    assert value == test_dict


def test_config_typed_accessors(config_manager):
    """Test typed property accessors"""
    config = config_manager

    # Test client_id
    config.set_client_id("client-123")
    assert config.client_id == "client-123"

    # Test tally_port
    config.set_tally_port(9000)
    assert config.tally_port == 9000

    # Test company_guid
    config.set_company_guid("550e8400-e29b-41d4-a716-446655440000")
    assert config.company_guid == "550e8400-e29b-41d4-a716-446655440000"


def test_config_api_key_hash(config_manager):
    """Test API key hashing (never storing raw key)"""
    config = config_manager

    api_key = "super_secret_key_12345"
    config.set_api_key_hash(api_key)

    # Should be stored as hash
    stored_hash = config.api_key_hash
    assert stored_hash is not None
    assert stored_hash != api_key
    assert len(stored_hash) == 64  # SHA256 hex digest


def test_config_defaults(config_manager):
    """Test default values for unconfigured keys"""
    config = config_manager

    # Should return default values for unset keys
    assert config.tally_host == "localhost"
    assert config.tally_port == 9000
    assert config.lookback_days == 45
    assert config.sync_scope_years == 3


def test_config_get_all(config_manager):
    """Test retrieving all configuration"""
    config = config_manager

    config.set_client_id("client-123")
    config.set_tally_port(9000)
    config.set_company_guid("uuid-123")

    all_config = config.get_all()
    assert "client_id" in all_config
    assert all_config["client_id"] == "client-123"
    assert all_config["tally_port"] == 9000


def test_config_delete(config_manager):
    """Test deleting configuration values"""
    config = config_manager

    config.set("temp_key", "temp_value")
    assert config.get("temp_key", expected_type="string") == "temp_value"

    # Delete it
    result = config.delete("temp_key")
    assert result is True

    # Should return default now
    assert config.get("temp_key", default="gone", expected_type="string") == "gone"


def test_config_fingerprint(config_manager):
    """Test company fingerprint storage"""
    config = config_manager

    fingerprint = {
        "name": "National Traders",
        "pan": "ABCD1234E",
        "gstin": "27ABCD1234E1Z5",
        "currency": "INR",
        "start_date": "2020-04-01"
    }

    config.set_company_fingerprint(fingerprint)
    retrieved = config.get_company_fingerprint()

    assert retrieved["name"] == "National Traders"
    assert retrieved["pan"] == "ABCD1234E"
    assert retrieved["gstin"] == "27ABCD1234E1Z5"


def test_config_persistence(temp_db):
    """Test that config persists across manager instances"""
    config1 = ConfigManager(temp_db)
    config1.set_client_id("client-persist-test")
    config1.close()

    # Create a new manager instance with same DB
    config2 = ConfigManager(temp_db)
    assert config2.client_id == "client-persist-test"
    config2.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
