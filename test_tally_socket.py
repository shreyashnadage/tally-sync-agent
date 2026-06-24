#!/usr/bin/env python
"""Test Tally connectivity at socket level"""
import socket
import time

print("Testing Tally socket connectivity on localhost:9000...")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)

    print("Connecting to localhost:9000...")
    result = sock.connect_ex(("localhost", 9000))

    if result == 0:
        print("[OK] Connection established on port 9000")

        # Try to send a simple HTTP request
        request = b"GET / HTTP/1.1\r\nHost: localhost:9000\r\n\r\n"
        print("\nSending HTTP GET request...")
        sock.send(request)

        # Try to receive response
        sock.settimeout(3)
        try:
            response = sock.recv(1024)
            print(f"[OK] Received response ({len(response)} bytes)")
            print(f"Preview: {response[:300]}")
        except socket.timeout:
            print("[FAIL] No response received (timeout)")
    else:
        print(f"[FAIL] Connection failed: {result}")

    sock.close()

except Exception as e:
    print(f"Error: {e}")
