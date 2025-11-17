#!/usr/bin/env python3
"""
Event Management App Backend API Testing
Tests all endpoints including auth, events, bookings, and payments
"""

import requests
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

class EventAppTester:
    def __init__(self, base_url="https://ticketmaster-70.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    expected_status: int = 200, use_auth: bool = False) -> tuple[bool, Dict]:
        """Make HTTP request and validate response"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if use_auth and self.session_token:
            headers['Authorization'] = f'Bearer {self.session_token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text[:200]}

            return success, response_data

        except Exception as e:
            return False, {"error": str(e)}

    def setup_test_user(self) -> bool:
        """Create test user and session in MongoDB"""
        print("\n🔧 Setting up test user...")
        
        # Generate unique test data
        timestamp = int(time.time())
        user_id = f"test-user-{timestamp}"
        session_token = f"test_session_{timestamp}"
        email = f"test.user.{timestamp}@example.com"
        
        # MongoDB commands to create test user and session
        mongo_commands = f"""
        use test_database;
        db.users.insertOne({{
            id: "{user_id}",
            email: "{email}",
            name: "Test User {timestamp}",
            picture: "https://via.placeholder.com/150",
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: "{user_id}",
            session_token: "{session_token}",
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            created_at: new Date()
        }});
        """
        
        try:
            import subprocess
            result = subprocess.run(
                ['mongosh', '--eval', mongo_commands],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                self.session_token = session_token
                self.user_id = user_id
                print(f"✅ Test user created: {email}")
                print(f"✅ Session token: {session_token[:20]}...")
                return True
            else:
                print(f"❌ MongoDB setup failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ MongoDB setup error: {str(e)}")
            return False

    def test_health_check(self):
        """Test basic connectivity"""
        print("\n🏥 Testing Health Check...")
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            success = response.status_code in [200, 404]  # 404 is OK for root
            self.log_test("Health Check", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Health Check", False, str(e))

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication...")
        
        # Test /auth/me with valid token
        success, data = self.make_request('GET', 'auth/me', use_auth=True)
        self.log_test("GET /auth/me (authenticated)", success, 
                     f"User: {data.get('name', 'Unknown')}" if success else str(data))
        
        # Test /auth/me without token (should fail)
        success, data = self.make_request('GET', 'auth/me', expected_status=401)
        self.log_test("GET /auth/me (unauthenticated)", success, "Correctly rejected")

    def test_categories(self):
        """Test category endpoints"""
        print("\n📂 Testing Categories...")
        
        success, data = self.make_request('GET', 'categories')
        if success and isinstance(data, list) and len(data) > 0:
            self.log_test("GET /categories", True, f"Found {len(data)} categories")
            return data
        else:
            self.log_test("GET /categories", False, str(data))
            return []

    def test_events(self, categories: list) -> Optional[str]:
        """Test event endpoints"""
        print("\n🎪 Testing Events...")
        
        # Test GET events (public)
        success, data = self.make_request('GET', 'events')
        self.log_test("GET /events (public)", success, 
                     f"Found {len(data)} events" if success and isinstance(data, list) else str(data))
        
        # Test GET my events (authenticated)
        success, data = self.make_request('GET', 'events/my-events/list', use_auth=True)
        self.log_test("GET /events/my-events/list", success, 
                     f"Found {len(data)} user events" if success and isinstance(data, list) else str(data))
        
        # Test CREATE event
        if categories:
            event_data = {
                "title": f"Test Event {int(time.time())}",
                "description": "This is a test event for API testing",
                "date": (datetime.now() + timedelta(days=30)).isoformat(),
                "location": "Test Venue, Test City",
                "capacity": 100,
                "category": categories[0]['name'],
                "image_url": "https://via.placeholder.com/400x300"
            }
            
            success, data = self.make_request('POST', 'events', event_data, 
                                            expected_status=200, use_auth=True)
            if success:
                event_id = data.get('id')
                self.log_test("POST /events", True, f"Created event: {event_id}")
                return event_id
            else:
                self.log_test("POST /events", False, str(data))
        
        return None

    def test_ticket_types(self, event_id: str) -> list:
        """Test ticket type endpoints"""
        if not event_id:
            return []
            
        print("\n🎫 Testing Ticket Types...")
        
        # Create ticket types
        ticket_types = [
            {"name": "General Admission", "price": 0.0, "quantity_available": 50},
            {"name": "VIP", "price": 25.99, "quantity_available": 10}
        ]
        
        created_tickets = []
        for ticket_data in ticket_types:
            success, data = self.make_request('POST', f'events/{event_id}/ticket-types', 
                                            ticket_data, expected_status=200, use_auth=True)
            if success:
                created_tickets.append(data)
                self.log_test(f"POST /events/{event_id}/ticket-types ({ticket_data['name']})", 
                            True, f"Price: ${ticket_data['price']}")
            else:
                self.log_test(f"POST /events/{event_id}/ticket-types ({ticket_data['name']})", 
                            False, str(data))
        
        # Test GET ticket types
        success, data = self.make_request('GET', f'events/{event_id}/ticket-types')
        self.log_test(f"GET /events/{event_id}/ticket-types", success, 
                     f"Found {len(data)} ticket types" if success and isinstance(data, list) else str(data))
        
        return created_tickets

    def test_bookings(self, event_id: str, ticket_types: list):
        """Test booking endpoints"""
        if not event_id or not ticket_types:
            return
            
        print("\n📝 Testing Bookings...")
        
        # Test free ticket booking
        free_ticket = next((t for t in ticket_types if t['price'] == 0), None)
        if free_ticket:
            booking_data = {
                "event_id": event_id,
                "ticket_type_id": free_ticket['id'],
                "quantity": 2
            }
            
            success, data = self.make_request('POST', 'bookings', booking_data, 
                                            expected_status=200, use_auth=True)
            if success:
                booking = data.get('booking', {})
                requires_payment = data.get('requires_payment', False)
                self.log_test("POST /bookings (free ticket)", True, 
                            f"Booking ID: {booking.get('id')}, Payment required: {requires_payment}")
                
                # Test QR code for confirmed booking
                if booking.get('status') == 'confirmed':
                    booking_id = booking.get('id')
                    try:
                        qr_response = requests.get(f"{self.api_url}/bookings/{booking_id}/qr", 
                                                 headers={'Authorization': f'Bearer {self.session_token}'})
                        qr_success = qr_response.status_code == 200 and qr_response.headers.get('content-type', '').startswith('image/')
                        self.log_test("GET /bookings/{id}/qr", qr_success, 
                                    f"QR code generated" if qr_success else f"Status: {qr_response.status_code}")
                    except Exception as e:
                        self.log_test("GET /bookings/{id}/qr", False, str(e))
            else:
                self.log_test("POST /bookings (free ticket)", False, str(data))
        
        # Test paid ticket booking (will create pending booking)
        paid_ticket = next((t for t in ticket_types if t['price'] > 0), None)
        if paid_ticket:
            booking_data = {
                "event_id": event_id,
                "ticket_type_id": paid_ticket['id'],
                "quantity": 1
            }
            
            success, data = self.make_request('POST', 'bookings', booking_data, 
                                            expected_status=200, use_auth=True)
            if success:
                booking = data.get('booking', {})
                requires_payment = data.get('requires_payment', False)
                self.log_test("POST /bookings (paid ticket)", True, 
                            f"Booking ID: {booking.get('id')}, Payment required: {requires_payment}")
                
                # Test checkout session creation
                if requires_payment:
                    checkout_data = {
                        "booking_id": booking.get('id'),
                        "origin_url": self.base_url
                    }
                    success, checkout_response = self.make_request('POST', 'bookings/checkout', 
                                                                 checkout_data, expected_status=200, use_auth=True)
                    if success and 'url' in checkout_response:
                        self.log_test("POST /bookings/checkout", True, "Stripe checkout URL created")
                    else:
                        self.log_test("POST /bookings/checkout", False, str(checkout_response))
            else:
                self.log_test("POST /bookings (paid ticket)", False, str(data))
        
        # Test GET my bookings
        success, data = self.make_request('GET', 'bookings/my-bookings/list', use_auth=True)
        self.log_test("GET /bookings/my-bookings/list", success, 
                     f"Found {len(data)} bookings" if success and isinstance(data, list) else str(data))

    def test_event_details(self, event_id: str):
        """Test event details endpoint"""
        if not event_id:
            return
            
        print("\n🔍 Testing Event Details...")
        
        success, data = self.make_request('GET', f'events/{event_id}')
        if success:
            self.log_test(f"GET /events/{event_id}", True, f"Event: {data.get('title', 'Unknown')}")
        else:
            self.log_test(f"GET /events/{event_id}", False, str(data))

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Event Management App Backend Tests")
        print(f"🌐 Testing API: {self.api_url}")
        
        # Setup
        if not self.setup_test_user():
            print("❌ Cannot proceed without test user setup")
            return False
        
        # Run tests
        self.test_health_check()
        self.test_auth_endpoints()
        categories = self.test_categories()
        event_id = self.test_events(categories)
        ticket_types = self.test_ticket_types(event_id)
        self.test_bookings(event_id, ticket_types)
        self.test_event_details(event_id)
        
        # Summary
        print(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 80

def main():
    tester = EventAppTester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": tester.tests_run,
            "passed_tests": tester.tests_passed,
            "success_rate": (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
        },
        "test_details": tester.test_results
    }
    
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())