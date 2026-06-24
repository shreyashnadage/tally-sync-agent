"""
Tally Pre-flight Check
HTTP probe to verify Tally is accessible and responding correctly
"""
import httpx
from typing import Optional
from enum import Enum
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)


class PreflightStatus(str, Enum):
    """Status of Tally pre-flight check"""
    ACTIVE = "ACTIVE"                  # Tally is running and responding
    PORT_CLOSED = "PORT_CLOSED"        # No connection on configured port
    WRONG_RESPONSE = "WRONG_RESPONSE"  # Port open but not Tally XML response
    TIMEOUT = "TIMEOUT"                # Connection timeout
    ERROR = "ERROR"                    # Other error


class TallyPreflight:
    """
    Pre-flight check for Tally HTTP server availability.
    Probes the configured host:port and validates response is Tally XML.
    """

    def __init__(self, host: str = "localhost", port: int = 9000, timeout: float = 3.0):
        """
        Initialize pre-flight checker

        Args:
            host: Tally server host (default: localhost)
            port: Tally HTTP server port (default: 9000)
            timeout: HTTP request timeout in seconds (default: 3.0)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"

    def check(self) -> tuple[PreflightStatus, Optional[str]]:
        """
        Check if Tally is accessible

        Returns:
            Tuple of (PreflightStatus, error_message)
            error_message is None if status is ACTIVE
        """
        try:
            # Create a minimal Tally XML request to get company list
            # This helps verify it's actually Tally responding
            request_xml = """<?xml version="1.0" encoding="utf-8"?>
<ENVELOPE RequestType="Command">
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>List</TALLYREQUEST>
        <TYPE>Collection</TYPE>
    </HEADER>
    <BODY>
        <FETCH>
            <TYPE>Company</TYPE>
        </FETCH>
    </BODY>
</ENVELOPE>"""

            response = httpx.post(
                self.base_url,
                content=request_xml,
                headers={"Content-Type": "application/xml"},
                timeout=self.timeout
            )

            # Check if response is valid XML and looks like Tally
            if response.status_code != 200:
                return (
                    PreflightStatus.WRONG_RESPONSE,
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )

            # Try to parse as XML
            try:
                root = ET.fromstring(response.text)
                # Check for Tally-specific XML elements
                # Tally responses typically have ENVELOPE or RESPONSE elements
                if root.tag in ("ENVELOPE", "RESPONSE") or "TALLYRESPONSE" in response.text:
                    logger.info(f"Tally pre-flight check PASSED: {self.host}:{self.port}")
                    return (PreflightStatus.ACTIVE, None)
                else:
                    return (
                        PreflightStatus.WRONG_RESPONSE,
                        f"Response is XML but not Tally format. Root tag: {root.tag}"
                    )
            except ET.ParseError as e:
                return (
                    PreflightStatus.WRONG_RESPONSE,
                    f"Response is not valid XML: {str(e)[:100]}"
                )

        except httpx.ConnectError as e:
            error_msg = str(e)
            if "refused" in error_msg.lower() or "failed" in error_msg.lower():
                return (PreflightStatus.PORT_CLOSED, f"Connection refused: {error_msg[:100]}")
            return (PreflightStatus.ERROR, f"Connection error: {error_msg[:100]}")

        except httpx.TimeoutException:
            return (PreflightStatus.TIMEOUT, "Request timeout (> 3 seconds)")

        except httpx.RequestError as e:
            return (PreflightStatus.ERROR, f"Request error: {str(e)[:100]}")

        except Exception as e:
            logger.error(f"Unexpected error in preflight check: {e}", exc_info=True)
            return (PreflightStatus.ERROR, f"Unexpected error: {str(e)[:100]}")

    def is_accessible(self) -> bool:
        """Quick check if Tally is accessible"""
        status, _ = self.check()
        return status == PreflightStatus.ACTIVE
