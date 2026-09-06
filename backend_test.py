#!/usr/bin/env python3
"""
ALDI MOTOR Backend Test Suite - Mechanic Photo Upload Feature
Tests the new mechanic photo upload/delete functionality
"""
import os
import sys
import requests
from io import BytesIO
from PIL import Image
import time

# Backend URL from frontend/.env
BACKEND_URL = "https://bf4f7221-ce61-49f2-a3c1-cc17b0180a7b.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
ADMIN_USERNAME = "adminaldimotor"
ADMIN_PASSWORD = "aldimotorjaya"

# Test state
token = None
test_mechanic_id = None
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


def test_get_mechanics():
    """Test 1: GET /api/mechanics - verify 5 mechanics with real names and photo fields"""
    print("\n=== TEST 1: GET /api/mechanics ===")
    resp = requests.get(f"{API_BASE}/mechanics", timeout=10)
    
    if resp.status_code != 200:
        log_test("1", "FAIL", f"GET /api/mechanics returned {resp.status_code}")
        return False
    
    mechanics = resp.json()
    
    # Check we have 5 mechanics
    if len(mechanics) < 5:
        log_test("1", "FAIL", f"Expected at least 5 mechanics, got {len(mechanics)}")
        return False
    
    # Expected real names
    expected_names = ["Andi Muh Wahidin", "Ahmad Balla", "Kasim", "Ansar", "Muh Risal"]
    found_names = [m.get("name") for m in mechanics]
    
    # Check all expected names are present
    missing_names = [name for name in expected_names if name not in found_names]
    if missing_names:
        log_test("1", "FAIL", f"Missing mechanics: {missing_names}. Found: {found_names}")
        return False
    
    # Check each mechanic has a photo field
    mechanics_without_photo = [m.get("name") for m in mechanics if "photo" not in m or not m["photo"]]
    if mechanics_without_photo:
        log_test("1", "FAIL", f"Mechanics without photo field: {mechanics_without_photo}")
        return False
    
    # Verify photo field format (should be like "/mechanics/<slug>.jpg")
    for m in mechanics:
        photo = m.get("photo", "")
        if not photo.startswith("/mechanics/") and not photo.startswith("/api/uploads/mechanics/"):
            log_test("1", "FAIL", f"Mechanic {m.get('name')} has invalid photo format: {photo}")
            return False
    
    log_test("1", "PASS", f"Found {len(mechanics)} mechanics with real names and photo fields")
    return True


