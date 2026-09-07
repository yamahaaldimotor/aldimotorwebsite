#!/usr/bin/env python3
"""
ALDI MOTOR Backend Test Suite - Motor Type Feature
Tests the new motor_type field on POST /api/bookings
"""
import os
import sys
import requests
from datetime import datetime, timedelta
import time

# Backend URL from frontend/.env
BACKEND_URL = "https://repo-sync-122.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
ADMIN_USERNAME = "adminaldimotor"
ADMIN_PASSWORD = "aldimotorjaya"

# Test state
token = None
test_booking_id = None
test_results = []


def log_test(step, status, message):
    """Log test result"""
    symbol = "✅" if status == "PASS" else "❌"
    print(f"{symbol} Step {step}: {message}")
    test_results.append({"step": step, "status": status, "message": message})


def login():
    """Login and get JWT token"""
    global token
    print("\n=== AUTHENTICATION ===")
    resp = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=10
    )
    if resp.status_code != 200:
        log_test("LOGIN", "FAIL", f"Login failed: {resp.status_code} - {resp.text}")
        sys.exit(1)
    
    data = resp.json()
    token = data.get("token")
    if not token:
        log_test("LOGIN", "FAIL", "No token in response")
        sys.exit(1)
    
    log_test("LOGIN", "PASS", f"Login successful, token received")
    return token


def get_valid_booking_date():
    """Get a valid booking date (non-Sunday, within business hours range)"""
    print("\n=== STEP 1: Get valid booking date ===")
    
    # Get business hours
    resp = requests.get(f"{API_BASE}/business-hours", timeout=10)
    if resp.status_code != 200:
        log_test("1a", "FAIL", f"GET /api/business-hours returned {resp.status_code}")
        return None, None
    
    bh = resp.json()
    min_date = bh.get("min_date")
    max_date = bh.get("max_date")
    
    if not min_date or not max_date:
        log_test("1a", "FAIL", f"Business hours missing min_date or max_date")
        return None, None
    
    log_test("1a", "PASS", f"Business hours: min_date={min_date}, max_date={max_date}")
    
    # Get holidays
    resp = requests.get(f"{API_BASE}/holidays", timeout=10)
    if resp.status_code != 200:
        log_test("1b", "FAIL", f"GET /api/holidays returned {resp.status_code}")
        return None, None
    
    holidays = resp.json()
    holiday_dates = [h.get("date") for h in holidays]
    log_test("1b", "PASS", f"Got {len(holiday_dates)} holidays")
    
    # Find a valid date (non-Sunday, not holiday)
    current_date = datetime.strptime(min_date, "%Y-%m-%d")
    max_date_obj = datetime.strptime(max_date, "%Y-%m-%d")
    
    valid_date = None
    while current_date <= max_date_obj:
        date_str = current_date.strftime("%Y-%m-%d")
        # Check if Sunday (weekday 6)
        if current_date.weekday() != 6 and date_str not in holiday_dates:
            valid_date = date_str
            break
        current_date += timedelta(days=1)
    
    if not valid_date:
        log_test("1c", "FAIL", "No valid booking date found in range")
        return None, None
    
    log_test("1c", "PASS", f"Found valid booking date: {valid_date}")
    return valid_date, bh


def get_service_and_availability(booking_date):
    """Get service ID and available slot"""
    print("\n=== STEP 1 (continued): Get service and availability ===")
    
    # Get services
    resp = requests.get(f"{API_BASE}/services", timeout=10)
    if resp.status_code != 200:
        log_test("1d", "FAIL", f"GET /api/services returned {resp.status_code}")
        return None, None
    
    services = resp.json()
    ringan_service = None
    for svc in services:
        if svc.get("code") == "ringan":
            ringan_service = svc
            break
    
    if not ringan_service:
        log_test("1d", "FAIL", "Ringan service not found")
        return None, None
    
    service_id = ringan_service.get("id")
    log_test("1d", "PASS", f"Found ringan service: id={service_id}")
    
    # Get availability
    resp = requests.get(
        f"{API_BASE}/availability",
        params={"date": booking_date, "service_id": service_id},
        timeout=10
    )
    if resp.status_code != 200:
        log_test("1e", "FAIL", f"GET /api/availability returned {resp.status_code}")
        return None, None
    
    availability = resp.json()
    slots = availability.get("slots", [])
    
    # Find an available slot (not closed, not full)
    available_slot = None
    for slot in slots:
        if slot.get("status") not in ["closed", "full"]:
            available_slot = slot.get("time")
            break
    
    if not available_slot:
        log_test("1e", "FAIL", "No available slot found")
        return None, None
    
    log_test("1e", "PASS", f"Found available slot: {available_slot}")
    return service_id, available_slot


