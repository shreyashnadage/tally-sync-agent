#!/usr/bin/env python
"""Quick test of Tally HTTP connectivity"""
import httpx

print("Testing Tally HTTP connectivity on localhost:9000...")

# Try a simple GET first
try:
    print("\n1. Trying GET /")
    response = httpx.get("http://localhost:9000/", timeout=5.0)
    print(f"   Status: {response.status_code}")
    print(f"   Preview: {response.text[:300]}")
except Exception as e:
    print(f"   Failed: {e}")

# Try POST with minimal XML
try:
    print("\n2. Trying POST with Company list XML")
    xml = """<?xml version="1.0" encoding="utf-8"?>
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
        "http://localhost:9000",
        content=xml,
        headers={"Content-Type": "application/xml"},
        timeout=10.0
    )
    print(f"   Status: {response.status_code}")
    print(f"   Preview: {response.text[:500]}")
except Exception as e:
    print(f"   Failed: {e}")

print("\nDone!")
