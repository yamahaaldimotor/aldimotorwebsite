#!/usr/bin/env python3
"""
ALDI MOTOR Backend Test Suite - Admin Service Prices CRUD
Tests the admin CRUD endpoints for service prices
"""
import sys
import requests

# Backend URL from frontend/.env
BACKEND_URL = "https://repo-sync-122.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
ADMIN_USERNAME = "adminaldimotor"
ADMIN_PASSWORD = "aldimotorjaya"

# Test state
token = None
test_motor_uji_id = None
test_motor_baru_id = None
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


def test_step_1_get_admin_service_prices():
    """Step 1: GET /api/admin/service-prices with auth -> 31 items; without auth -> 401"""
    print("\n=== STEP 1: GET /api/admin/service-prices (auth & no auth) ===")
    
    # Test without auth - should return 401
    resp_no_auth = requests.get(f"{API_BASE}/admin/service-prices", timeout=10)
    if resp_no_auth.status_code != 401:
        log_test("1a", "FAIL", f"GET without auth returned {resp_no_auth.status_code}, expected 401")
        return False
    log_test("1a", "PASS", "GET without auth correctly returned 401")
    
    # Test with auth - should return 31 items
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE}/admin/service-prices", headers=headers, timeout=10)
    
    if resp.status_code != 200:
        log_test("1b", "FAIL", f"GET with auth returned {resp.status_code}: {resp.text}")
        return False
    
    items = resp.json()
    if not isinstance(items, list):
        log_test("1b", "FAIL", f"Response is not a list: {type(items)}")
        return False
    
    if len(items) != 31:
        log_test("1b", "FAIL", f"Expected 31 items, got {len(items)}")
        return False
    
    log_test("1b", "PASS", f"GET with auth returned 31 items")
    return True


