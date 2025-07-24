#!/usr/bin/env python3
"""
Test Runner for Agent-Based Medical Scribe System
Executes all tests and generates a comprehensive report
"""

import sys
import os
import asyncio
import pytest
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestRunner:
    def __init__(self):
        self.results = {
            "start_time": datetime.now().isoformat(),
            "test_suites": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0
            }
        }
    
    def run_unit_tests(self):
        """Run unit tests for individual components"""
        print("\n" + "="*60)
        print("RUNNING UNIT TESTS")
        print("="*60)
        
        test_files = [
            "test_speaker_diarization_agent.py",
            "test_section_agents.py",
            "test_agent_orchestrator.py"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"\nRunning {test_file}...")
                result = pytest.main([
                    test_file,
                    "-v",
                    "--tb=short",
                    "-q"
                ])
                
                self.results["test_suites"][test_file] = {
                    "status": "passed" if result == 0 else "failed",
                    "exit_code": result
                }
    
    def run_integration_tests(self):
        """Run integration tests"""
        print("\n" + "="*60)
        print("RUNNING INTEGRATION TESTS")
        print("="*60)
        
        # Add integration test files here
        print("Integration tests would be run here...")
    
    def run_performance_tests(self):
        """Run performance tests"""
        print("\n" + "="*60)
        print("RUNNING PERFORMANCE TESTS")
        print("="*60)
        
        # Simple performance test
        asyncio.run(self._test_agent_performance())
    
    async def _test_agent_performance(self):
        """Test agent response times"""
        try:
            from app.services.speaker_diarization_agent import SpeakerDiarizationAgent
            import time
            
            agent = SpeakerDiarizationAgent()
            
            # Test latency
            times = []
            for _ in range(10):
                start = time.time()
                await agent.identify_speaker("Test transcription text")
                times.append(time.time() - start)
            
            avg_time = sum(times) / len(times)
            max_time = max(times)
            
            print(f"Speaker Diarization Performance:")
            print(f"  Average latency: {avg_time*1000:.2f}ms")
            print(f"  Max latency: {max_time*1000:.2f}ms")
            
            self.results["test_suites"]["performance"] = {
                "speaker_diarization_avg_ms": avg_time * 1000,
                "speaker_diarization_max_ms": max_time * 1000,
                "status": "passed" if avg_time < 0.5 else "failed"
            }
            
        except Exception as e:
            print(f"Performance test error: {e}")
            self.results["test_suites"]["performance"] = {
                "status": "error",
                "error": str(e)
            }
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("TEST REPORT")
        print("="*60)
        
        # Count results
        for suite, result in self.results["test_suites"].items():
            if result.get("status") == "passed":
                self.results["summary"]["passed"] += 1
            elif result.get("status") == "failed":
                self.results["summary"]["failed"] += 1
            elif result.get("status") == "error":
                self.results["summary"]["errors"] += 1
        
        self.results["summary"]["total"] = len(self.results["test_suites"])
        self.results["end_time"] = datetime.now().isoformat()
        
        # Print summary
        print(f"\nTotal Test Suites: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Errors: {self.results['summary']['errors']}")
        
        # Save detailed report
        report_path = Path("test_report.json")
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        # Return exit code
        return 0 if self.results["summary"]["failed"] == 0 and self.results["summary"]["errors"] == 0 else 1
    
    def run_all_tests(self):
        """Run all test suites"""
        print("Starting Medical Scribe Agent System Tests")
        print(f"Time: {datetime.now()}")
        
        self.run_unit_tests()
        self.run_integration_tests()
        self.run_performance_tests()
        
        return self.generate_report()

def main():
    """Main entry point"""
    runner = TestRunner()
    exit_code = runner.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()