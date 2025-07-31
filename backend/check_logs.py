#!/usr/bin/env python3
"""Quick script to check recent logs and debug SSE issues"""

import subprocess
import sys

print("🔍 Checking recent backend logs for SSE and section updates...\n")

# Check for SSE publishing
print("=" * 60)
print("1. SSE Publishing Events:")
print("=" * 60)
subprocess.run(["grep", "-n", "Published.*event", "-A", "2", "-B", "2", "app.log"], stderr=subprocess.DEVNULL)

print("\n" + "=" * 60)
print("2. Section Extraction:")
print("=" * 60)
subprocess.run(["grep", "-n", "Extracted clinical sections", "-A", "5", "app.log"], stderr=subprocess.DEVNULL)

print("\n" + "=" * 60)
print("3. SSE Manager Activity:")
print("=" * 60)
subprocess.run(["grep", "-n", "SSE.*publish", "-A", "2", "app.log"], stderr=subprocess.DEVNULL)

print("\n" + "=" * 60)
print("4. Clinical Analysis Agent:")
print("=" * 60)
subprocess.run(["grep", "-n", "clinical analysis", "-A", "3", "app.log"], stderr=subprocess.DEVNULL)

print("\n" + "=" * 60)
print("5. Recent Errors:")
print("=" * 60)
subprocess.run(["grep", "-n", "ERROR", "-A", "3", "app.log", "|", "tail", "-20"], shell=True, stderr=subprocess.DEVNULL)