def test_booking_without_motor_type(booking_date, service_id, start_time):
    """Test 2: POST /api/bookings without motor_type - should return 422"""
    print("\n=== TEST 2: POST /api/bookings without motor_type ===")
    
    booking_data = {
        "customer_name": "Tester Motor",
        "whatsapp": "081200002222",
        "plate_number": "DD 2 TM",
        # motor_type is missing
        "complaint": "tes motor type",
        "service_id": service_id,
        "booking_date": booking_date,
        "start_time": start_time
    }
    
    resp = requests.post(f"{API_BASE}/bookings", json=booking_data, timeout=10)
    
    if resp.status_code != 422:
        log_test("2", "FAIL", f"Expected 422 without motor_type, got {resp.status_code}: {resp.text}")
        return False
    
    log_test("2", "PASS", "Correctly rejected booking without motor_type with 422")
    return True


def test_booking_with_short_motor_type(booking_date, service_id, start_time):
    """Test 3: POST /api/bookings with motor_type 'X' (1 char) - should return 422"""
    print("\n=== TEST 3: POST /api/bookings with motor_type 'X' (1 char) ===")
    
    booking_data = {
        "customer_name": "Tester Motor",
        "whatsapp": "081200002222",
        "plate_number": "DD 2 TM",
        "motor_type": "X",  # Too short (min_length=2)
        "complaint": "tes motor type",
        "service_id": service_id,
        "booking_date": booking_date,
        "start_time": start_time
    }
    
    resp = requests.post(f"{API_BASE}/bookings", json=booking_data, timeout=10)
    
    if resp.status_code != 422:
        log_test("3", "FAIL", f"Expected 422 with motor_type 'X', got {resp.status_code}: {resp.text}")
        return False
    
    log_test("3", "PASS", "Correctly rejected booking with motor_type 'X' (1 char) with 422")
    return True


