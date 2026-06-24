"""
Tally XML Parser
Fault-tolerant XML parsing with encoding normalization and recovery
"""
import logging
from typing import Optional, Dict, Any, List
import unicodedata
import re
from lxml import etree
import chardet

logger = logging.getLogger(__name__)


class XMLParseError(Exception):
    """XML parsing error"""
    pass


class TallyXMLParser:
    """
    Parse Tally XML responses with robustness for encoding issues,
    malformed data, and special characters (₹ symbol, etc.)
    """

    # ₹ symbol in different encodings
    RUPEE_SYMBOL_CP1252 = 0xA4  # In Tally's cp1252 variant
    RUPEE_SYMBOL_UTF8 = "₹"

    def __init__(self, recover_mode: bool = True):
        """
        Initialize XML parser

        Args:
            recover_mode: Enable lxml recover mode for malformed XML
        """
        self.recover_mode = recover_mode

    def _sanitize_bytes(self, data: bytes) -> bytes:
        """
        Pre-sanitization of bytes before parsing:
        - Escape bare & characters
        - Remove null bytes
        - Remove control characters
        - Handle ₹ symbol

        Args:
            data: Raw bytes from Tally response

        Returns:
            Sanitized bytes
        """
        # Replace bare & with &amp; (before XML parsing treats it as entity)
        # But be careful not to double-escape existing entities
        data = re.sub(br'&(?![#\w]+;)', b'&amp;', data)

        # Remove null bytes
        data = data.replace(b'\x00', b'')

        # Remove control characters except whitespace
        # Keep: tab (09), newline (0A), carriage return (0D)
        data_list = bytearray(data)
        for i in range(len(data_list)):
            if data_list[i] < 0x20 and data_list[i] not in (0x09, 0x0A, 0x0D):
                data_list[i] = ord(b' ')
        data = bytes(data_list)

        # Fix common ₹ encoding issues
        # Tally uses cp1252 where ₹ might be encoded as 0xA4
        try:
            # Try to detect and fix bad rupee encoding
            if b'\xa4' in data:
                # Check if this might be rupee symbol
                data = data.replace(b'\xa4', '₹'.encode('utf-8'))
        except:
            pass

        return data

    def _detect_encoding(self, data: bytes) -> str:
        """
        Detect encoding of the response data.
        Try in order: UTF-8, cp1252 (Tally variant), chardet

        Args:
            data: Raw bytes

        Returns:
            Detected encoding name
        """
        # First try UTF-8 (most common)
        try:
            data.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            pass

        # Try cp1252 (Tally's preferred encoding)
        try:
            data.decode('cp1252')
            return 'cp1252'
        except UnicodeDecodeError:
            pass

        # Use chardet as fallback
        detected = chardet.detect(data)
        encoding = detected.get('encoding', 'utf-8')

        # chardet might return None or unusual names
        if not encoding or encoding.lower() in ('ascii', 'utf-7'):
            encoding = 'utf-8'

        return encoding

    def _normalize_string(self, text: str) -> str:
        """
        Normalize string to NFC form and clean up whitespace

        Args:
            text: Input string

        Returns:
            Normalized string
        """
        # NFC normalization (canonical decomposition, then recomposition)
        text = unicodedata.normalize('NFC', text)

        # Clean up excessive whitespace while preserving structure
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)

        # Remove trailing/leading whitespace
        text = text.strip()

        return text

    def parse_bytes(self, data: bytes) -> Optional[etree._Element]:
        """
        Parse Tally XML from bytes with full fault tolerance

        Args:
            data: Raw bytes from Tally HTTP response

        Returns:
            Parsed XML root element, or None if parsing failed
        """
        if not data:
            logger.error("Empty data provided to XML parser")
            return None

        try:
            # Step 1: Sanitize bytes
            data = self._sanitize_bytes(data)

            # Step 2: Detect encoding
            encoding = self._detect_encoding(data)
            logger.debug(f"Detected encoding: {encoding}")

            # Step 3: Decode to string
            try:
                text = data.decode(encoding, errors='replace')
            except Exception as e:
                logger.warning(f"Failed to decode with {encoding}, using utf-8: {e}")
                text = data.decode('utf-8', errors='replace')

            # Step 4: Create parser with recovery
            parser = etree.XMLParser(recover=self.recover_mode, encoding='utf-8')

            # Step 5: Parse XML
            root = etree.fromstring(text.encode('utf-8'), parser=parser)

            logger.debug(f"Successfully parsed XML with root tag: {root.tag}")
            return root

        except etree.XMLSyntaxError as e:
            logger.error(f"XML syntax error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during XML parsing: {e}", exc_info=True)
            return None

    def parse_string(self, xml_string: str) -> Optional[etree._Element]:
        """
        Parse XML from string

        Args:
            xml_string: XML string

        Returns:
            Parsed XML root element, or None if parsing failed
        """
        return self.parse_bytes(xml_string.encode('utf-8'))

    def extract_text(self, element: etree._Element, path: str, default: str = "") -> str:
        """
        Extract text from XML element at given xpath, with normalization

        Args:
            element: Parent XML element
            path: XPath to target element
            default: Default value if not found

        Returns:
            Normalized text value
        """
        try:
            found = element.find(path)
            if found is not None and found.text:
                return self._normalize_string(found.text)
            return default
        except Exception as e:
            logger.debug(f"Error extracting text from {path}: {e}")
            return default

    def extract_attrib(self, element: etree._Element, attrib: str, default: str = "") -> str:
        """
        Extract attribute value from XML element

        Args:
            element: XML element
            attrib: Attribute name
            default: Default value if not found

        Returns:
            Attribute value or default
        """
        try:
            value = element.get(attrib, default)
            return self._normalize_string(value) if value else default
        except Exception as e:
            logger.debug(f"Error extracting attribute {attrib}: {e}")
            return default

    def iter_elements(self, element: etree._Element, tag: str) -> List[etree._Element]:
        """
        Iterate over child elements with given tag

        Args:
            element: Parent XML element
            tag: Tag name to find

        Returns:
            List of matching child elements
        """
        try:
            return list(element.findall(tag))
        except Exception as e:
            logger.debug(f"Error iterating elements with tag {tag}: {e}")
            return []

    def element_to_dict(self, element: Optional[etree._Element], include_text: bool = True) -> Dict[str, Any]:
        """
        Convert XML element to dictionary representation

        Args:
            element: XML element to convert (or None)
            include_text: Include element text in output

        Returns:
            Dictionary with tag, text, attributes, and children, or empty dict if element is None
        """
        if element is None:
            return {}

        result = {
            "tag": element.tag,
            "attributes": dict(element.attrib) if element.attrib else {},
            "children": []
        }

        if include_text and element.text:
            text = self._normalize_string(element.text)
            if text:
                result["text"] = text

        # Add child elements
        for child in element:
            child_dict = self.element_to_dict(child, include_text)
            result["children"].append(child_dict)

        return result

    @staticmethod
    def validate_tally_response(root: Optional[etree._Element]) -> bool:
        """
        Validate that parsed XML looks like a Tally response

        Args:
            root: Parsed XML root element

        Returns:
            True if response looks like Tally XML
        """
        if root is None:
            return False

        # Tally responses typically have these root tags
        valid_roots = {"ENVELOPE", "RESPONSE"}
        if root.tag in valid_roots:
            return True

        # Or contain TALLYRESPONSE anywhere
        for elem in root.iter():
            if "TALLYRESPONSE" in elem.tag.upper():
                return True

        return False
