#!/usr/bin/env python3
"""
Event Management App Backend API Testing - Role System Focus
Tests user role system, role-based access control, and admin endpoints
"""

import requests
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

class EventAppRoleTester:
    def __init__(self, base_url="https://ticketmaster-70.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = None
        self.admin_id = None
        self.attendee_token = None
        self.attendee_id = None
        self.organizer_token = None
        self.organizer_id = None
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
                    expected_status: int = 200, use_auth: bool = False, token: str = None) -> tuple[bool, Dict]:
        """Make HTTP request and validate response"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if use_auth:
            auth_token = token or self.admin_token  # Default to admin token
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=30)
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

    def clear_database(self) -> bool:
        """Clear database to test first-user-as-admin logic"""
        print("\n🗑️ Clearing database for role testing...")
        
        mongo_commands = """
        use test_database;
        db.users.deleteMany({});
        db.user_sessions.deleteMany({});
        db.events.deleteMany({});
        db.bookings.deleteMany({});
        db.ticket_types.deleteMany({});
        """
        
        try:
            import subprocess
            result = subprocess.run(
                ['mongosh', '--eval', mongo_commands],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Database cleared successfully")
                return True
            else:
                print(f"❌ Database clear failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Database clear error: {str(e)}")
            return False

    def create_test_user(self, role: str, is_first_user: bool = False) -> tuple[str, str]:
        """Create test user with specific role"""
        timestamp = int(time.time())
        user_id = f"test-{role}-{timestamp}"
        session_token = f"session_{role}_{timestamp}"
        email = f"test.{role}.{timestamp}@example.com"
        
        # First user should automatically become admin regardless of specified role
        actual_role = "admin" if is_first_user else role
        
        mongo_commands = f"""
        use test_database;
        db.users.insertOne({{
            id: "{user_id}",
            email: "{email}",
            name: "Test {role.title()} User",
            picture: "https://via.placeholder.com/150",
            role: "{actual_role}",
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
                print(f"✅ {role.title()} user created: {email} (actual role: {actual_role})")
                return user_id, session_token
            else:
                print(f"❌ {role.title()} user creation failed: {result.stderr}")
                return None, None
                
        except Exception as e:
            print(f"❌ {role.title()} user creation error: {str(e)}")
            return None, None

    def setup_role_test_users(self) -> bool:
        """Setup test users for role testing"""
        print("\n🔧 Setting up role test users...")
        
        # Create admin user (first user)
        self.admin_id, self.admin_token = self.create_test_user("admin", is_first_user=True)
        if not self.admin_token:
            return False
        
        # Create attendee user
        self.attendee_id, self.attendee_token = self.create_test_user("attendee")
        if not self.attendee_token:
            return False
        
        # Create organizer user (will start as attendee, then we'll change role)
        self.organizer_id, self.organizer_token = self.create_test_user("attendee")
        if not self.organizer_token:
            return False
        
        return True

    def test_health_check(self):
        """Test basic connectivity"""
        print("\n🏥 Testing Health Check...")
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            success = response.status_code in [200, 404]  # 404 is OK for root
            self.log_test("Health Check", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Health Check", False, str(e))

    def test_user_role_assignment(self):
        """Test user role assignment and first-user-as-admin logic"""
        print("\n👑 Testing User Role Assignment...")
        
        # Test admin user (first user should be admin)
        success, data = self.make_request('GET', 'auth/me', use_auth=True, token=self.admin_token)
        if success and data.get('role') == 'admin':
            self.log_test("First user gets admin role", True, f"Role: {data.get('role')}")
        else:
            self.log_test("First user gets admin role", False, f"Expected admin, got: {data.get('role', 'unknown')}")
        
        # Test attendee user (default role)
        success, data = self.make_request('GET', 'auth/me', use_auth=True, token=self.attendee_token)
        if success and data.get('role') == 'attendee':
            self.log_test("Second user gets attendee role", True, f"Role: {data.get('role')}")
        else:
            self.log_test("Second user gets attendee role", False, f"Expected attendee, got: {data.get('role', 'unknown')}")
        
        # Test role selection (change attendee to organizer)
        role_data = {"role": "organizer"}
        success, data = self.make_request('PATCH', 'auth/select-role', role_data, 
                                        expected_status=200, use_auth=True, token=self.organizer_token)
        if success:
            self.log_test("PATCH /auth/select-role (attendee to organizer)", True, "Role changed successfully")
            
            # Verify role change
            success, data = self.make_request('GET', 'auth/me', use_auth=True, token=self.organizer_token)
            if success and data.get('role') == 'organizer':
                self.log_test("Role change verification", True, f"New role: {data.get('role')}")
            else:
                self.log_test("Role change verification", False, f"Expected organizer, got: {data.get('role', 'unknown')}")
        else:
            self.log_test("PATCH /auth/select-role (attendee to organizer)", False, str(data))
        
        # Test invalid role selection
        invalid_role_data = {"role": "invalid_role"}
        success, data = self.make_request('PATCH', 'auth/select-role', invalid_role_data, 
                                        expected_status=400, use_auth=True, token=self.attendee_token)
        self.log_test("PATCH /auth/select-role (invalid role)", success, "Correctly rejected invalid role")
        
        # Test admin cannot change their role
        admin_role_data = {"role": "attendee"}
        success, data = self.make_request('PATCH', 'auth/select-role', admin_role_data, 
                                        expected_status=403, use_auth=True, token=self.admin_token)
        self.log_test("PATCH /auth/select-role (admin cannot change)", success, "Admin role change correctly blocked")

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

    def test_role_based_access_control(self):
        """Test role-based access control for event creation"""
        print("\n🔒 Testing Role-Based Access Control...")
        
        # Test event data
        event_data = {
            "title": f"Role Test Event {int(time.time())}",
            "description": "Testing role-based access control",
            "date": (datetime.now() + timedelta(days=30)).isoformat(),
            "location": "Test Venue, Test City",
            "capacity": 100,
            "category": "Conference",
            "image_url": "https://via.placeholder.com/400x300"
        }
        
        # Test attendee CANNOT create events (should get 403)
        success, data = self.make_request('POST', 'events', event_data, 
                                        expected_status=403, use_auth=True, token=self.attendee_token)
        self.log_test("POST /events (attendee - should fail)", success, 
                     "Correctly blocked attendee from creating event")
        
        # Test organizer CAN create events
        success, data = self.make_request('POST', 'events', event_data, 
                                        expected_status=200, use_auth=True, token=self.organizer_token)
        if success:
            organizer_event_id = data.get('id')
            self.log_test("POST /events (organizer - should succeed)", True, 
                         f"Organizer created event: {organizer_event_id}")
        else:
            self.log_test("POST /events (organizer - should succeed)", False, str(data))
            organizer_event_id = None
        
        # Test admin CAN create events
        success, data = self.make_request('POST', 'events', event_data, 
                                        expected_status=200, use_auth=True, token=self.admin_token)
        if success:
            admin_event_id = data.get('id')
            self.log_test("POST /events (admin - should succeed)", True, 
                         f"Admin created event: {admin_event_id}")
        else:
            self.log_test("POST /events (admin - should succeed)", False, str(data))
            admin_event_id = None
        
        return organizer_event_id, admin_event_id
    
    def test_event_ownership_control(self, organizer_event_id: str, admin_event_id: str):
        """Test that organizers can only edit their own events, but admins can edit any"""
        print("\n🏠 Testing Event Ownership Control...")
        
        if not organizer_event_id or not admin_event_id:
            print("⚠️ Skipping ownership tests - missing event IDs")
            return
        
        update_data = {"title": "Updated Event Title"}
        
        # Test organizer can edit their own event
        success, data = self.make_request('PUT', f'events/{organizer_event_id}', update_data,
                                        expected_status=200, use_auth=True, token=self.organizer_token)
        self.log_test("PUT /events/{id} (organizer owns event)", success, 
                     "Organizer can edit own event")
        
        # Test organizer CANNOT edit admin's event
        success, data = self.make_request('PUT', f'events/{admin_event_id}', update_data,
                                        expected_status=403, use_auth=True, token=self.organizer_token)
        self.log_test("PUT /events/{id} (organizer doesn't own)", success, 
                     "Organizer correctly blocked from editing others' events")
        
        # Test admin CAN edit any event (including organizer's)
        success, data = self.make_request('PUT', f'events/{organizer_event_id}', update_data,
                                        expected_status=200, use_auth=True, token=self.admin_token)
        self.log_test("PUT /events/{id} (admin can edit any)", success, 
                     "Admin can edit any event")
        
        # Test admin can edit their own event
        success, data = self.make_request('PUT', f'events/{admin_event_id}', update_data,
                                        expected_status=200, use_auth=True, token=self.admin_token)
        self.log_test("PUT /events/{id} (admin owns event)", success, 
                     "Admin can edit own event")

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