def test_booking_with_valid_motor_type(booking_date, service_id, start_time):
    """Test 4: POST /api/bookings with valid motor_type 'Yamaha NMAX 155' - should return 200"""
    global test_booking_id
    print("\n=== TEST 4: POST /api/bookings with valid motor_type ===")
    
    booking_data = {
        "customer_name": "Tester Motor",
        "whatsapp": "081200002222",
        "plate_number": "DD 2 TM",
        "motor_type": "Yamaha NMAX 155",
        "complaint": "tes motor type",
        "service_id": service_id,
        "booking_date": booking_date,
        "start_time": start_time
    }
    
    resp = requests.post(f"{API_BASE}/bookings", json=booking_data, timeout=10)
    
    if resp.status_code != 200:
        log_test("4", "FAIL", f"POST /api/bookings returned {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    booking = data.get("booking")
    
    if not booking:
        log_test("4", "FAIL", "No booking in response")
        return False
    
    test_booking_id = booking.get("id")
    
    # Check motor_type in response
    if booking.get("motor_type") != "Yamaha NMAX 155":
        log_test("4", "FAIL", f"motor_type mismatch: expected 'Yamaha NMAX 155', got '{booking.get('motor_type')}'")
        return False
    
    # Check wa_customer_link contains "Jenis"
    wa_customer_link = data.get("wa_customer_link", "")
    if "Jenis" not in wa_customer_link:
        log_test("4", "FAIL", f"wa_customer_link doesn't contain 'Jenis': {wa_customer_link}")
        return False
    
    # Check wa_admin_link contains "Jenis"
    wa_admin_link = data.get("wa_admin_link", "")
    if "Jenis" not in wa_admin_link:
        log_test("4", "FAIL", f"wa_admin_link doesn't contain 'Jenis': {wa_admin_link}")
        return False
    
    log_test("4", "PASS", f"Booking created successfully with motor_type='Yamaha NMAX 155', id={test_booking_id}, WA links contain 'Jenis'")
    return True


def test_admin_bookings_has_motor_type():
    """Test 5: GET /api/admin/bookings - verify booking has motor_type"""
    print("\n=== TEST 5: GET /api/admin/bookings ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE}/admin/bookings", headers=headers, timeout=10)
    
    if resp.status_code != 200:
        log_test("5", "FAIL", f"GET /api/admin/bookings returned {resp.status_code}")
        return False
    
    bookings = resp.json()
    
    # Find our test booking
    test_booking = None
    for b in bookings:
        if b.get("id") == test_booking_id:
            test_booking = b
            break
    
    if not test_booking:
        log_test("5", "FAIL", f"Test booking {test_booking_id} not found in admin bookings")
        return False
    
    if test_booking.get("motor_type") != "Yamaha NMAX 155":
        log_test("5", "FAIL", f"motor_type mismatch: expected 'Yamaha NMAX 155', got '{test_booking.get('motor_type')}'")
        return False
    
    log_test("5", "PASS", f"Admin bookings contains test booking with motor_type='Yamaha NMAX 155'")
    return True


def test_customer_history_has_motor_type():
    """Test 6: GET /api/customer/history?plate=DD%202%20TM - verify motor_type"""
    print("\n=== TEST 6: GET /api/customer/history ===")
    
    resp = requests.get(
        f"{API_BASE}/customer/history",
        params={"plate": "DD 2 TM"},
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("6", "FAIL", f"GET /api/customer/history returned {resp.status_code}")
        return False
    
    data = resp.json()
    recent_list = data.get("recent", [])
    
    if not recent_list or len(recent_list) == 0:
        log_test("6", "FAIL", "No recent bookings found for plate 'DD 2 TM'")
        return False
    
    # Check the most recent booking (should be our test booking)
    recent = recent_list[0]
    
    if recent.get("motor_type") != "Yamaha NMAX 155":
        log_test("6", "FAIL", f"motor_type mismatch: expected 'Yamaha NMAX 155', got '{recent.get('motor_type')}'")
        return False
    
    log_test("6", "PASS", f"Customer history contains booking with motor_type='Yamaha NMAX 155'")
    return True


def test_monthly_pdf_report(booking_date):
    """Test 7: GET /api/admin/reports/monthly.pdf - verify PDF generation"""
    print("\n=== TEST 7: GET /api/admin/reports/monthly.pdf ===")
    
    # Extract year and month from booking_date
    date_obj = datetime.strptime(booking_date, "%Y-%m-%d")
    year = date_obj.year
    month = date_obj.month
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{API_BASE}/admin/reports/monthly.pdf",
        params={"year": year, "month": month, "token": token},
        headers=headers,
        timeout=15
    )
    
    if resp.status_code != 200:
        log_test("7", "FAIL", f"GET /api/admin/reports/monthly.pdf returned {resp.status_code}: {resp.text}")
        return False
    
    # Check content type
    content_type = resp.headers.get("content-type", "")
    if "application/pdf" not in content_type:
        log_test("7", "FAIL", f"Content-Type is {content_type}, expected application/pdf")
        return False
    
    # Check PDF signature
    if not resp.content.startswith(b"%PDF"):
        log_test("7", "FAIL", "Response doesn't start with %PDF")
        return False
    
    pdf_size = len(resp.content)
    log_test("7", "PASS", f"Monthly PDF generated successfully: {pdf_size} bytes, content-type=application/pdf, starts with %PDF")
    return True


def cleanup_test_booking():
    """Test 8: Cleanup - PATCH /api/admin/bookings/{id} status to 'Dibatalkan'"""
    print("\n=== TEST 8: Cleanup - Cancel test booking ===")
    
    if not test_booking_id:
        log_test("8", "SKIP", "No test booking to cleanup")
        return True
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.patch(
        f"{API_BASE}/admin/bookings/{test_booking_id}",
        json={"status": "Dibatalkan"},
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("8", "FAIL", f"PATCH /api/admin/bookings/{test_booking_id} returned {resp.status_code}: {resp.text}")
        return False
    
    log_test("8", "PASS", f"Test booking {test_booking_id} cancelled successfully")
    return True


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    skipped = sum(1 for r in test_results if r["status"] == "SKIP")
    total = len(test_results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    if skipped > 0:
        print(f"Skipped: {skipped} ⏭️")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for r in test_results:
            if r["status"] == "FAIL":
                print(f"  - Step {r['step']}: {r['message']}")
    
    print("\n" + "="*60)
    
    return failed == 0


def main():
    """Run all tests"""
    print("="*60)
    print("ALDI MOTOR - Motor Type Feature Test Suite")
    print("="*60)
    
    try:
        # Login
        login()
        
        # Step 1: Get valid booking date and service
        booking_date, bh = get_valid_booking_date()
        if not booking_date:
            print("\n❌ FATAL ERROR: Could not get valid booking date")
            return False
        
        service_id, start_time = get_service_and_availability(booking_date)
        if not service_id or not start_time:
            print("\n❌ FATAL ERROR: Could not get service or available slot")
            return False
        
        # Step 2: Test booking without motor_type
        test_booking_without_motor_type(booking_date, service_id, start_time)
        
        # Step 3: Test booking with short motor_type
        test_booking_with_short_motor_type(booking_date, service_id, start_time)
        
        # Step 4: Test booking with valid motor_type
        if not test_booking_with_valid_motor_type(booking_date, service_id, start_time):
            print("\n❌ FATAL ERROR: Could not create test booking")
            return False
        
        # Step 5: Test admin bookings
        test_admin_bookings_has_motor_type()
        
        # Step 6: Test customer history
        test_customer_history_has_motor_type()
        
        # Step 7: Test monthly PDF report
        test_monthly_pdf_report(booking_date)
        
        # Step 8: Cleanup
        cleanup_test_booking()
        
        # Print summary
        success = print_summary()
        
        return success
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
