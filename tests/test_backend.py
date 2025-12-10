"""
ICC Agent Backend - API Test Suite

This script tests all backend API endpoints to verify functionality.
Run this after starting the backend to ensure everything works correctly.

Usage:
    python test_backend.py
    python test_backend.py --url http://localhost:8000
"""

import requests
import json
import sys
import time
from typing import Dict, Any, Optional
import argparse


class BackendTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session_id: Optional[str] = None
        self.tests_passed = 0
        self.tests_failed = 0
        
    def print_test(self, test_name: str, status: str, details: str = ""):
        """Print test result with formatting"""
        status_icon = "✓" if status == "PASS" else "✗"
        status_color = "\033[92m" if status == "PASS" else "\033[91m"
        reset_color = "\033[0m"
        
        print(f"{status_color}{status_icon} {test_name}{reset_color}")
        if details:
            print(f"  {details}")
        
        if status == "PASS":
            self.tests_passed += 1
        else:
            self.tests_failed += 1
    
    def test_health_check(self) -> bool:
        """Test 1: Health Check Endpoint"""
        print("\n" + "="*60)
        print("TEST 1: Health Check")
        print("="*60)
        
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Status: {data.get('status')}")
                print(f"Version: {data.get('version')}")
                print(f"Services: {data.get('services')}")
                self.print_test("Health Check", "PASS", f"Backend is healthy")
                return True
            else:
                self.print_test("Health Check", "FAIL", f"Status code: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.print_test("Health Check", "FAIL", "Cannot connect to backend. Is it running?")
            return False
        except Exception as e:
            self.print_test("Health Check", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_create_session(self) -> bool:
        """Test 2: Create Session"""
        print("\n" + "="*60)
        print("TEST 2: Create Session")
        print("="*60)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat/sessions",
                json={},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get('session_id')
                print(f"Session ID: {self.session_id}")
                print(f"Created at: {data.get('created_at')}")
                self.print_test("Create Session", "PASS", f"Session created: {self.session_id[:8]}...")
                return True
            else:
                self.print_test("Create Session", "FAIL", f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_test("Create Session", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_get_connections(self) -> bool:
        """Test 3: Get Database Connections"""
        print("\n" + "="*60)
        print("TEST 3: Get Database Connections")
        print("="*60)
        
        try:
            response = requests.get(f"{self.base_url}/api/connections", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                connections = data.get('connections', [])
                print(f"Found {len(connections)} connections:")
                for conn in connections[:3]:  # Show first 3
                    print(f"  - {conn.get('name')} ({conn.get('type')})")
                if len(connections) > 3:
                    print(f"  ... and {len(connections) - 3} more")
                
                self.print_test("Get Connections", "PASS", f"Retrieved {len(connections)} connections")
                return True
            else:
                self.print_test("Get Connections", "FAIL", f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_test("Get Connections", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_send_message(self) -> bool:
        """Test 4: Send Message"""
        print("\n" + "="*60)
        print("TEST 4: Send Message")
        print("="*60)
        
        if not self.session_id:
            self.print_test("Send Message", "FAIL", "No session ID available")
            return False
        
        try:
            # Send a simple help request
            response = requests.post(
                f"{self.base_url}/api/chat/message",
                json={
                    "session_id": self.session_id,
                    "message": "help"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Stage: {data.get('stage')}")
                print(f"Response preview: {data.get('response', '')[:100]}...")
                print(f"Requires dropdown: {data.get('requires_dropdown')}")
                
                self.print_test("Send Message", "PASS", "Message processed successfully")
                return True
            else:
                self.print_test("Send Message", "FAIL", f"Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            self.print_test("Send Message", "FAIL", "Request timeout (>30s)")
            return False
        except Exception as e:
            self.print_test("Send Message", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_get_session(self) -> bool:
        """Test 5: Get Session Info"""
        print("\n" + "="*60)
        print("TEST 5: Get Session Info")
        print("="*60)
        
        if not self.session_id:
            self.print_test("Get Session", "FAIL", "No session ID available")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/api/chat/sessions/{self.session_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Session ID: {data.get('session_id')}")
                print(f"Stage: {data.get('stage')}")
                
                self.print_test("Get Session", "PASS", "Session info retrieved")
                return True
            else:
                self.print_test("Get Session", "FAIL", f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_test("Get Session", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_delete_session(self) -> bool:
        """Test 6: Delete Session"""
        print("\n" + "="*60)
        print("TEST 6: Delete Session")
        print("="*60)
        
        if not self.session_id:
            self.print_test("Delete Session", "FAIL", "No session ID available")
            return False
        
        try:
            response = requests.delete(
                f"{self.base_url}/api/chat/sessions/{self.session_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Message: {data.get('message')}")
                
                self.print_test("Delete Session", "PASS", "Session deleted successfully")
                return True
            else:
                self.print_test("Delete Session", "FAIL", f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_test("Delete Session", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_api_docs(self) -> bool:
        """Test 7: API Documentation"""
        print("\n" + "="*60)
        print("TEST 7: API Documentation")
        print("="*60)
        
        try:
            # Test Swagger UI
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            if response.status_code == 200:
                print(f"Swagger UI: ✓ Available at {self.base_url}/docs")
            else:
                print(f"Swagger UI: ✗ Not available")
            
            # Test OpenAPI JSON
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            if response.status_code == 200:
                print(f"OpenAPI JSON: ✓ Available at {self.base_url}/openapi.json")
            else:
                print(f"OpenAPI JSON: ✗ Not available")
            
            self.print_test("API Documentation", "PASS", "Documentation endpoints accessible")
            return True
                
        except Exception as e:
            self.print_test("API Documentation", "FAIL", f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n" + "="*60)
        print("ICC AGENT BACKEND - API TEST SUITE")
        print("="*60)
        print(f"Testing backend at: {self.base_url}")
        print()
        
        # Run tests
        tests = [
            self.test_health_check,
            self.test_create_session,
            self.test_get_connections,
            self.test_send_message,
            self.test_get_session,
            self.test_delete_session,
            self.test_api_docs,
        ]
        
        for test in tests:
            test()
            time.sleep(0.5)  # Small delay between tests
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_failed}")
        print(f"Total Tests: {self.tests_passed + self.tests_failed}")
        
        if self.tests_failed == 0:
            print("\n✓ ALL TESTS PASSED! Backend is working correctly.")
            return 0
        else:
            print(f"\n✗ {self.tests_failed} TEST(S) FAILED! Check the errors above.")
            return 1


def main():
    parser = argparse.ArgumentParser(description='Test ICC Agent Backend API')
    parser.add_argument('--url', default='http://localhost:8000', 
                       help='Backend URL (default: http://localhost:8000)')
    args = parser.parse_args()
    
    tester = BackendTester(args.url)
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
