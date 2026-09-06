#!/usr/bin/env python3
"""
Backend API Test Suite for ALDI MOTOR
Tests price removal and WhatsApp number change features
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Optional

# Configuration
BASE_URL = "https://bf4f7221-ce61-49f2-a3c1-cc17b0180a7b.preview.emergentagent.com/api"
ADMIN_USERNAME = "adminaldimotor"
ADMIN_PASSWORD = "aldimotorjaya"
EXPECTED_WA = "6285657237827"

# Test results tracking
test_results = []


def log_test(test_name: str, passed: bool, message: str):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if not passed or message:
        print(f"   {message}")
    test_results.append({"test": test_name, "passed": passed, "message": message})


def admin_login() -> Optional[str]:
    """Login as admin and return JWT token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            log_test("Admin Login", True, f"Logged in as {data['user']['username']}")
            return token
        else:
            log_test("Admin Login", False, f"Status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        log_test("Admin Login", False, f"Exception: {str(e)}")
        return None


def test_1_services_no_price():
    """Test 1: GET /api/services - verify no price key"""
    try:
        response = requests.get(f"{BASE_URL}/services", timeout=10)
        if response.status_code != 200:
            log_test("1. GET /api/services", False, f"Status {response.status_code}")
            return
        
        services = response.json()
        if not isinstance(services, list):
            log_test("1. GET /api/services", False, "Response is not a list")
            return
        
        if len(services) != 4:
            log_test("1. GET /api/services", False, f"Expected 4 services, got {len(services)}")
            return
        
        # Check that NONE of them has a "price" key
        services_with_price = [s for s in services if "price" in s]
        if services_with_price:
            log_test("1. GET /api/services", False, 
                    f"Found {len(services_with_price)} services with 'price' key: {[s.get('name') for s in services_with_price]}")
            return
        
        log_test("1. GET /api/services", True, 
                f"All 4 services returned without 'price' key: {[s.get('name') for s in services]}")
        return services
    except Exception as e:
        log_test("1. GET /api/services", False, f"Exception: {str(e)}")
        return None


def test_2_availability_flow(services):
    """Test 2: GET business hours, holidays, availability"""
    try:
        # Get business hours
        response = requests.get(f"{BASE_URL}/business-hours", timeout=10)
        if response.status_code != 200:
            log_test("2. GET /api/business-hours", False, f"Status {response.status_code}")
            return None, None
        
        bh_data = response.json()
        min_date = bh_data.get("min_date")
        max_date = bh_data.get("max_date")
        
        if not min_date or not max_date:
            log_test("2. GET /api/business-hours", False, "Missing min_date or max_date")
            return None, None
        
        log_test("2. GET /api/business-hours", True, 
                f"min_date={min_date}, max_date={max_date}")
        
        # Get holidays
        response = requests.get(f"{BASE_URL}/holidays", timeout=10)
        if response.status_code != 200:
            log_test("2. GET /api/holidays", False, f"Status {response.status_code}")
            return None, None
        
        holidays = response.json()
        holiday_dates = [h.get("date") for h in holidays]
        log_test("2. GET /api/holidays", True, 
                f"Retrieved {len(holidays)} holidays")
        
        # Find a valid date (not Sunday, not holiday)
        min_dt = datetime.strptime(min_date, "%Y-%m-%d")
        max_dt = datetime.strptime(max_date, "%Y-%m-%d")
        
        test_date = None
        current = min_dt
        while current <= max_dt:
            if current.weekday() != 6 and current.strftime("%Y-%m-%d") not in holiday_dates:
                test_date = current.strftime("%Y-%m-%d")
                break
            current += timedelta(days=1)
        
        if not test_date:
            log_test("2. Find valid booking date", False, "No valid date found")
            return None, None
        
        log_test("2. Find valid booking date", True, f"Using date: {test_date}")
        
        # Get availability for "Servis Ringan"
        ringan_service = next((s for s in services if s.get("code") == "ringan"), None)
        if not ringan_service:
            log_test("2. GET /api/availability", False, "Servis Ringan not found")
            return None, None
        
        response = requests.get(
            f"{BASE_URL}/availability",
            params={"date": test_date, "service_id": ringan_service["id"]},
            timeout=10
        )
        
        if response.status_code != 200:
            log_test("2. GET /api/availability", False, f"Status {response.status_code}")
            return None, None
        
        avail_data = response.json()
        slots = avail_data.get("slots", [])
        available_slot = next((s for s in slots if s.get("status") == "available"), None)
        
        if not available_slot:
            log_test("2. GET /api/availability", False, "No available slots found")
            return None, None
        
        log_test("2. GET /api/availability", True, 
                f"Found available slot at {available_slot['time']}")
        
        return test_date, available_slot["time"], ringan_service["id"]
    
    except Exception as e:
        log_test("2. Availability flow", False, f"Exception: {str(e)}")
        return None, None


def test_3_create_booking(test_date, start_time, service_id):
    """Test 3: POST /api/bookings - verify no price, correct WA number"""
    try:
        booking_data = {
            "customer_name": "Test Backend",
            "whatsapp": "081234567890",
            "plate_number": "DD 1234 TB",
            "complaint": "cek rem",
            "service_id": service_id,
            "booking_date": test_date,
            "start_time": start_time
        }
        
        response = requests.post(
            f"{BASE_URL}/bookings",
            json=booking_data,
            timeout=10
        )
        
        if response.status_code != 200:
            log_test("3. POST /api/bookings", False, 
                    f"Status {response.status_code}: {response.text}")
            return None
        
        data = response.json()
        booking = data.get("booking")
        workshop_wa = data.get("workshop_whatsapp")
        wa_customer_link = data.get("wa_customer_link")
        wa_admin_link = data.get("wa_admin_link")
        
        # Check 1: booking has NO "price" key
        if "price" in booking:
            log_test("3. POST /api/bookings - no price", False, 
                    f"Booking contains 'price' key: {booking.get('price')}")
            return None
        
        log_test("3. POST /api/bookings - no price", True, 
                "Booking has no 'price' key")
        
        # Check 2: workshop_whatsapp == "6285657237827"
        if workshop_wa != EXPECTED_WA:
            log_test("3. POST /api/bookings - WA number", False, 
                    f"Expected {EXPECTED_WA}, got {workshop_wa}")
            return None
        
        log_test("3. POST /api/bookings - WA number", True, 
                f"workshop_whatsapp = {EXPECTED_WA}")
        
        # Check 3: wa_customer_link starts with correct URL
        expected_link_prefix = f"https://wa.me/{EXPECTED_WA}"
        if not wa_customer_link.startswith(expected_link_prefix):
            log_test("3. POST /api/bookings - customer link", False, 
                    f"Link doesn't start with {expected_link_prefix}")
            return None
        
        log_test("3. POST /api/bookings - customer link", True, 
                f"wa_customer_link starts with {expected_link_prefix}")
        
        # Check 4: wa_admin_link also uses correct WA
        if not wa_admin_link.startswith(expected_link_prefix):
            log_test("3. POST /api/bookings - admin link", False, 
                    f"Link doesn't start with {expected_link_prefix}")
            return None
        
        log_test("3. POST /api/bookings - admin link", True, 
                f"wa_admin_link uses {EXPECTED_WA}")
        
        return booking["id"]
    
    except Exception as e:
        log_test("3. POST /api/bookings", False, f"Exception: {str(e)}")
        return None


def test_4_admin_bookings(token, booking_id):
    """Test 4: GET /api/admin/bookings - verify no price key"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/admin/bookings",
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            log_test("4. GET /api/admin/bookings", False, 
                    f"Status {response.status_code}")
            return
        
        bookings = response.json()
        if not isinstance(bookings, list):
            log_test("4. GET /api/admin/bookings", False, "Response is not a list")
            return
        
        # Check that NONE of them has a "price" key
        bookings_with_price = [b for b in bookings if "price" in b]
        if bookings_with_price:
            log_test("4. GET /api/admin/bookings", False, 
                    f"Found {len(bookings_with_price)} bookings with 'price' key")
            return
        
        log_test("4. GET /api/admin/bookings", True, 
                f"All {len(bookings)} bookings have no 'price' key")
    
    except Exception as e:
        log_test("4. GET /api/admin/bookings", False, f"Exception: {str(e)}")


def test_5_update_booking(token, booking_id):
    """Test 5: PATCH /api/admin/bookings - status works, price ignored"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 5a: Update status to "Dikonfirmasi"
        response = requests.patch(
            f"{BASE_URL}/admin/bookings/{booking_id}",
            headers=headers,
            json={"status": "Dikonfirmasi"},
            timeout=10
        )
        
        if response.status_code != 200:
            log_test("5a. PATCH booking status", False, 
                    f"Status {response.status_code}")
            return
        
        updated = response.json()
        if updated.get("status") != "Dikonfirmasi":
            log_test("5a. PATCH booking status", False, 
                    f"Status not updated: {updated.get('status')}")
            return
        
        log_test("5a. PATCH booking status", True, 
                "Status updated to 'Dikonfirmasi'")
        
        # Test 5b: Try to add price field (should be ignored)
        response = requests.patch(
            f"{BASE_URL}/admin/bookings/{booking_id}",
            headers=headers,
            json={"price": 5000},
            timeout=10
        )
        
        if response.status_code != 200:
            log_test("5b. PATCH booking with price", False, 
                    f"Status {response.status_code}")
            return
        
        updated = response.json()
        if "price" in updated:
            log_test("5b. PATCH booking with price", False, 
                    f"Price field was added: {updated.get('price')}")
            return
        
        log_test("5b. PATCH booking with price", True, 
                "Price field ignored (not added to booking)")
    
    except Exception as e:
        log_test("5. PATCH /api/admin/bookings", False, f"Exception: {str(e)}")


def test_6_update_service(token, service_id):
    """Test 6: PATCH /api/admin/services - duration works, price alone returns 400"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 6a: Update duration_hours
        response = requests.patch(
            f"{BASE_URL}/admin/services/{service_id}",
            headers=headers,
            json={"duration_hours": 1},
            timeout=10
        )
        
        if response.status_code != 200:
            log_test("6a. PATCH service duration", False, 
                    f"Status {response.status_code}")
            return
        
        log_test("6a. PATCH service duration", True, 
                "Duration updated successfully")
        
        # Test 6b: Try to update price alone (should return 400)
        response = requests.patch(
            f"{BASE_URL}/admin/services/{service_id}",
            headers=headers,
            json={"price": 100},
            timeout=10
        )
        
        if response.status_code != 400:
            log_test("6b. PATCH service price only", False, 
                    f"Expected 400, got {response.status_code}")
            return
        
        error_data = response.json()
        if "Tidak ada perubahan" not in error_data.get("detail", ""):
            log_test("6b. PATCH service price only", False, 
                    f"Expected 'Tidak ada perubahan', got: {error_data.get('detail')}")
            return
        
        log_test("6b. PATCH service price only", True, 
                "Returns 400 'Tidak ada perubahan' (price field not recognized)")
    
    except Exception as e:
        log_test("6. PATCH /api/admin/services", False, f"Exception: {str(e)}")


def test_7_monthly_report(token, test_date):
    """Test 7: GET /api/admin/reports/monthly - no revenue fields"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Use the year and month from test_date
        dt = datetime.strptime(test_date, "%Y-%m-%d")
        year = dt.year
        month = dt.month
        
        response = requests.get(
            f"{BASE_URL}/admin/reports/monthly",
            headers=headers,
            params={"year": year, "month": month},
            timeout=10
        )
        
        if response.status_code != 200:
            log_test("7. GET /api/admin/reports/monthly", False, 
                    f"Status {response.status_code}")
            return
        
        data = response.json()
        
        # Check required keys exist
        required_keys = ["total", "active_total", "completed_total", "by_status", "by_service", "bookings"]
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            log_test("7. Monthly report - required keys", False, 
                    f"Missing keys: {missing_keys}")
            return
        
        log_test("7. Monthly report - required keys", True, 
                f"Has all required keys: {required_keys}")
        
        # Check that revenue fields do NOT exist
        revenue_keys = [k for k in data.keys() if "revenue" in k.lower()]
        if revenue_keys:
            log_test("7. Monthly report - no revenue", False, 
                    f"Found revenue keys: {revenue_keys}")
            return
        
        log_test("7. Monthly report - no revenue", True, 
                "No revenue_total or revenue_completed fields")
    
    except Exception as e:
        log_test("7. GET /api/admin/reports/monthly", False, f"Exception: {str(e)}")


def test_8_monthly_pdf(token, test_date):
    """Test 8: GET /api/admin/reports/monthly.pdf - PDF download"""
    try:
        dt = datetime.strptime(test_date, "%Y-%m-%d")
        year = dt.year
        month = dt.month
        
        response = requests.get(
            f"{BASE_URL}/admin/reports/monthly.pdf",
            params={"year": year, "month": month, "token": token},
            timeout=15
        )
        
        if response.status_code != 200:
            log_test("8. GET /api/admin/reports/monthly.pdf", False, 
                    f"Status {response.status_code}")
            return
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        if "application/pdf" not in content_type:
            log_test("8. PDF content-type", False, 
                    f"Expected application/pdf, got {content_type}")
            return
        
        log_test("8. PDF content-type", True, 
                f"Content-Type: {content_type}")
        
        # Check PDF signature
        content = response.content
        if not content.startswith(b"%PDF"):
            log_test("8. PDF signature", False, 
                    "Content doesn't start with %PDF")
            return
        
        log_test("8. PDF signature", True, 
                f"PDF file generated ({len(content)} bytes)")
    
    except Exception as e:
        log_test("8. GET /api/admin/reports/monthly.pdf", False, f"Exception: {str(e)}")


def test_9_admin_stats(token):
    """Test 9: GET /api/admin/stats - basic check"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BASE_URL}/admin/stats",
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            log_test("9. GET /api/admin/stats", False, 
                    f"Status {response.status_code}")
            return
        
        data = response.json()
        required_keys = ["total", "today", "tomorrow", "by_status"]
        missing_keys = [k for k in required_keys if k not in data]
        
        if missing_keys:
            log_test("9. GET /api/admin/stats", False, 
                    f"Missing keys: {missing_keys}")
            return
        
        log_test("9. GET /api/admin/stats", True, 
                f"Stats retrieved: total={data['total']}, today={data['today']}, tomorrow={data['tomorrow']}")
    
    except Exception as e:
        log_test("9. GET /api/admin/stats", False, f"Exception: {str(e)}")


def main():
    """Run all tests"""
    print("=" * 70)
    print("ALDI MOTOR Backend API Test Suite")
    print("Testing: Price removal & WhatsApp number change")
    print("=" * 70)
    print()
    
    # Login
    token = admin_login()
    if not token:
        print("\n❌ Cannot proceed without admin token")
        return
    
    print()
    
    # Test 1: Services without price
    services = test_1_services_no_price()
    if not services:
        print("\n❌ Cannot proceed without services data")
        return
    
    print()
    
    # Test 2: Availability flow
    result = test_2_availability_flow(services)
    if result == (None, None):
        print("\n❌ Cannot proceed without valid booking date/time")
        return
    
    test_date, start_time, service_id = result
    print()
    
    # Test 3: Create booking
    booking_id = test_3_create_booking(test_date, start_time, service_id)
    if not booking_id:
        print("\n⚠️  Booking creation failed, some tests will be skipped")
    
    print()
    
    # Test 4: Admin bookings
    test_4_admin_bookings(token, booking_id)
    print()
    
    # Test 5: Update booking
    if booking_id:
        test_5_update_booking(token, booking_id)
        print()
    
    # Test 6: Update service
    test_6_update_service(token, service_id)
    print()
    
    # Test 7: Monthly report
    test_7_monthly_report(token, test_date)
    print()
    
    # Test 8: Monthly PDF
    test_8_monthly_pdf(token, test_date)
    print()
    
    # Test 9: Admin stats
    test_9_admin_stats(token)
    print()
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in test_results if r["passed"])
    total = len(test_results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    failed_tests = [r for r in test_results if not r["passed"]]
    if failed_tests:
        print(f"\n❌ Failed tests ({len(failed_tests)}):")
        for r in failed_tests:
            print(f"   - {r['test']}")
            if r['message']:
                print(f"     {r['message']}")
    else:
        print("\n✅ All tests passed!")
    
    print()


if __name__ == "__main__":
    main()
