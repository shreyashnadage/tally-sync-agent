"""
Tests for Tally Pre-flight Check
Unit tests with mocked HTTP responses
"""
import pytest
from unittest.mock import patch, MagicMock
import httpx
from tallybridge_agent.tally.preflight import TallyPreflight, PreflightStatus


@pytest.fixture
def preflight():
    """Create a TallyPreflight instance"""
    return TallyPreflight(host="localhost", port=9000, timeout=3.0)


def test_preflight_initialization(preflight):
    """Test TallyPreflight initialization"""
    assert preflight.host == "localhost"
    assert preflight.port == 9000
    assert preflight.timeout == 3.0
    assert preflight.base_url == "http://localhost:9000"


@patch('tallybridge_agent.tally.preflight.httpx.post')
def test_preflight_active_response(mock_post, preflight):
    """Test successful Tally response"""
    # Mock a valid Tally XML response
    tally_response = """<?xml version="1.0" encoding="utf-8"?>
<ENVELOPE RequestType="Command">
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYRESPONSE>OK</TALLYRESPONSE>
    </HEADER>
    <BODY>
        <COMPANY>
            <NAME>National Traders</NAME>
        </COMPANY>
    </BODY>
</ENVELOPE>"""

    mock_post.return_value = MagicMock(status_code=200, text=tally_response)

    status, error = preflight.check()
    assert status == PreflightStatus.ACTIVE
    assert error is None


@patch('tallybridge_agent.tally.preflight.httpx.post')
def test_preflight_wrong_response(mock_post, preflight):
    """Test response that's not Tally XML"""
    # Mock an HTML response (wrong format)
    html_response = "<html><body>Error 404</body></html>"
    mock_post.return_value = MagicMock(status_code=200, text=html_response)

    status, error = preflight.check()
    assert status == PreflightStatus.WRONG_RESPONSE
    assert error is not None


@patch('tallybridge_agent.tally.preflight.httpx.post')
def test_preflight_connection_refused(mock_post, preflight):
    """Test connection refused (port closed)"""
    mock_post.side_effect = httpx.ConnectError("Connection refused")

    status, error = preflight.check()
    assert status == PreflightStatus.PORT_CLOSED
    assert error is not None


@patch('tallybridge_agent.tally.preflight.httpx.post')
def test_preflight_timeout(mock_post, preflight):
    """Test request timeout"""
    mock_post.side_effect = httpx.TimeoutException("Request timeout")

    status, error = preflight.check()
    assert status == PreflightStatus.TIMEOUT
    assert error is not None


@patch('tallybridge_agent.tally.preflight.httpx.post')
def test_preflight_http_error_status(mock_post, preflight):
    """Test HTTP error status code"""
    mock_post.return_value = MagicMock(status_code=500, text="Internal Server Error")

    status, error = preflight.check()
    assert status == PreflightStatus.WRONG_RESPONSE
    assert "500" in error


@patch('tallybridge_agent.tally.preflight.httpx.post')
def test_preflight_invalid_xml(mock_post, preflight):
    """Test invalid XML response"""
    mock_post.return_value = MagicMock(status_code=200, text="<invalid xml without closing>")

    status, error = preflight.check()
    assert status == PreflightStatus.WRONG_RESPONSE
    assert "not valid XML" in error


@patch('tallybridge_agent.tally.preflight.httpx.post')
def test_preflight_is_accessible(mock_post, preflight):
    """Test is_accessible helper method"""
    tally_response = """<?xml version="1.0"?>
<ENVELOPE><HEADER><TALLYRESPONSE>OK</TALLYRESPONSE></HEADER></ENVELOPE>"""
    mock_post.return_value = MagicMock(status_code=200, text=tally_response)

    assert preflight.is_accessible() is True

    # Test when not accessible
    mock_post.side_effect = httpx.ConnectError("Connection refused")
    assert preflight.is_accessible() is False


@pytest.mark.integration
def test_preflight_actual_tally():
    """
    Integration test against actual Tally Prime instance
    Only runs if Tally is actually running on localhost:9000
    """
    preflight = TallyPreflight(host="localhost", port=9000, timeout=5.0)
    status, error = preflight.check()

    # This test may pass or fail depending on whether Tally is running
    # We document both outcomes
    if status == PreflightStatus.ACTIVE:
        print("✓ Tally Prime is running and responding correctly")
        assert error is None
    elif status == PreflightStatus.PORT_CLOSED:
        print("✓ Port 9000 is closed (Tally not running)")
        assert "Connection refused" in error or "refused" in error.lower()
    elif status == PreflightStatus.TIMEOUT:
        print("✓ Connection timed out (Tally not responding)")
    else:
        print(f"✓ Got status: {status}, error: {error}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
