"""
Configuration Management
Handles reading/writing config from encrypted SQLite DB with typed accessors
"""
import json
import hashlib
from typing import Any, Optional, Dict
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from tallybridge_agent.db.models import Base, Config


class ConfigManager:
    """Typed configuration accessor for the agent"""

    def __init__(self, db_path: str, encryption_key: Optional[str] = None):
        """
        Initialize config manager with SQLCipher database

        Args:
            db_path: Path to SQLite database file
            encryption_key: SQLCipher encryption passphrase (if None, unencrypted)
        """
        self.db_path = Path(db_path)
        self.encryption_key = encryption_key
        self._setup_database()

    def _setup_database(self):
        """Set up SQLCipher connection and create tables"""
        # Build connection string
        if self.encryption_key:
            # SQLCipher connection with encryption
            connection_string = f"sqlite+pysqlcipher://:{self.encryption_key}@/{self.db_path}"
        else:
            # Plain SQLite (for testing)
            connection_string = f"sqlite:///{self.db_path}"

        # Create engine
        self.engine = create_engine(
            connection_string,
            connect_args={"check_same_thread": False} if not self.encryption_key else {},
            echo=False
        )

        # Configure SQLCipher-specific pragmas
        if self.encryption_key:
            @event.listens_for(self.engine, "connect")
            def set_sqlcipher_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA secure_delete=ON")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()

        # Create tables
        Base.metadata.create_all(self.engine)

        # Session factory
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def _get_session(self) -> Session:
        """Get a new database session"""
        return self.Session()

    def close(self):
        """Close database connection"""
        self.engine.dispose()

    def set(self, key: str, value: Any, value_type: Optional[str] = None, encrypted: bool = False) -> None:
        """
        Set a configuration value

        Args:
            key: Config key name
            value: Config value (will be serialized based on value_type)
            value_type: "string", "int", "bool", "json" (auto-detected if None)
            encrypted: Mark as encrypted (for sensitive values)
        """
        if value_type is None:
            # Auto-detect type
            if isinstance(value, bool):
                value_type = "bool"
                value_str = "true" if value else "false"
            elif isinstance(value, int):
                value_type = "int"
                value_str = str(value)
            elif isinstance(value, (dict, list)):
                value_type = "json"
                value_str = json.dumps(value)
            else:
                value_type = "string"
                value_str = str(value)
        else:
            # Explicit type conversion
            if value_type == "int":
                value_str = str(int(value))
            elif value_type == "bool":
                value_str = "true" if value else "false"
            elif value_type == "json":
                value_str = json.dumps(value)
            else:
                value_str = str(value)

        session = self._get_session()
        try:
            # Try to update existing
            config_row = session.query(Config).filter(Config.key == key).first()
            if config_row:
                config_row.value = value_str
                config_row.value_type = value_type
                config_row.encrypted = encrypted
            else:
                # Create new
                config_row = Config(
                    key=key,
                    value=value_str,
                    value_type=value_type,
                    encrypted=encrypted
                )
                session.add(config_row)
            session.commit()
        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to set config key '{key}': {e}")
        finally:
            session.close()

    def get(self, key: str, default: Any = None, expected_type: Optional[str] = None) -> Any:
        """
        Get a configuration value with type conversion

        Args:
            key: Config key name
            default: Default value if key not found
            expected_type: "string", "int", "bool", "json" (uses stored type if None)

        Returns:
            Typed configuration value
        """
        session = self._get_session()
        try:
            config_row = session.query(Config).filter(Config.key == key).first()
            if not config_row:
                return default

            value_str = config_row.value
            value_type = expected_type or config_row.value_type

            # Type conversion
            if value_type == "int":
                return int(value_str) if value_str else (default or 0)
            elif value_type == "bool":
                return value_str.lower() in ("true", "1", "yes") if value_str else (default or False)
            elif value_type == "json":
                return json.loads(value_str) if value_str else (default or {})
            else:
                return value_str or default

        finally:
            session.close()

    def delete(self, key: str) -> bool:
        """Delete a configuration key"""
        session = self._get_session()
        try:
            config_row = session.query(Config).filter(Config.key == key).first()
            if config_row:
                session.delete(config_row)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        session = self._get_session()
        try:
            rows = session.query(Config).all()
            result = {}
            for row in rows:
                value = self.get(row.key, expected_type=row.value_type)
                result[row.key] = value
            return result
        finally:
            session.close()

    # Typed accessors for common keys
    @property
    def api_key_hash(self) -> Optional[str]:
        """Get stored API key hash (for identity verification only, not the key itself)"""
        return self.get("api_key_hash", expected_type="string")

    def set_api_key_hash(self, api_key: str):
        """Store SHA256 hash of API key (never store the raw key)"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self.set("api_key_hash", key_hash, value_type="string", encrypted=False)

    @property
    def client_id(self) -> Optional[str]:
        return self.get("client_id", expected_type="string")

    def set_client_id(self, value: str):
        self.set("client_id", value, value_type="string")

    @property
    def company_guid(self) -> Optional[str]:
        return self.get("company_guid", expected_type="string")

    def set_company_guid(self, value: str):
        self.set("company_guid", value, value_type="string")

    @property
    def tally_host(self) -> str:
        return self.get("tally_host", default="localhost", expected_type="string")

    def set_tally_host(self, value: str):
        self.set("tally_host", value, value_type="string")

    @property
    def tally_port(self) -> int:
        return self.get("tally_port", default=9000, expected_type="int")

    def set_tally_port(self, value: int):
        self.set("tally_port", value, value_type="int")

    @property
    def tally_version(self) -> Optional[str]:
        return self.get("tally_version", expected_type="string")

    def set_tally_version(self, value: str):
        self.set("tally_version", value, value_type="string")

    @property
    def lookback_days(self) -> int:
        return self.get("lookback_days", default=45, expected_type="int")

    def set_lookback_days(self, value: int):
        self.set("lookback_days", value, value_type="int")

    @property
    def sync_scope_years(self) -> int:
        return self.get("sync_scope_years", default=3, expected_type="int")

    def set_sync_scope_years(self, value: int):
        self.set("sync_scope_years", value, value_type="int")

    @property
    def sync_window_start(self) -> str:
        return self.get("sync_window_start", default="19:00", expected_type="string")

    def set_sync_window_start(self, value: str):
        self.set("sync_window_start", value, value_type="string")

    @property
    def sync_window_end(self) -> str:
        return self.get("sync_window_end", default="08:00", expected_type="string")

    def set_sync_window_end(self, value: str):
        self.set("sync_window_end", value, value_type="string")

    def get_company_fingerprint(self) -> Dict[str, Any]:
        """Get stored company fingerprint"""
        return {
            "name": self.get("company_fingerprint_name", expected_type="string"),
            "pan": self.get("company_fingerprint_pan", expected_type="string"),
            "gstin": self.get("company_fingerprint_gstin", expected_type="string"),
            "currency": self.get("company_fingerprint_currency", expected_type="string"),
            "start_date": self.get("company_fingerprint_start_date", expected_type="string"),
        }

    def set_company_fingerprint(self, fingerprint: Dict[str, Any]):
        """Store company fingerprint for GUID stability checking"""
        self.set("company_fingerprint_name", fingerprint.get("name"), value_type="string")
        self.set("company_fingerprint_pan", fingerprint.get("pan"), value_type="string")
        self.set("company_fingerprint_gstin", fingerprint.get("gstin"), value_type="string")
        self.set("company_fingerprint_currency", fingerprint.get("currency"), value_type="string")
        self.set("company_fingerprint_start_date", fingerprint.get("start_date"), value_type="string")
