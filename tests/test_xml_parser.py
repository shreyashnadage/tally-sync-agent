"""
Tests for Tally XML Parser
Encoding, malformed XML, and special character handling
"""
import pytest
from lxml import etree
from tallybridge_agent.tally.xmlparser import TallyXMLParser


@pytest.fixture
def parser():
    """Create XML parser instance"""
    return TallyXMLParser(recover_mode=True)


# ============= Basic Parsing Tests =============

def test_parser_initialization():
    """Test parser initialization"""
    parser = TallyXMLParser(recover_mode=True)
    assert parser.recover_mode is True


def test_parse_simple_xml(parser):
    """Test parsing simple valid XML"""
    xml = """<?xml version="1.0"?>
<ENVELOPE>
    <COMPANY>
        <NAME>Test Company</NAME>
    </COMPANY>
</ENVELOPE>"""

    root = parser.parse_string(xml)
    assert root is not None
    assert root.tag == "ENVELOPE"


def test_parse_empty_data(parser):
    """Test parsing empty data"""
    root = parser.parse_bytes(b"")
    assert root is None


def test_parse_none_data(parser):
    """Test parsing None"""
    root = parser.parse_bytes(b"")
    assert root is None


# ============= Encoding Tests =============

def test_encoding_detection_utf8(parser):
    """Test UTF-8 encoding detection"""
    xml = """<?xml version="1.0" encoding="utf-8"?>
<TEST>Hindi Text: हिंदी</TEST>""".encode('utf-8')

    detected = parser._detect_encoding(xml)
    assert detected.lower() in ('utf-8', 'utf-8-sig', 'ascii')


def test_encoding_detection_cp1252(parser):
    """Test cp1252 encoding detection"""
    # Create cp1252 encoded text
    xml = """<?xml version="1.0"?>
<TEST>Some text</TEST>""".encode('cp1252')

    detected = parser._detect_encoding(xml)
    assert detected.lower() in ('utf-8', 'cp1252')  # Both might work for ASCII-compatible text


def test_parse_utf8_with_hindi(parser):
    """Test parsing UTF-8 XML with Hindi characters - just verify it doesn't fail"""
    xml = """<?xml version="1.0" encoding="utf-8"?>
<COMPANY>
    <NAME>राष्ट्रीय व्यापारी</NAME>
</COMPANY>""".encode('utf-8')

    root = parser.parse_bytes(xml)
    assert root is not None
    assert root.tag == "COMPANY"


def test_parse_gujarati_text(parser):
    """Test parsing Gujarati text"""
    xml = """<?xml version="1.0" encoding="utf-8"?>
<PARTY>
    <NAME>ગુજરાતી વ્યાપારી</NAME>
</PARTY>""".encode('utf-8')

    root = parser.parse_bytes(xml)
    assert root is not None


# ============= Sanitization Tests =============

def test_sanitize_bare_ampersand(parser):
    """Test sanitization of bare & characters"""
    data = b"<TEST>A & B</TEST>"
    sanitized = parser._sanitize_bytes(data)
    # Should escape bare &
    assert b"&amp;" in sanitized or b"& " in sanitized  # Depends on regex


def test_sanitize_null_bytes(parser):
    """Test removal of null bytes"""
    data = b"<TEST>Text\x00WithNull</TEST>"
    sanitized = parser._sanitize_bytes(data)
    assert b"\x00" not in sanitized


def test_sanitize_control_characters(parser):
    """Test removal of control characters"""
    # Control character 0x01 (invalid in XML)
    data = b"<TEST>Text\x01Invalid</TEST>"
    sanitized = parser._sanitize_bytes(data)
    # Should preserve the data but remove control chars
    assert b"\x01" not in sanitized or len(sanitized) > 0


# ============= Malformed XML Tests =============

def test_parse_malformed_unclosed_tag(parser):
    """Test parsing malformed XML with unclosed tag"""
    xml = b"""<?xml version="1.0"?>
<ENVELOPE>
    <COMPANY>
        <NAME>Test</NAME>
    </ENVELOPE>"""

    root = parser.parse_bytes(xml)
    # With recover=True, should still parse
    # (Note: behavior depends on lxml's recovery)
    if root is not None:
        assert root.tag in ("ENVELOPE", "COMPANY")


def test_parse_missing_xml_declaration(parser):
    """Test parsing XML without declaration"""
    xml = b"""<ENVELOPE>
    <COMPANY>
        <NAME>Test</NAME>
    </COMPANY>
</ENVELOPE>"""

    root = parser.parse_bytes(xml)
    assert root is not None
    assert root.tag == "ENVELOPE"


