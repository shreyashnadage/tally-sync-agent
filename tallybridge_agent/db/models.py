"""
TallyBridge Agent Database Models
SQLAlchemy models for local SQLite DB with SQLCipher encryption
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SchemaVersion(Base):
    """Track database schema migrations"""
    __tablename__ = "schema_version"

    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False, unique=True)
    description = Column(String(255))
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Config(Base):
    """Agent configuration and secrets"""
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text)
    value_type = Column(String(50))  # "string", "int", "bool", "json"
    encrypted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @staticmethod
    def get_key_names():
        """Config key names referenced in the codebase"""
        return {
            # Authentication
            "api_key_hash": "SHA256 hash of API key for identity verification",
            "client_id": "Cloud client ID",
            "company_guid": "Tally company GUID (single company mode)",

            # Tally Connection
            "tally_host": "Tally server host (default: localhost)",
            "tally_port": "Tally HTTP server port (default: 9000)",
            "tally_version": "Detected Tally version (ERP9_R6, PRIME_1X, PRIME_4X)",

            # Sync Configuration
            "lookback_days": "Sync lookback window in days (default: 45)",
            "sync_scope_years": "Initial sync scope in financial years (default: 3)",
            "sync_window_start": "Off-peak window start time (HH:MM)",
            "sync_window_end": "Off-peak window end time (HH:MM)",

            # Company Fingerprint (for GUID stability)
            "company_fingerprint_name": "Company name at last lock",
            "company_fingerprint_pan": "Company PAN at last lock",
            "company_fingerprint_gstin": "Company GSTIN at last lock",
            "company_fingerprint_currency": "Company currency at last lock",
            "company_fingerprint_start_date": "Company start date at last lock",
        }


class SyncState(Base):
    """Track sync state for resumable, incremental synchronization"""
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True)
    company_guid = Column(String(36), nullable=False, index=True)
    financial_year = Column(String(10))  # Format: "2024-25"
    data_type = Column(String(50), nullable=False)  # "LEDGER", "GROUP", "VOUCHERTYPE", "SALES_VOUCHER", etc.

    # Incremental tracking
    max_alterid = Column(Integer, default=0)
    max_date = Column(DateTime)

    # Status tracking
    status = Column(String(50), default="NEVER_SYNCED")  # NEVER_SYNCED, IN_PROGRESS, COMPLETE, STALE
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)

    # Metadata
    record_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OutboundQueue(Base):
    """Queue of data to be sent to cloud, with retry logic"""
    __tablename__ = "outbound_queue"

    id = Column(Integer, primary_key=True)
    company_guid = Column(String(36), nullable=False, index=True)

    # Queue metadata
    queue_type = Column(String(50), nullable=False)  # "MASTER_SYNC", "VOUCHER_SYNC", "STATUS_UPDATE"
    status = Column(String(50), default="PENDING")  # PENDING, IN_FLIGHT, DELIVERED, STALE_PENDING, FAILED

    # Payload (encrypted before storage)
    payload_json = Column(Text, nullable=False)
    payload_size_bytes = Column(Integer)

    # Retry tracking
    attempt_count = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    # Cloud response
    cloud_status_code = Column(Integer, nullable=True)
    cloud_response_json = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)


class InboundCommands(Base):
    """Commands received from cloud, queued for execution"""
    __tablename__ = "inbound_commands"

    id = Column(Integer, primary_key=True)
    company_guid = Column(String(36), nullable=False, index=True)

    # Command metadata
    command_id = Column(String(36), unique=True, nullable=False)  # Message UUID from cloud
    command_type = Column(String(50), nullable=False)  # TRIGGER_SYNC, FETCH_VOUCHER, HEALTH_CHECK, etc.

    # Payload
    payload_json = Column(Text)

    # Execution status
    status = Column(String(50), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    response_json = Column(Text, nullable=True)

    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    executed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Immutable append-only audit log with chained hashing"""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    company_guid = Column(String(36), nullable=False, index=True)

    # Event metadata
    event_type = Column(String(50), nullable=False, index=True)
    event_severity = Column(String(20))  # "INFO", "WARNING", "ERROR", "CRITICAL"

    # Event details (never financial data)
    event_data_json = Column(Text)

    # Chained hashing for integrity
    previous_hash = Column(String(64))
    event_hash = Column(String(64), nullable=False, unique=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class CompanyInfo(Base):
    """Cached company information from Tally"""
    __tablename__ = "company_info"

    id = Column(Integer, primary_key=True)
    company_guid = Column(String(36), unique=True, nullable=False, index=True)

    # Company identity
    company_name = Column(String(255), nullable=False)
    pan = Column(String(10))
    gstin = Column(String(15))

    # Financial year info
    financial_year_start_date = Column(DateTime)
    financial_year_end_date = Column(DateTime)

    # Tally version when company was registered
    tally_version = Column(String(50))

    # Lock time (for stability checking)
    locked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MigrationHistory(Base):
    """Track schema migrations for database versioning"""
    __tablename__ = "migration_history"

    id = Column(Integer, primary_key=True)
    migration_name = Column(String(255), unique=True, nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
