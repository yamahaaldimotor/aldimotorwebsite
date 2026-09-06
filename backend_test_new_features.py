#!/usr/bin/env python3
"""
ALDI MOTOR Backend Testing - New Features
Tests for:
A) Schedule/Business Hours with Friday break
B) Admin Sparepart CRUD
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Optional

# Backend URL from frontend/.env
BASE_URL = "https://bf4f7221-ce61-49f2-a3c1-cc17b0180a7b.preview.emergentagent.com/api"

# Test credentials
ADMIN_USERNAME = "adminaldimotor"
ADMIN_PASSWORD = "aldimotorjaya"

# Global token storage
AUTH_TOKEN = None

# Test results tracking
test_results = []
created_bookings = []  # Track bookings to clean up
created_sparepart_id = None  # Track test sparepart


def log_test(step: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = f"{status} - Step {step}: {details}"
    test_results.append({"step": step, "passed": passed, "details": details})
    print(result)
    return passed


def login_admin() -> Optional[str]:
    """Login as admin and return token"""
    global AUTH_TOKEN
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            AUTH_TOKEN = data.get("token")
            log_test("Login", True, f"Admin logged in successfully")
            return AUTH_TOKEN
        else:
            log_test("Login", False, f"Login failed: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        log_test("Login", False, f"Login error: {str(e)}")
        return None


def get_auth_headers() -> dict:
    """Get authorization headers"""
    if not AUTH_TOKEN:
        login_admin()
    return {"Authorization": f"Bearer {AUTH_TOKEN}"}


def find_friday_date(min_date: str, max_date: str) -> Optional[str]:
    """Find a Friday between min_date and max_date"""
    start = datetime.strptime(min_date, "%Y-%m-%d")
    end = datetime.strptime(max_date, "%Y-%m-%d")
    current = start
    while current <= end:
        if current.weekday() == 4:  # Friday
            return current.strftime("%Y-%m-%d")
        current += timedelta(days=1)
    return None


def find_non_friday_weekday(min_date: str, max_date: str) -> Optional[str]:
    """Find a non-Friday weekday (Mon-Thu or Sat) between min_date and max_date"""
    start = datetime.strptime(min_date, "%Y-%m-%d")
    end = datetime.strptime(max_date, "%Y-%m-%d")
    current = start
    while current <= end:
        weekday = current.weekday()
        # Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        if weekday in [0, 1, 2, 3, 5]:  # Mon-Thu or Sat
            return current.strftime("%Y-%m-%d")
        current += timedelta(days=1)
    return None


# ============================================================================
# A) SCHEDULE TESTS
# ============================================================================

def test_a1_business_hours():
    """A1: GET /api/business-hours -> opening_time "08:30", closing_time "16:30", breaks contains Friday break"""
    try:
        resp = requests.get(f"{BASE_URL}/business-hours", timeout=10)
        if resp.status_code != 200:
            return log_test("A1", False, f"GET /api/business-hours returned {resp.status_code}")
        
        data = resp.json()
        
        # Check opening_time
        if data.get("opening_time") != "08:30":
            return log_test("A1", False, f"opening_time is '{data.get('opening_time')}', expected '08:30'")
        
        # Check closing_time
        if data.get("closing_time") != "16:30":
            return log_test("A1", False, f"closing_time is '{data.get('closing_time')}', expected '16:30'")
        
        # Check breaks contains Friday break
        breaks = data.get("breaks", [])
        friday_break = None
        for br in breaks:
            if br.get("weekday") == 4:  # Friday
                friday_break = br
                break
        
        if not friday_break:
            return log_test("A1", False, "No Friday break found in breaks array")
        
        if friday_break.get("start") != "11:00":
            return log_test("A1", False, f"Friday break start is '{friday_break.get('start')}', expected '11:00'")
        
        if friday_break.get("end") != "14:00":
            return log_test("A1", False, f"Friday break end is '{friday_break.get('end')}', expected '14:00'")
        
        return log_test("A1", True, "Business hours correct: 08:30-16:30 with Friday break 11:00-14:00")
    
    except Exception as e:
        return log_test("A1", False, f"Exception: {str(e)}")


def test_a2_get_service_ids():
    """A2: GET /api/services -> get IDs for 'ringan' (1h) and 'berat' (2h)"""
    try:
        resp = requests.get(f"{BASE_URL}/services", timeout=10)
        if resp.status_code != 200:
            return log_test("A2", False, f"GET /api/services returned {resp.status_code}")
        
        services = resp.json()
        ringan = None
        berat = None
        
        for svc in services:
            if svc.get("code") == "ringan" and svc.get("duration_hours") == 1.0:
                ringan = svc
            elif svc.get("code") == "berat" and svc.get("duration_hours") == 2.0:
                berat = svc
        
        if not ringan:
            return log_test("A2", False, "Service 'ringan' (1h) not found")
        
        if not berat:
            return log_test("A2", False, "Service 'berat' (2h) not found")
        
        # Store for later tests
        global RINGAN_ID, BERAT_ID
        RINGAN_ID = ringan["id"]
        BERAT_ID = berat["id"]
        
        return log_test("A2", True, f"Found ringan (1h) id={RINGAN_ID}, berat (2h) id={BERAT_ID}")
    
    except Exception as e:
        return log_test("A2", False, f"Exception: {str(e)}")


def test_a3_availability_friday_ringan():
    """A3: GET /api/availability Friday + ringan -> slots [08:30,09:30,10:30,14:00,15:00,16:00], 10:30 & 16:00 closed"""
    try:
        # Get business hours to find date range
        bh_resp = requests.get(f"{BASE_URL}/business-hours", timeout=10)
        if bh_resp.status_code != 200:
            return log_test("A3", False, "Failed to get business hours")
        
        bh_data = bh_resp.json()
        min_date = bh_data.get("min_date")
        max_date = bh_data.get("max_date")
        
        friday_date = find_friday_date(min_date, max_date)
        if not friday_date:
            return log_test("A3", False, f"No Friday found between {min_date} and {max_date}")
        
        # Get availability for Friday + ringan
        resp = requests.get(
            f"{BASE_URL}/availability",
            params={"date": friday_date, "service_id": RINGAN_ID},
            timeout=10
        )
        
        if resp.status_code != 200:
            return log_test("A3", False, f"GET /api/availability returned {resp.status_code}: {resp.text}")
        
        data = resp.json()
        slots = data.get("slots", [])
        
        # Expected slot times
        expected_times = ["08:30", "09:30", "10:30", "14:00", "15:00", "16:00"]
        actual_times = [s["time"] for s in slots]
        
        if actual_times != expected_times:
            return log_test("A3", False, f"Slot times are {actual_times}, expected {expected_times}")
        
        # Check 10:30 is closed
        slot_1030 = next((s for s in slots if s["time"] == "10:30"), None)
        if not slot_1030 or slot_1030.get("status") != "closed":
            return log_test("A3", False, f"Slot 10:30 status is '{slot_1030.get('status') if slot_1030 else 'missing'}', expected 'closed'")
        
        # Check 16:00 is closed
        slot_1600 = next((s for s in slots if s["time"] == "16:00"), None)
        if not slot_1600 or slot_1600.get("status") != "closed":
            return log_test("A3", False, f"Slot 16:00 status is '{slot_1600.get('status') if slot_1600 else 'missing'}', expected 'closed'")
        
        # Check windows
        windows = data.get("windows", [])
        if len(windows) != 2:
            return log_test("A3", False, f"Expected 2 windows, got {len(windows)}")
        
        # Check breaks
        breaks = data.get("breaks", [])
        if len(breaks) != 1:
            return log_test("A3", False, f"Expected 1 break, got {len(breaks)}")
        
        return log_test("A3", True, f"Friday {friday_date} ringan: slots correct, 10:30 & 16:00 closed, 2 windows, 1 break")
    
    except Exception as e:
        return log_test("A3", False, f"Exception: {str(e)}")


def test_a4_availability_friday_berat():
    """A4: GET /api/availability Friday + berat -> 09:30, 10:30, 15:00, 16:00 closed; 08:30 & 14:00 not closed"""
    try:
        bh_resp = requests.get(f"{BASE_URL}/business-hours", timeout=10)
        bh_data = bh_resp.json()
        min_date = bh_data.get("min_date")
        max_date = bh_data.get("max_date")
        
        friday_date = find_friday_date(min_date, max_date)
        if not friday_date:
            return log_test("A4", False, "No Friday found")
        
        resp = requests.get(
            f"{BASE_URL}/availability",
            params={"date": friday_date, "service_id": BERAT_ID},
            timeout=10
        )
        
        if resp.status_code != 200:
            return log_test("A4", False, f"GET /api/availability returned {resp.status_code}")
        
        data = resp.json()
        slots = data.get("slots", [])
        
        # Check 09:30 is closed
        slot_0930 = next((s for s in slots if s["time"] == "09:30"), None)
        if not slot_0930 or slot_0930.get("status") != "closed":
            return log_test("A4", False, f"Slot 09:30 status is '{slot_0930.get('status') if slot_0930 else 'missing'}', expected 'closed'")
        
        # Check 10:30 is closed
        slot_1030 = next((s for s in slots if s["time"] == "10:30"), None)
        if not slot_1030 or slot_1030.get("status") != "closed":
            return log_test("A4", False, f"Slot 10:30 status is '{slot_1030.get('status') if slot_1030 else 'missing'}', expected 'closed'")
        
        # Check 15:00 is closed
        slot_1500 = next((s for s in slots if s["time"] == "15:00"), None)
        if not slot_1500 or slot_1500.get("status") != "closed":
            return log_test("A4", False, f"Slot 15:00 status is '{slot_1500.get('status') if slot_1500 else 'missing'}', expected 'closed'")
        
        # Check 16:00 is closed
        slot_1600 = next((s for s in slots if s["time"] == "16:00"), None)
        if not slot_1600 or slot_1600.get("status") != "closed":
            return log_test("A4", False, f"Slot 16:00 status is '{slot_1600.get('status') if slot_1600 else 'missing'}', expected 'closed'")
        
        # Check 08:30 is NOT closed
        slot_0830 = next((s for s in slots if s["time"] == "08:30"), None)
        if not slot_0830 or slot_0830.get("status") == "closed":
            return log_test("A4", False, f"Slot 08:30 should not be closed, status is '{slot_0830.get('status') if slot_0830 else 'missing'}'")
        
        # Check 14:00 is NOT closed
        slot_1400 = next((s for s in slots if s["time"] == "14:00"), None)
        if not slot_1400 or slot_1400.get("status") == "closed":
            return log_test("A4", False, f"Slot 14:00 should not be closed, status is '{slot_1400.get('status') if slot_1400 else 'missing'}'")
        
        return log_test("A4", True, f"Friday {friday_date} berat: 09:30,10:30,15:00,16:00 closed; 08:30,14:00 not closed")
    
    except Exception as e:
        return log_test("A4", False, f"Exception: {str(e)}")


def test_a5_availability_non_friday():
    """A5: GET /api/availability non-Friday weekday + ringan -> 8 slots 08:30..15:30, none closed"""
    try:
        bh_resp = requests.get(f"{BASE_URL}/business-hours", timeout=10)
        bh_data = bh_resp.json()
        min_date = bh_data.get("min_date")
        max_date = bh_data.get("max_date")
        
        non_friday = find_non_friday_weekday(min_date, max_date)
        if not non_friday:
            return log_test("A5", False, f"No non-Friday weekday found between {min_date} and {max_date}")
        
        resp = requests.get(
            f"{BASE_URL}/availability",
            params={"date": non_friday, "service_id": RINGAN_ID},
            timeout=10
        )
        
        if resp.status_code != 200:
            return log_test("A5", False, f"GET /api/availability returned {resp.status_code}")
        
        data = resp.json()
        slots = data.get("slots", [])
        
        # Expected 8 slots: 08:30, 09:30, 10:30, 11:30, 12:30, 13:30, 14:30, 15:30
        expected_times = ["08:30", "09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]
        actual_times = [s["time"] for s in slots]
        
        if actual_times != expected_times:
            return log_test("A5", False, f"Slot times are {actual_times}, expected {expected_times}")
        
        # Check none are closed
        closed_slots = [s["time"] for s in slots if s.get("status") == "closed"]
        if closed_slots:
            return log_test("A5", False, f"Slots {closed_slots} are closed, expected none closed")
        
        return log_test("A5", True, f"Non-Friday {non_friday} ringan: 8 slots 08:30-15:30, none closed")
    
    except Exception as e:
        return log_test("A5", False, f"Exception: {str(e)}")


def test_a6_booking_validations():
    """A6: POST /api/bookings - test various scenarios"""
    global created_bookings
    
    try:
        bh_resp = requests.get(f"{BASE_URL}/business-hours", timeout=10)
        bh_data = bh_resp.json()
        min_date = bh_data.get("min_date")
        max_date = bh_data.get("max_date")
        
        friday_date = find_friday_date(min_date, max_date)
        non_friday = find_non_friday_weekday(min_date, max_date)
        
        if not friday_date or not non_friday:
            return log_test("A6", False, "Could not find required dates")
        
        # Test 1: Friday 10:30 ringan -> 400 (closed slot)
        resp1 = requests.post(
            f"{BASE_URL}/bookings",
            json={
                "customer_name": "Tester Jadwal",
                "whatsapp": "081200001111",
                "plate_number": "DD 1 TJ",
                "complaint": "tes jadwal",
                "service_id": RINGAN_ID,
                "booking_date": friday_date,
                "start_time": "10:30"
            },
            timeout=10
        )
        
        if resp1.status_code != 400:
            return log_test("A6", False, f"Friday 10:30 ringan should return 400, got {resp1.status_code}")
        
        # Test 2: Friday 14:00 ringan -> 200, end_time 15:00
        resp2 = requests.post(
            f"{BASE_URL}/bookings",
            json={
                "customer_name": "Tester Jadwal",
                "whatsapp": "081200001111",
                "plate_number": "DD 1 TJ",
                "complaint": "tes jadwal",
                "service_id": RINGAN_ID,
                "booking_date": friday_date,
                "start_time": "14:00"
            },
            timeout=10
        )
        
        if resp2.status_code != 200:
            return log_test("A6", False, f"Friday 14:00 ringan should return 200, got {resp2.status_code}: {resp2.text}")
        
        data2 = resp2.json()
        booking2 = data2.get("booking", {})
        if booking2.get("end_time") != "15:00":
            return log_test("A6", False, f"Friday 14:00 ringan end_time is '{booking2.get('end_time')}', expected '15:00'")
        
        created_bookings.append(booking2.get("id"))
        
        # Test 3: Non-Friday 08:00 -> 400 (before opening)
        resp3 = requests.post(
            f"{BASE_URL}/bookings",
            json={
                "customer_name": "Tester Jadwal",
                "whatsapp": "081200001111",
                "plate_number": "DD 1 TJ",
                "complaint": "tes jadwal",
                "service_id": RINGAN_ID,
                "booking_date": non_friday,
                "start_time": "08:00"
            },
            timeout=10
        )
        
        if resp3.status_code != 400:
            return log_test("A6", False, f"Non-Friday 08:00 should return 400, got {resp3.status_code}")
        
        # Test 4: Non-Friday 08:30 -> 200, end_time 09:30
        resp4 = requests.post(
            f"{BASE_URL}/bookings",
            json={
                "customer_name": "Tester Jadwal",
                "whatsapp": "081200001111",
                "plate_number": "DD 1 TJ",
                "complaint": "tes jadwal",
                "service_id": RINGAN_ID,
                "booking_date": non_friday,
                "start_time": "08:30"
            },
            timeout=10
        )
        
        if resp4.status_code != 200:
            return log_test("A6", False, f"Non-Friday 08:30 should return 200, got {resp4.status_code}: {resp4.text}")
        
        data4 = resp4.json()
        booking4 = data4.get("booking", {})
        if booking4.get("end_time") != "09:30":
            return log_test("A6", False, f"Non-Friday 08:30 end_time is '{booking4.get('end_time')}', expected '09:30'")
        
        created_bookings.append(booking4.get("id"))
        
        return log_test("A6", True, "Booking validations: Friday 10:30→400, Friday 14:00→200(15:00), Non-Fri 08:00→400, Non-Fri 08:30→200(09:30)")
    
    except Exception as e:
        return log_test("A6", False, f"Exception: {str(e)}")


def test_a7_business_hours_update():
    """A7: PUT /api/admin/business-hours - test valid and invalid updates"""
    try:
        headers = get_auth_headers()
        
        # Test 1: Valid update (restore original)
        resp1 = requests.put(
            f"{BASE_URL}/admin/business-hours",
            headers=headers,
            json={
                "opening_time": "08:30",
                "closing_time": "16:30",
                "breaks": [
                    {
                        "weekday": 4,
                        "start": "11:00",
                        "end": "14:00",
                        "label": "Istirahat Sholat Jumat"
                    }
                ]
            },
            timeout=10
        )
        
        if resp1.status_code != 200:
            return log_test("A7", False, f"Valid update should return 200, got {resp1.status_code}: {resp1.text}")
        
        data1 = resp1.json()
        if data1.get("opening_time") != "08:30" or data1.get("closing_time") != "16:30":
            return log_test("A7", False, "Valid update did not return correct times")
        
        breaks1 = data1.get("breaks", [])
        if len(breaks1) != 1 or breaks1[0].get("weekday") != 4:
            return log_test("A7", False, "Valid update did not return correct breaks")
        
        # Test 2: Invalid breaks (start >= end)
        resp2 = requests.put(
            f"{BASE_URL}/admin/business-hours",
            headers=headers,
            json={
                "opening_time": "08:30",
                "closing_time": "16:30",
                "breaks": [
                    {
                        "weekday": 4,
                        "start": "15:00",
                        "end": "14:00",
                        "label": "Invalid"
                    }
                ]
            },
            timeout=10
        )
        
        if resp2.status_code != 400:
            return log_test("A7", False, f"Invalid breaks (start>=end) should return 400, got {resp2.status_code}")
        
        # Test 3: Invalid opening/closing (opening >= closing)
        resp3 = requests.put(
            f"{BASE_URL}/admin/business-hours",
            headers=headers,
            json={
                "opening_time": "17:00",
                "closing_time": "16:30",
                "breaks": []
            },
            timeout=10
        )
        
        if resp3.status_code != 400:
            return log_test("A7", False, f"Invalid opening>=closing should return 400, got {resp3.status_code}")
        
        # Restore original state
        requests.put(
            f"{BASE_URL}/admin/business-hours",
            headers=headers,
            json={
                "opening_time": "08:30",
                "closing_time": "16:30",
                "breaks": [
                    {
                        "weekday": 4,
                        "start": "11:00",
                        "end": "14:00",
                        "label": "Istirahat Sholat Jumat"
                    }
                ]
            },
            timeout=10
        )
        
        return log_test("A7", True, "Business hours update: valid→200, invalid breaks→400, invalid times→400")
    
    except Exception as e:
        return log_test("A7", False, f"Exception: {str(e)}")


def test_a8_calendar_day_friday():
    """A8: GET /api/admin/calendar/day Friday -> columns has break between 10:30 and 14:00"""
    try:
        headers = get_auth_headers()
        
        bh_resp = requests.get(f"{BASE_URL}/business-hours", timeout=10)
        bh_data = bh_resp.json()
        min_date = bh_data.get("min_date")
        max_date = bh_data.get("max_date")
        
        friday_date = find_friday_date(min_date, max_date)
        if not friday_date:
            return log_test("A8", False, "No Friday found")
        
        resp = requests.get(
            f"{BASE_URL}/admin/calendar/day",
            headers=headers,
            params={"date": friday_date},
            timeout=10
        )
        
        if resp.status_code != 200:
            return log_test("A8", False, f"GET /api/admin/calendar/day returned {resp.status_code}")
        
        data = resp.json()
        columns = data.get("columns", [])
        hours = data.get("hours", [])
        
        # Check hours
        expected_hours = ["08:30", "09:30", "10:30", "14:00", "15:00", "16:00"]
        if hours != expected_hours:
            return log_test("A8", False, f"hours are {hours}, expected {expected_hours}")
        
        # Check columns contains exactly one break
        break_columns = [c for c in columns if c.get("type") == "break"]
        if len(break_columns) != 1:
            return log_test("A8", False, f"Expected 1 break column, got {len(break_columns)}")
        
        # Check break is positioned between 10:30 and 14:00
        break_col = break_columns[0]
        break_idx = columns.index(break_col)
        
        # Find 10:30 slot index
        slot_1030_idx = None
        slot_1400_idx = None
        for i, c in enumerate(columns):
            if c.get("type") == "slot" and c.get("time") == "10:30":
                slot_1030_idx = i
            if c.get("type") == "slot" and c.get("time") == "14:00":
                slot_1400_idx = i
        
        if slot_1030_idx is None or slot_1400_idx is None:
            return log_test("A8", False, "Could not find 10:30 or 14:00 slot in columns")
        
        if not (slot_1030_idx < break_idx < slot_1400_idx):
            return log_test("A8", False, f"Break column at index {break_idx} not between 10:30 (idx {slot_1030_idx}) and 14:00 (idx {slot_1400_idx})")
        
        # Check each mechanic's cells include a break cell
        mechanics = data.get("mechanics", [])
        for mech in mechanics:
            cells = mech.get("cells", [])
            break_cells = [c for c in cells if c.get("type") == "break"]
            if len(break_cells) == 0:
                return log_test("A8", False, f"Mechanic {mech.get('name')} has no break cell")
        
        return log_test("A8", True, f"Calendar day Friday {friday_date}: 1 break column between 10:30 and 14:00, hours correct, mechanics have break cells")
    
    except Exception as e:
        return log_test("A8", False, f"Exception: {str(e)}")


def test_a9_calendar_week():
    """A9: GET /api/admin/calendar/week -> Friday capacity = active_mechanics*6, Monday = active_mechanics*8, Sunday = 0"""
    try:
        headers = get_auth_headers()
        
        bh_resp = requests.get(f"{BASE_URL}/business-hours", timeout=10)
        bh_data = bh_resp.json()
        min_date = bh_data.get("min_date")
        
        # Find a Monday to start the week
        start_date = datetime.strptime(min_date, "%Y-%m-%d")
        while start_date.weekday() != 0:  # Find Monday
            start_date += timedelta(days=1)
        
        monday_str = start_date.strftime("%Y-%m-%d")
        
        resp = requests.get(
            f"{BASE_URL}/admin/calendar/week",
            headers=headers,
            params={"start": monday_str},
            timeout=10
        )
        
        if resp.status_code != 200:
            return log_test("A9", False, f"GET /api/admin/calendar/week returned {resp.status_code}")
        
        data = resp.json()
        days = data.get("days", [])
        
        if len(days) != 7:
            return log_test("A9", False, f"Expected 7 days, got {len(days)}")
        
        # Get active mechanics count
        mech_resp = requests.get(f"{BASE_URL}/mechanics", timeout=10)
        mechanics = mech_resp.json()
        active_mechanics = len([m for m in mechanics if m.get("status") == "active"])
        
        # Find Monday (weekday 0), Friday (weekday 4), Sunday (weekday 6)
        monday_day = next((d for d in days if d.get("weekday") == 0), None)
        friday_day = next((d for d in days if d.get("weekday") == 4), None)
        sunday_day = next((d for d in days if d.get("weekday") == 6), None)
        
        if not monday_day:
            return log_test("A9", False, "Monday not found in week")
        
        if not friday_day:
            return log_test("A9", False, "Friday not found in week")
        
        if not sunday_day:
            return log_test("A9", False, "Sunday not found in week")
        
        # Check Monday capacity = active_mechanics * 8
        expected_monday_capacity = active_mechanics * 8
        if monday_day.get("capacity") != expected_monday_capacity:
            return log_test("A9", False, f"Monday capacity is {monday_day.get('capacity')}, expected {expected_monday_capacity}")
        
        # Check Friday capacity = active_mechanics * 6
        expected_friday_capacity = active_mechanics * 6
        if friday_day.get("capacity") != expected_friday_capacity:
            return log_test("A9", False, f"Friday capacity is {friday_day.get('capacity')}, expected {expected_friday_capacity}")
        
        # Check Sunday capacity = 0
        if sunday_day.get("capacity") != 0:
            return log_test("A9", False, f"Sunday capacity is {sunday_day.get('capacity')}, expected 0")
        
        return log_test("A9", True, f"Calendar week: Monday capacity={expected_monday_capacity}, Friday capacity={expected_friday_capacity}, Sunday capacity=0")
    
    except Exception as e:
        return log_test("A9", False, f"Exception: {str(e)}")


# ============================================================================
# B) SPAREPART ADMIN CRUD TESTS
# ============================================================================

def test_b10_admin_spareparts_list():
    """B10: GET /api/admin/spareparts (auth) -> 200 list length 268. Without auth -> 401"""
    try:
        # Test without auth
        resp_no_auth = requests.get(f"{BASE_URL}/admin/spareparts", timeout=10)
        if resp_no_auth.status_code != 401:
            return log_test("B10", False, f"GET /api/admin/spareparts without auth should return 401, got {resp_no_auth.status_code}")
        
        # Test with auth
        headers = get_auth_headers()
        resp = requests.get(f"{BASE_URL}/admin/spareparts", headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return log_test("B10", False, f"GET /api/admin/spareparts with auth returned {resp.status_code}")
        
        spareparts = resp.json()
        
        if not isinstance(spareparts, list):
            return log_test("B10", False, f"Response is not a list, got {type(spareparts)}")
        
        if len(spareparts) != 268:
            return log_test("B10", False, f"Expected 268 spareparts, got {len(spareparts)}")
        
        return log_test("B10", True, "Admin spareparts list: 268 items with auth, 401 without auth")
    
    except Exception as e:
        return log_test("B10", False, f"Exception: {str(e)}")


def test_b11_admin_create_sparepart():
    """B11: POST /api/admin/spareparts -> 200, id present, price_label correct, order is max+1"""
    global created_sparepart_id
    
    try:
        headers = get_auth_headers()
        
        # Get current max order
        resp_list = requests.get(f"{BASE_URL}/admin/spareparts", headers=headers, timeout=10)
        spareparts = resp_list.json()
        max_order = max([sp.get("order", 0) for sp in spareparts]) if spareparts else 0
        
        # Create new sparepart
        resp = requests.post(
            f"{BASE_URL}/admin/spareparts",
            headers=headers,
            json={
                "category": "Kampas Rem Tes",
                "group": "Rem, Kemudi & Suspensi",
                "motor": "MotorUnikXYZ",
                "price": 45000
            },
            timeout=10
        )
        
        if resp.status_code != 200:
            return log_test("B11", False, f"POST /api/admin/spareparts returned {resp.status_code}: {resp.text}")
        
        data = resp.json()
        
        # Check id present
        if not data.get("id"):
            return log_test("B11", False, "Response does not contain 'id'")
        
        created_sparepart_id = data.get("id")
        
        # Check price_label
        if data.get("price_label") != "Rp 45.000":
            return log_test("B11", False, f"price_label is '{data.get('price_label')}', expected 'Rp 45.000'")
        
        # Check order
        if data.get("order") != max_order + 1:
            return log_test("B11", False, f"order is {data.get('order')}, expected {max_order + 1}")
        
        return log_test("B11", True, f"Created sparepart id={created_sparepart_id}, price_label='Rp 45.000', order={max_order + 1}")
    
    except Exception as e:
        return log_test("B11", False, f"Exception: {str(e)}")


def test_b12_public_search_sparepart():
    """B12: GET /api/spareparts?q=motorunikxyz (public) -> total_items 1 with that item"""
    try:
        resp = requests.get(
            f"{BASE_URL}/spareparts",
            params={"q": "motorunikxyz"},
            timeout=10
        )
        
        if resp.status_code != 200:
            return log_test("B12", False, f"GET /api/spareparts returned {resp.status_code}")
        
        data = resp.json()
        
        if data.get("total_items") != 1:
            return log_test("B12", False, f"total_items is {data.get('total_items')}, expected 1")
        
        # Check the item is present
        groups = data.get("groups", [])
        found = False
        for group in groups:
            for category in group.get("categories", []):
                for item in category.get("items", []):
                    if "motorunikxyz" in item.get("motor", "").lower():
                        found = True
                        break
        
        if not found:
            return log_test("B12", False, "MotorUnikXYZ item not found in search results")
        
        return log_test("B12", True, "Public search 'motorunikxyz': total_items=1, item found")
    
    except Exception as e:
        return log_test("B12", False, f"Exception: {str(e)}")


def test_b13_admin_update_sparepart():
    """B13: PATCH /api/admin/spareparts/{id} - test various updates"""
    try:
        headers = get_auth_headers()
        
        if not created_sparepart_id:
            return log_test("B13", False, "No sparepart ID to update")
        
        # Test 1: Update price
        resp1 = requests.patch(
            f"{BASE_URL}/admin/spareparts/{created_sparepart_id}",
            headers=headers,
            json={"price": 50000},
            timeout=10
        )
        
        if resp1.status_code != 200:
            return log_test("B13", False, f"PATCH price returned {resp1.status_code}: {resp1.text}")
        
        data1 = resp1.json()
        if data1.get("price_label") != "Rp 50.000":
            return log_test("B13", False, f"After price update, price_label is '{data1.get('price_label')}', expected 'Rp 50.000'")
        
        # Test 2: Update description and variant
        resp2 = requests.patch(
            f"{BASE_URL}/admin/spareparts/{created_sparepart_id}",
            headers=headers,
            json={"description": "Tes desc", "variant": "V1"},
            timeout=10
        )
        
        if resp2.status_code != 200:
            return log_test("B13", False, f"PATCH description/variant returned {resp2.status_code}")
        
        data2 = resp2.json()
        if data2.get("description") != "Tes desc" or data2.get("variant") != "V1":
            return log_test("B13", False, "description or variant not set correctly")
        
        # Test 3: Remove description (empty string)
        resp3 = requests.patch(
            f"{BASE_URL}/admin/spareparts/{created_sparepart_id}",
            headers=headers,
            json={"description": ""},
            timeout=10
        )
        
        if resp3.status_code != 200:
            return log_test("B13", False, f"PATCH empty description returned {resp3.status_code}")
        
        data3 = resp3.json()
        if "description" in data3:
            return log_test("B13", False, "description should be removed, but still present")
        
        # Test 4: Set custom price_label
        resp4 = requests.patch(
            f"{BASE_URL}/admin/spareparts/{created_sparepart_id}",
            headers=headers,
            json={"price_label": "Rp 50.000 – Rp 70.000"},
            timeout=10
        )
        
        if resp4.status_code != 200:
            return log_test("B13", False, f"PATCH custom price_label returned {resp4.status_code}")
        
        data4 = resp4.json()
        if data4.get("price_label") != "Rp 50.000 – Rp 70.000":
            return log_test("B13", False, f"Custom price_label is '{data4.get('price_label')}', expected 'Rp 50.000 – Rp 70.000'")
        
        # Test 5: Update price again (should regenerate label)
        resp5 = requests.patch(
            f"{BASE_URL}/admin/spareparts/{created_sparepart_id}",
            headers=headers,
            json={"price": 60000},
            timeout=10
        )
        
        if resp5.status_code != 200:
            return log_test("B13", False, f"PATCH price (regenerate label) returned {resp5.status_code}")
        
        data5 = resp5.json()
        if data5.get("price_label") != "Rp 60.000":
            return log_test("B13", False, f"After price update, price_label is '{data5.get('price_label')}', expected 'Rp 60.000' (regenerated)")
        
        # Test 6: Empty PATCH -> 400
        resp6 = requests.patch(
            f"{BASE_URL}/admin/spareparts/{created_sparepart_id}",
            headers=headers,
            json={},
            timeout=10
        )
        
        if resp6.status_code != 400:
            return log_test("B13", False, f"Empty PATCH should return 400, got {resp6.status_code}")
        
        # Test 7: Non-existent ID -> 404
        resp7 = requests.patch(
            f"{BASE_URL}/admin/spareparts/nonexistent-id-12345",
            headers=headers,
            json={"price": 100000},
            timeout=10
        )
        
        if resp7.status_code != 404:
            return log_test("B13", False, f"PATCH non-existent ID should return 404, got {resp7.status_code}")
        
        return log_test("B13", True, "PATCH sparepart: price→Rp 50.000, desc/variant set, desc removed, custom label kept, price regenerates label, empty→400, non-existent→404")
    
    except Exception as e:
        return log_test("B13", False, f"Exception: {str(e)}")


def test_b14_admin_create_sparepart_validation():
    """B14: POST with missing motor -> 422"""
    try:
        headers = get_auth_headers()
        
        resp = requests.post(
            f"{BASE_URL}/admin/spareparts",
            headers=headers,
            json={
                "category": "Test Category",
                "group": "Test Group",
                # motor is missing
                "price": 10000
            },
            timeout=10
        )
        
        if resp.status_code != 422:
            return log_test("B14", False, f"POST without motor should return 422, got {resp.status_code}")
        
        return log_test("B14", True, "POST sparepart without motor: 422")
    
    except Exception as e:
        return log_test("B14", False, f"Exception: {str(e)}")


def test_b15_admin_delete_sparepart():
    """B15: DELETE /api/admin/spareparts/{id} -> {ok:true}; again -> 404; search -> 0; total back to 268"""
    try:
        headers = get_auth_headers()
        
        if not created_sparepart_id:
            return log_test("B15", False, "No sparepart ID to delete")
        
        # Delete
        resp1 = requests.delete(
            f"{BASE_URL}/admin/spareparts/{created_sparepart_id}",
            headers=headers,
            timeout=10
        )
        
        if resp1.status_code != 200:
            return log_test("B15", False, f"DELETE returned {resp1.status_code}: {resp1.text}")
        
        data1 = resp1.json()
        if data1.get("ok") != True:
            return log_test("B15", False, f"DELETE response is {data1}, expected {{'ok': True}}")
        
        # Delete again -> 404
        resp2 = requests.delete(
            f"{BASE_URL}/admin/spareparts/{created_sparepart_id}",
            headers=headers,
            timeout=10
        )
        
        if resp2.status_code != 404:
            return log_test("B15", False, f"DELETE again should return 404, got {resp2.status_code}")
        
        # Search -> 0
        resp3 = requests.get(
            f"{BASE_URL}/spareparts",
            params={"q": "motorunikxyz"},
            timeout=10
        )
        
        if resp3.status_code != 200:
            return log_test("B15", False, f"Search after delete returned {resp3.status_code}")
        
        data3 = resp3.json()
        if data3.get("total_items") != 0:
            return log_test("B15", False, f"Search after delete: total_items is {data3.get('total_items')}, expected 0")
        
        # Check total back to 268
        resp4 = requests.get(f"{BASE_URL}/admin/spareparts", headers=headers, timeout=10)
        spareparts = resp4.json()
        
        if len(spareparts) != 268:
            return log_test("B15", False, f"Total spareparts is {len(spareparts)}, expected 268")
        
        return log_test("B15", True, "DELETE sparepart: ok=true, again→404, search→0, total back to 268")
    
    except Exception as e:
        return log_test("B15", False, f"Exception: {str(e)}")


# ============================================================================
# CLEANUP
# ============================================================================

def cleanup_test_bookings():
    """Cancel all test bookings created during tests"""
    if not created_bookings:
        return
    
    headers = get_auth_headers()
    for booking_id in created_bookings:
        try:
            requests.patch(
                f"{BASE_URL}/admin/bookings/{booking_id}",
                headers=headers,
                json={"status": "Dibatalkan"},
                timeout=10
            )
            print(f"✓ Cancelled booking {booking_id}")
        except Exception as e:
            print(f"✗ Failed to cancel booking {booking_id}: {str(e)}")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print("=" * 80)
    print("ALDI MOTOR Backend Testing - New Features")
    print("=" * 80)
    print()
    
    # Login
    if not login_admin():
        print("\n❌ CRITICAL: Admin login failed. Cannot proceed with tests.")
        return
    
    print()
    print("=" * 80)
    print("A) SCHEDULE TESTS")
    print("=" * 80)
    print()
    
    # A) Schedule tests
    test_a1_business_hours()
    test_a2_get_service_ids()
    test_a3_availability_friday_ringan()
    test_a4_availability_friday_berat()
    test_a5_availability_non_friday()
    test_a6_booking_validations()
    test_a7_business_hours_update()
    test_a8_calendar_day_friday()
    test_a9_calendar_week()
    
    print()
    print("=" * 80)
    print("B) SPAREPART ADMIN CRUD TESTS")
    print("=" * 80)
    print()
    
    # B) Sparepart admin CRUD tests
    test_b10_admin_spareparts_list()
    test_b11_admin_create_sparepart()
    test_b12_public_search_sparepart()
    test_b13_admin_update_sparepart()
    test_b14_admin_create_sparepart_validation()
    test_b15_admin_delete_sparepart()
    
    print()
    print("=" * 80)
    print("CLEANUP")
    print("=" * 80)
    print()
    
    # Cleanup
    cleanup_test_bookings()
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    # Summary
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["passed"])
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print()
    
    if failed_tests > 0:
        print("FAILED TESTS:")
        for r in test_results:
            if not r["passed"]:
                print(f"  ❌ Step {r['step']}: {r['details']}")
    else:
        print("✅ ALL TESTS PASSED!")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