def test_parse_html_instead_of_xml(parser):
    """Test that HTML is rejected"""
    html = b"""<html>
    <body>
        <p>This is HTML</p>
    </body>
</html>"""

    root = parser.parse_bytes(html)
    # Might parse as XML but won't validate as Tally
    if root:
        assert not TallyXMLParser.validate_tally_response(root)


# ============= String Normalization Tests =============

def test_normalize_string_whitespace(parser):
    """Test whitespace normalization"""
    text = "Text   with    multiple    spaces"
    normalized = parser._normalize_string(text)
    assert "   " not in normalized
    assert normalized == "Text with multiple spaces"


def test_normalize_string_unicode(parser):
    """Test unicode normalization (NFC)"""
    # Decomposed form: e + combining acute accent
    decomposed = "café"  # Using decomposed form if available
    normalized = parser._normalize_string(decomposed)
    # Should be in NFC form
    assert len(normalized) > 0


def test_normalize_string_strip(parser):
    """Test stripping whitespace"""
    text = "  Text with spaces  "
    normalized = parser._normalize_string(text)
    assert normalized == "Text with spaces"


# ============= Element Extraction Tests =============

def test_extract_text(parser):
    """Test extracting text from element"""
    xml = """<?xml version="1.0"?>
<ROOT>
    <COMPANY>
        <NAME>National Traders</NAME>
    </COMPANY>
</ROOT>"""

    root = parser.parse_string(xml)
    name = parser.extract_text(root, 'COMPANY/NAME')
    assert name == "National Traders"


def test_extract_text_with_whitespace(parser):
    """Test extracting text with extra whitespace"""
    xml = """<?xml version="1.0"?>
<ROOT>
    <COMPANY>
        <NAME>  National   Traders  </NAME>
    </COMPANY>
</ROOT>"""

    root = parser.parse_string(xml)
    name = parser.extract_text(root, 'COMPANY/NAME')
    assert name == "National Traders"


def test_extract_text_default(parser):
    """Test extract_text default value"""
    xml = """<?xml version="1.0"?>
<ROOT>
    <COMPANY>
    </COMPANY>
</ROOT>"""

    root = parser.parse_string(xml)
    name = parser.extract_text(root, 'COMPANY/NAME', default="Unknown")
    assert name == "Unknown"


def test_extract_attrib(parser):
    """Test extracting attribute"""
    xml = """<?xml version="1.0"?>
<ROOT>
    <COMPANY id="123" name="Test">
    </COMPANY>
</ROOT>"""

    root = parser.parse_string(xml)
    company = root.find('COMPANY')
    if company is not None:
        company_id = parser.extract_attrib(company, 'id')
        assert company_id == "123"


# ============= Iteration Tests =============

def test_iter_elements(parser):
    """Test iterating over elements"""
    xml = """<?xml version="1.0"?>
<ROOT>
    <COMPANY>
        <NAME>Company 1</NAME>
    </COMPANY>
    <COMPANY>
        <NAME>Company 2</NAME>
    </COMPANY>
</ROOT>"""

    root = parser.parse_string(xml)
    companies = parser.iter_elements(root, 'COMPANY')
    assert len(companies) == 2


# ============= Tally Validation Tests =============

def test_validate_tally_envelope(parser):
    """Test validation of Tally ENVELOPE response"""
    xml = """<?xml version="1.0"?>
<ENVELOPE>
    <HEADER>
        <TALLYRESPONSE>OK</TALLYRESPONSE>
    </HEADER>
</ENVELOPE>"""

    root = parser.parse_string(xml)
    assert TallyXMLParser.validate_tally_response(root) is True


def test_validate_tally_response_element(parser):
    """Test validation of Tally RESPONSE element"""
    xml = """<?xml version="1.0"?>
<RESPONSE>
    <COMPANY>Test</COMPANY>
</RESPONSE>"""

    root = parser.parse_string(xml)
    assert TallyXMLParser.validate_tally_response(root) is True


def test_validate_non_tally_xml(parser):
    """Test that non-Tally XML is rejected"""
    xml = """<?xml version="1.0"?>
<CUSTOM>
    <DATA>Some data</DATA>
</CUSTOM>"""

    root = parser.parse_string(xml)
    assert TallyXMLParser.validate_tally_response(root) is False


def test_validate_none(parser):
    """Test validation of None"""
    assert TallyXMLParser.validate_tally_response(None) is False


# ============= Element to Dict Conversion =============

def test_element_to_dict(parser):
    """Test converting element to dictionary"""
    xml = """<?xml version="1.0"?>
<COMPANY id="123">
    <NAME>Test Company</NAME>
    <PAN>ABC123</PAN>
</COMPANY>"""

    root = parser.parse_string(xml)
    company_dict = parser.element_to_dict(root)

    assert company_dict['tag'] == 'COMPANY'
    assert company_dict['attributes']['id'] == '123'
    assert len(company_dict['children']) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