def test_step_2_post_sport_motor():
    """Step 2: POST new Sport motor with prices"""
    global test_motor_uji_id
    print("\n=== STEP 2: POST /api/admin/service-prices (Sport category) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "category": "Sport",
        "motor": "MotorUjiXYZ",
        "ringan": 90000,
        "berat": 120000,
        "overhaul": 310000
    }
    
    resp = requests.post(f"{API_BASE}/admin/service-prices", headers=headers, json=payload, timeout=10)
    
    if resp.status_code != 200:
        log_test("2", "FAIL", f"POST returned {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    
    # Check required fields
    if "id" not in data:
        log_test("2", "FAIL", "Response missing 'id' field")
        return False
    
    test_motor_uji_id = data["id"]
    
    # Check category_order should be 4 (same as other Sport items)
    if data.get("category_order") != 4:
        log_test("2", "FAIL", f"category_order is {data.get('category_order')}, expected 4")
        return False
    
    # Check order should be 31 (max + 1)
    if data.get("order") != 31:
        log_test("2", "FAIL", f"order is {data.get('order')}, expected 31")
        return False
    
    # Check prices
    if data.get("ringan") != 90000 or data.get("berat") != 120000 or data.get("overhaul") != 310000:
        log_test("2", "FAIL", f"Prices don't match: ringan={data.get('ringan')}, berat={data.get('berat')}, overhaul={data.get('overhaul')}")
        return False
    
    log_test("2", "PASS", f"POST Sport motor successful: id={test_motor_uji_id}, category_order=4, order=31")
    return True


def test_step_3_get_public_search():
    """Step 3: GET /api/service-prices?q=motorujixyz (public) -> verify item appears"""
    print("\n=== STEP 3: GET /api/service-prices?q=motorujixyz (public) ===")
    
    resp = requests.get(f"{API_BASE}/service-prices?q=motorujixyz", timeout=10)
    
    if resp.status_code != 200:
        log_test("3", "FAIL", f"GET returned {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    
    # Check total_motors
    if data.get("total_motors") != 1:
        log_test("3", "FAIL", f"total_motors is {data.get('total_motors')}, expected 1")
        return False
    
    # Check categories
    categories = data.get("categories", [])
    if len(categories) != 1:
        log_test("3", "FAIL", f"Expected 1 category, got {len(categories)}")
        return False
    
    category = categories[0]
    if category.get("category") != "Sport":
        log_test("3", "FAIL", f"Category is {category.get('category')}, expected Sport")
        return False
    
    # Check items
    items = category.get("items", [])
    if len(items) != 1:
        log_test("3", "FAIL", f"Expected 1 item, got {len(items)}")
        return False
    
    item = items[0]
    prices = item.get("prices", {})
    if prices.get("ringan") != 90000 or prices.get("berat") != 120000 or prices.get("overhaul") != 310000:
        log_test("3", "FAIL", f"Prices don't match: {prices}")
        return False
    
    log_test("3", "PASS", "Public search found MotorUjiXYZ in Sport category with correct prices")
    return True


def test_step_4_post_duplicate():
    """Step 4: POST duplicate motor (lowercase) -> 400"""
    print("\n=== STEP 4: POST duplicate motor (lowercase) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "category": "Sport",
        "motor": "motorujixyz",  # lowercase
        "ringan": 90000,
        "berat": 120000,
        "overhaul": 310000
    }
    
    resp = requests.post(f"{API_BASE}/admin/service-prices", headers=headers, json=payload, timeout=10)
    
    if resp.status_code != 400:
        log_test("4", "FAIL", f"POST duplicate returned {resp.status_code}, expected 400: {resp.text}")
        return False
    
    log_test("4", "PASS", "POST duplicate motor correctly returned 400")
    return True


def test_step_5_post_new_category():
    """Step 5: POST new category without prices"""
    global test_motor_baru_id
    print("\n=== STEP 5: POST /api/admin/service-prices (new category, no prices) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "category": "Kategori Baru",
        "motor": "MotorBaruQQ"
    }
    
    resp = requests.post(f"{API_BASE}/admin/service-prices", headers=headers, json=payload, timeout=10)
    
    if resp.status_code != 200:
        log_test("5a", "FAIL", f"POST returned {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    test_motor_baru_id = data.get("id")
    
    # Check category_order should be 8 (new category)
    if data.get("category_order") != 8:
        log_test("5a", "FAIL", f"category_order is {data.get('category_order')}, expected 8")
        return False
    
    # Check prices are null
    if data.get("ringan") is not None or data.get("berat") is not None or data.get("overhaul") is not None:
        log_test("5a", "FAIL", f"Prices should be null: ringan={data.get('ringan')}, berat={data.get('berat')}, overhaul={data.get('overhaul')}")
        return False
    
    log_test("5a", "PASS", f"POST new category successful: id={test_motor_baru_id}, category_order=8, prices=null")
    
    # Verify in public endpoint
    resp_public = requests.get(f"{API_BASE}/service-prices?q=motorbaruqq", timeout=10)
    if resp_public.status_code != 200:
        log_test("5b", "FAIL", f"Public GET returned {resp_public.status_code}")
        return False
    
    data_public = resp_public.json()
    if data_public.get("total_motors") != 1:
        log_test("5b", "FAIL", f"Public search total_motors is {data_public.get('total_motors')}, expected 1")
        return False
    
    # Check prices are null in public response
    categories = data_public.get("categories", [])
    if len(categories) != 1:
        log_test("5b", "FAIL", f"Expected 1 category in public response, got {len(categories)}")
        return False
    
    items = categories[0].get("items", [])
    if len(items) != 1:
        log_test("5b", "FAIL", f"Expected 1 item in public response, got {len(items)}")
        return False
    
    prices = items[0].get("prices", {})
    if prices.get("ringan") is not None or prices.get("berat") is not None or prices.get("overhaul") is not None:
        log_test("5b", "FAIL", f"Public prices should be null: {prices}")
        return False
    
    log_test("5b", "PASS", "Public search shows MotorBaruQQ with null prices")
    return True


def test_step_6_patch_operations():
    """Step 6: PATCH operations - update, negative value, empty body, non-existent id"""
    print("\n=== STEP 6: PATCH /api/admin/service-prices ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 6a: PATCH update ringan
    resp = requests.patch(
        f"{API_BASE}/admin/service-prices/{test_motor_uji_id}",
        headers=headers,
        json={"ringan": 95000},
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("6a", "FAIL", f"PATCH update returned {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    if data.get("ringan") != 95000:
        log_test("6a", "FAIL", f"ringan is {data.get('ringan')}, expected 95000")
        return False
    
    if data.get("berat") != 120000:
        log_test("6a", "FAIL", f"berat changed to {data.get('berat')}, should still be 120000")
        return False
    
    log_test("6a", "PASS", "PATCH update ringan successful, berat unchanged")
    
    # 6b: PATCH negative value -> 400
    resp = requests.patch(
        f"{API_BASE}/admin/service-prices/{test_motor_uji_id}",
        headers=headers,
        json={"ringan": -1},
        timeout=10
    )
    
    if resp.status_code != 400:
        log_test("6b", "FAIL", f"PATCH negative value returned {resp.status_code}, expected 400")
        return False
    
    log_test("6b", "PASS", "PATCH negative value correctly returned 400")
    
    # 6c: PATCH empty body -> 400
    resp = requests.patch(
        f"{API_BASE}/admin/service-prices/{test_motor_uji_id}",
        headers=headers,
        json={},
        timeout=10
    )
    
    if resp.status_code != 400:
        log_test("6c", "FAIL", f"PATCH empty body returned {resp.status_code}, expected 400")
        return False
    
    log_test("6c", "PASS", "PATCH empty body correctly returned 400")
    
    # 6d: PATCH non-existent id -> 404
    resp = requests.patch(
        f"{API_BASE}/admin/service-prices/random-id-12345",
        headers=headers,
        json={"ringan": 1},
        timeout=10
    )
    
    if resp.status_code != 404:
        log_test("6d", "FAIL", f"PATCH non-existent id returned {resp.status_code}, expected 404")
        return False
    
    log_test("6d", "PASS", "PATCH non-existent id correctly returned 404")
    
    return True


def test_step_7_delete_operations():
    """Step 7: DELETE both test items, verify deletion"""
    print("\n=== STEP 7: DELETE /api/admin/service-prices ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 7a: DELETE MotorUjiXYZ
    resp = requests.delete(
        f"{API_BASE}/admin/service-prices/{test_motor_uji_id}",
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("7a", "FAIL", f"DELETE MotorUjiXYZ returned {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    if data.get("ok") != True:
        log_test("7a", "FAIL", f"DELETE response should be {{ok:true}}, got {data}")
        return False
    
    log_test("7a", "PASS", "DELETE MotorUjiXYZ successful")
    
    # 7b: DELETE again -> 404
    resp = requests.delete(
        f"{API_BASE}/admin/service-prices/{test_motor_uji_id}",
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 404:
        log_test("7b", "FAIL", f"DELETE again returned {resp.status_code}, expected 404")
        return False
    
    log_test("7b", "PASS", "DELETE again correctly returned 404")
    
    # 7c: DELETE MotorBaruQQ
    resp = requests.delete(
        f"{API_BASE}/admin/service-prices/{test_motor_baru_id}",
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("7c", "FAIL", f"DELETE MotorBaruQQ returned {resp.status_code}: {resp.text}")
        return False
    
    log_test("7c", "PASS", "DELETE MotorBaruQQ successful")
    
    # 7d: Verify total_motors back to 31 and all_categories back to 8
    resp = requests.get(f"{API_BASE}/service-prices", timeout=10)
    if resp.status_code != 200:
        log_test("7d", "FAIL", f"GET service-prices returned {resp.status_code}")
        return False
    
    data = resp.json()
    if data.get("total_motors") != 31:
        log_test("7d", "FAIL", f"total_motors is {data.get('total_motors')}, expected 31")
        return False
    
    all_categories = data.get("all_categories", [])
    if len(all_categories) != 8:
        log_test("7d", "FAIL", f"all_categories length is {len(all_categories)}, expected 8")
        return False
    
    log_test("7d", "PASS", "Verified total_motors=31 and all_categories=8 after deletion")
    
    return True


def main():
    """Run all tests"""
    print("=" * 80)
    print("ALDI MOTOR - Admin Service Prices CRUD Test Suite")
    print("=" * 80)
    
    # Login
    login()
    
    # Run tests in sequence
    tests = [
        test_step_1_get_admin_service_prices,
        test_step_2_post_sport_motor,
        test_step_3_get_public_search,
        test_step_4_post_duplicate,
        test_step_5_post_new_category,
        test_step_6_patch_operations,
        test_step_7_delete_operations,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} raised exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    total = passed + failed
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