def test_create_mechanic():
    """Test 2: POST /api/admin/mechanics - create test mechanic"""
    global test_mechanic_id
    print("\n=== TEST 2: POST /api/admin/mechanics ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(
        f"{API_BASE}/admin/mechanics",
        json={"name": "Test Mekanik Foto"},
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("2", "FAIL", f"POST /api/admin/mechanics returned {resp.status_code}: {resp.text}")
        return False
    
    mechanic = resp.json()
    test_mechanic_id = mechanic.get("id")
    
    if not test_mechanic_id:
        log_test("2", "FAIL", "No id in response")
        return False
    
    if mechanic.get("name") != "Test Mekanik Foto":
        log_test("2", "FAIL", f"Name mismatch: expected 'Test Mekanik Foto', got '{mechanic.get('name')}'")
        return False
    
    log_test("2", "PASS", f"Created test mechanic with id: {test_mechanic_id}")
    return True


def create_test_image(width, height, format="PNG"):
    """Create a test image using PIL"""
    img = Image.new("RGB", (width, height), color=(73, 109, 137))
    # Add some pattern to make it recognizable
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([width//4, height//4, 3*width//4, 3*height//4], fill=(255, 200, 100))
    draw.text((width//2 - 20, height//2), "TEST", fill=(0, 0, 0))
    
    buf = BytesIO()
    img.save(buf, format=format, quality=95)
    buf.seek(0)
    return buf


def test_upload_photo_png():
    """Test 3a: POST /api/admin/mechanics/{id}/photo with PNG"""
    print("\n=== TEST 3a: Upload PNG photo ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create 800x600 PNG
    img_buf = create_test_image(800, 600, "PNG")
    
    files = {"file": ("test.png", img_buf, "image/png")}
    resp = requests.post(
        f"{API_BASE}/admin/mechanics/{test_mechanic_id}/photo",
        files=files,
        headers=headers,
        timeout=15
    )
    
    if resp.status_code != 200:
        log_test("3a", "FAIL", f"Upload PNG returned {resp.status_code}: {resp.text}")
        return False
    
    mechanic = resp.json()
    photo_url = mechanic.get("photo")
    
    if not photo_url:
        log_test("3a", "FAIL", "No photo field in response")
        return False
    
    if not photo_url.startswith(f"/api/uploads/mechanics/{test_mechanic_id}.jpg"):
        log_test("3a", "FAIL", f"Photo URL format incorrect: {photo_url}")
        return False
    
    if "?v=" not in photo_url:
        log_test("3a", "FAIL", f"Photo URL missing version parameter: {photo_url}")
        return False
    
    log_test("3a", "PASS", f"PNG uploaded successfully, photo URL: {photo_url}")
    return photo_url


def test_upload_photo_jpeg():
    """Test 3b: POST /api/admin/mechanics/{id}/photo with JPEG"""
    print("\n=== TEST 3b: Upload JPEG photo ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create 800x600 JPEG
    img_buf = create_test_image(800, 600, "JPEG")
    
    files = {"file": ("test.jpg", img_buf, "image/jpeg")}
    resp = requests.post(
        f"{API_BASE}/admin/mechanics/{test_mechanic_id}/photo",
        files=files,
        headers=headers,
        timeout=15
    )
    
    if resp.status_code != 200:
        log_test("3b", "FAIL", f"Upload JPEG returned {resp.status_code}: {resp.text}")
        return False
    
    mechanic = resp.json()
    photo_url = mechanic.get("photo")
    
    if not photo_url:
        log_test("3b", "FAIL", "No photo field in response")
        return False
    
    log_test("3b", "PASS", f"JPEG uploaded successfully, photo URL: {photo_url}")
    return photo_url


def test_get_uploaded_photo(photo_url):
    """Test 4: GET uploaded photo and verify it's 480x480 JPEG"""
    print("\n=== TEST 4: GET uploaded photo ===")
    
    # Extract path without query params
    photo_path = photo_url.split("?")[0]
    full_url = f"{BACKEND_URL}{photo_path}"
    
    resp = requests.get(full_url, timeout=10)
    
    if resp.status_code != 200:
        log_test("4", "FAIL", f"GET {photo_path} returned {resp.status_code}")
        return False
    
    content_type = resp.headers.get("content-type", "")
    if "image/jpeg" not in content_type:
        log_test("4", "FAIL", f"Content-Type is {content_type}, expected image/jpeg")
        return False
    
    # Verify image dimensions with PIL
    try:
        img = Image.open(BytesIO(resp.content))
        width, height = img.size
        
        if width != 480 or height != 480:
            log_test("4", "FAIL", f"Image dimensions are {width}x{height}, expected 480x480")
            return False
        
        log_test("4", "PASS", f"Photo retrieved successfully: 480x480 JPEG, {len(resp.content)} bytes")
        return True
    except Exception as e:
        log_test("4", "FAIL", f"Failed to verify image: {e}")
        return False


def test_upload_txt_file():
    """Test 5a: Upload .txt file - should return 400"""
    print("\n=== TEST 5a: Upload .txt file (negative test) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    txt_content = BytesIO(b"This is a text file, not an image")
    files = {"file": ("test.txt", txt_content, "text/plain")}
    
    resp = requests.post(
        f"{API_BASE}/admin/mechanics/{test_mechanic_id}/photo",
        files=files,
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 400:
        log_test("5a", "FAIL", f"Expected 400 for .txt file, got {resp.status_code}")
        return False
    
    log_test("5a", "PASS", "Correctly rejected .txt file with 400")
    return True


def test_upload_large_file():
    """Test 5b: Upload file > 5MB - should return 400"""
    print("\n=== TEST 5b: Upload file > 5MB (negative test) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a large PNG (3000x3000 with random noise should be > 5MB)
    img = Image.new("RGB", (3000, 3000))
    import random
    pixels = img.load()
    for i in range(3000):
        for j in range(3000):
            pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    size_mb = len(buf.getvalue()) / (1024 * 1024)
    
    if size_mb <= 5:
        log_test("5b", "FAIL", f"Test image is only {size_mb:.2f}MB, need > 5MB")
        return False
    
    files = {"file": ("large.png", buf, "image/png")}
    
    resp = requests.post(
        f"{API_BASE}/admin/mechanics/{test_mechanic_id}/photo",
        files=files,
        headers=headers,
        timeout=15
    )
    
    if resp.status_code != 400:
        log_test("5b", "FAIL", f"Expected 400 for {size_mb:.2f}MB file, got {resp.status_code}")
        return False
    
    log_test("5b", "PASS", f"Correctly rejected {size_mb:.2f}MB file with 400")
    return True


def test_upload_without_auth():
    """Test 5c: Upload without authentication - should return 401"""
    print("\n=== TEST 5c: Upload without auth (negative test) ===")
    
    img_buf = create_test_image(100, 100, "JPEG")
    files = {"file": ("test.jpg", img_buf, "image/jpeg")}
    
    resp = requests.post(
        f"{API_BASE}/admin/mechanics/{test_mechanic_id}/photo",
        files=files,
        timeout=10
    )
    
    if resp.status_code != 401:
        log_test("5c", "FAIL", f"Expected 401 without auth, got {resp.status_code}")
        return False
    
    log_test("5c", "PASS", "Correctly rejected upload without auth with 401")
    return True


def test_upload_nonexistent_mechanic():
    """Test 5d: Upload to non-existent mechanic - should return 404"""
    print("\n=== TEST 5d: Upload to non-existent mechanic (negative test) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    img_buf = create_test_image(100, 100, "JPEG")
    files = {"file": ("test.jpg", img_buf, "image/jpeg")}
    
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = requests.post(
        f"{API_BASE}/admin/mechanics/{fake_id}/photo",
        files=files,
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 404:
        log_test("5d", "FAIL", f"Expected 404 for non-existent mechanic, got {resp.status_code}")
        return False
    
    log_test("5d", "PASS", "Correctly returned 404 for non-existent mechanic")
    return True


def test_delete_photo():
    """Test 6: DELETE /api/admin/mechanics/{id}/photo"""
    print("\n=== TEST 6: DELETE photo ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.delete(
        f"{API_BASE}/admin/mechanics/{test_mechanic_id}/photo",
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("6", "FAIL", f"DELETE photo returned {resp.status_code}: {resp.text}")
        return False
    
    mechanic = resp.json()
    
    if "photo" in mechanic and mechanic["photo"]:
        log_test("6", "FAIL", f"Photo field still present after delete: {mechanic.get('photo')}")
        return False
    
    log_test("6", "PASS", "Photo deleted successfully, no photo field in response")
    return True


def test_photo_file_deleted():
    """Test 6b: Verify photo file returns 404 after deletion"""
    print("\n=== TEST 6b: Verify photo file deleted ===")
    
    photo_path = f"/api/uploads/mechanics/{test_mechanic_id}.jpg"
    full_url = f"{BACKEND_URL}{photo_path}"
    
    resp = requests.get(full_url, timeout=10)
    
    if resp.status_code != 404:
        log_test("6b", "FAIL", f"Expected 404 for deleted photo, got {resp.status_code}")
        return False
    
    log_test("6b", "PASS", "Photo file correctly returns 404 after deletion")
    return True


def test_reupload_and_delete_mechanic():
    """Test 7: Re-upload photo, then delete mechanic, verify file deleted"""
    print("\n=== TEST 7: Re-upload and delete mechanic ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Re-upload photo
    img_buf = create_test_image(500, 500, "JPEG")
    files = {"file": ("test.jpg", img_buf, "image/jpeg")}
    
    resp = requests.post(
        f"{API_BASE}/admin/mechanics/{test_mechanic_id}/photo",
        files=files,
        headers=headers,
        timeout=15
    )
    
    if resp.status_code != 200:
        log_test("7", "FAIL", f"Re-upload failed: {resp.status_code}")
        return False
    
    # Delete mechanic
    resp = requests.delete(
        f"{API_BASE}/admin/mechanics/{test_mechanic_id}",
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("7", "FAIL", f"Delete mechanic returned {resp.status_code}: {resp.text}")
        return False
    
    # Verify photo file is deleted
    photo_path = f"/api/uploads/mechanics/{test_mechanic_id}.jpg"
    full_url = f"{BACKEND_URL}{photo_path}"
    
    resp = requests.get(full_url, timeout=10)
    
    if resp.status_code != 404:
        log_test("7", "FAIL", f"Photo file still accessible after mechanic deletion: {resp.status_code}")
        return False
    
    log_test("7", "PASS", "Mechanic deleted, photo file correctly removed (404)")
    return True


def test_regression_services():
    """Test 8a: Regression - GET /api/services (no price)"""
    print("\n=== TEST 8a: Regression - GET /api/services ===")
    
    resp = requests.get(f"{API_BASE}/services", timeout=10)
    
    if resp.status_code != 200:
        log_test("8a", "FAIL", f"GET /api/services returned {resp.status_code}")
        return False
    
    services = resp.json()
    
    # Check no service has price field
    services_with_price = [s.get("name") for s in services if "price" in s]
    if services_with_price:
        log_test("8a", "FAIL", f"Services with price field: {services_with_price}")
        return False
    
    log_test("8a", "PASS", f"GET /api/services returned {len(services)} services without price field")
    return True


def test_regression_stats():
    """Test 8b: Regression - GET /api/admin/stats"""
    print("\n=== TEST 8b: Regression - GET /api/admin/stats ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{API_BASE}/admin/stats", headers=headers, timeout=10)
    
    if resp.status_code != 200:
        log_test("8b", "FAIL", f"GET /api/admin/stats returned {resp.status_code}")
        return False
    
    stats = resp.json()
    
    # Just verify it returns data
    if "total" not in stats:
        log_test("8b", "FAIL", "Stats response missing 'total' field")
        return False
    
    log_test("8b", "PASS", f"GET /api/admin/stats returned successfully")
    return True


def test_regression_monthly_report():
    """Test 8c: Regression - GET /api/admin/reports/monthly"""
    print("\n=== TEST 8c: Regression - GET /api/admin/reports/monthly ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(
        f"{API_BASE}/admin/reports/monthly",
        params={"year": 2026, "month": 9},
        headers=headers,
        timeout=10
    )
    
    if resp.status_code != 200:
        log_test("8c", "FAIL", f"GET /api/admin/reports/monthly returned {resp.status_code}")
        return False
    
    report = resp.json()
    
    # Verify has active_total and completed_total, no revenue fields
    if "active_total" not in report:
        log_test("8c", "FAIL", "Report missing 'active_total' field")
        return False
    
    if "completed_total" not in report:
        log_test("8c", "FAIL", "Report missing 'completed_total' field")
        return False
    
    if "revenue_total" in report or "revenue_completed" in report:
        log_test("8c", "FAIL", "Report contains revenue fields (should be removed)")
        return False
    
    log_test("8c", "PASS", "Monthly report has active_total/completed_total, no revenue fields")
    return True


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = sum(1 for r in test_results if r["status"] == "FAIL")
    total = len(test_results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
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
    print("ALDI MOTOR - Mechanic Photo Upload Feature Test")
    print("="*60)
    
    try:
        # Login
        login()
        
        # Test 1: GET mechanics
        test_get_mechanics()
        
        # Test 2: Create test mechanic
        if not test_create_mechanic():
            print("\n❌ Cannot continue without test mechanic")
            return False
        
        # Test 3: Upload photos (PNG and JPEG)
        photo_url = test_upload_photo_png()
        if photo_url:
            # Test 4: Verify uploaded photo
            test_get_uploaded_photo(photo_url)
        
        test_upload_photo_jpeg()
        
        # Test 5: Negative tests
        test_upload_txt_file()
        test_upload_large_file()
        test_upload_without_auth()
        test_upload_nonexistent_mechanic()
        
        # Test 6: Delete photo
        test_delete_photo()
        test_photo_file_deleted()
        
        # Test 7: Re-upload and delete mechanic
        test_reupload_and_delete_mechanic()
        
        # Test 8: Regression tests
        test_regression_services()
        test_regression_stats()
        test_regression_monthly_report()
        
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
