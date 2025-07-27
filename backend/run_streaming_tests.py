#!/usr/bin/env python3
"""Run streaming transcription tests"""
import sys
import subprocess
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Check if pytest is installed
try:
    import pytest
except ImportError:
    print("ERROR: pytest not installed")
    print("Please install it with: pip install pytest pytest-asyncio")
    sys.exit(1)

# Test files to run
test_files = [
    "tests/test_streaming_agents.py",
    "tests/test_streaming_supervisor.py", 
    "tests/test_streaming_api.py",
    "tests/test_streaming_integration.py"
]

print("="*60)
print("Running Streaming Transcription Tests")
print("="*60)

# Check for OpenAI API key
import os
if not os.getenv("OPENAI_API_KEY"):
    print("\nWARNING: OPENAI_API_KEY not set")
    print("Some integration tests will be skipped")
    print("Set the key in your .env file to run all tests")
    print()

# Run each test file
failed_tests = []
for test_file in test_files:
    print(f"\n>>> Running {test_file}")
    print("-"*40)
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        capture_output=False
    )
    
    if result.returncode != 0:
        failed_tests.append(test_file)
        
print("\n" + "="*60)
print("Test Summary")
print("="*60)

if failed_tests:
    print(f"\n❌ {len(failed_tests)} test file(s) failed:")
    for test in failed_tests:
        print(f"   - {test}")
    print("\nRun individual test files for more details:")
    print(f"   python -m pytest {failed_tests[0]} -v")
else:
    print("\n✅ All tests passed!")
    
# Run coverage report if coverage is installed
try:
    import coverage
    print("\n" + "="*60)
    print("Running Coverage Report")
    print("="*60)
    subprocess.run([
        sys.executable, "-m", "pytest", 
        "--cov=app.agents",
        "--cov-report=term-missing",
        *test_files
    ])
except ImportError:
    print("\nTip: Install coverage for code coverage reports:")
    print("   pip install pytest-cov")

print("\n" + "="*60)
print("Quick Test Commands:")
print("="*60)
print("Run all tests:           python run_streaming_tests.py")
print("Run specific test file:  python -m pytest tests/test_streaming_agents.py -v")
print("Run specific test:       python -m pytest tests/test_streaming_agents.py::TestAudioBuffer::test_add_chunk -v")
print("Run with coverage:       python -m pytest --cov=app.agents tests/")
print("Run integration only:    python -m pytest tests/test_streaming_integration.py -v")