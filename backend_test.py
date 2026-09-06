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


def test_spareparts_basic():
    """Test 9: GET /api/spareparts - basic structure"""
    print("\n=== TEST 9: GET /api/spareparts (basic) ===")
    
    resp = requests.get(f"{API_BASE}/spareparts", timeout=10)
    
    if resp.status_code != 200:
        log_test("9", "FAIL", f"GET /api/spareparts returned {resp.status_code}")
        return False
    
    data = resp.json()
    
    # Check total_items == 268
    if data.get("total_items") != 268:
        log_test("9", "FAIL", f"Expected total_items=268, got {data.get('total_items')}")
        return False
    
    # Check total_categories == 36
    if data.get("total_categories") != 36:
        log_test("9", "FAIL", f"Expected total_categories=36, got {data.get('total_categories')}")
        return False
    
    # Check groups has exactly 6 entries
    groups = data.get("groups", [])
    if len(groups) != 6:
        log_test("9", "FAIL", f"Expected 6 groups, got {len(groups)}")
        return False
    
    # Check group order
    expected_order = ["CVT & Transmisi", "Mesin & Bahan Bakar", "Kelistrikan", "Ban", "Rem, Kemudi & Suspensi", "Body & Aksesori"]
    actual_order = [g.get("group") for g in groups]
    
    if actual_order != expected_order:
        log_test("9", "FAIL", f"Group order mismatch. Expected: {expected_order}, Got: {actual_order}")
        return False
    
    # Verify every item has required keys
    for group in groups:
        for category in group.get("categories", []):
            for item in category.get("items", []):
                required_keys = ["id", "category", "group", "motor", "price_label", "price", "order"]
                missing_keys = [k for k in required_keys if k not in item]
                if missing_keys:
                    log_test("9", "FAIL", f"Item missing keys: {missing_keys}. Item: {item.get('id')}")
                    return False
                
                # Check price_label starts with "Rp "
                if not item.get("price_label", "").startswith("Rp "):
                    log_test("9", "FAIL", f"price_label doesn't start with 'Rp ': {item.get('price_label')}")
                    return False
    
    log_test("9", "PASS", f"GET /api/spareparts: 268 items, 36 categories, 6 groups in correct order")
    return True


def test_spareparts_search_nmax_lowercase():
    """Test 10: GET /api/spareparts?q=nmax (lowercase)"""
    print("\n=== TEST 10: GET /api/spareparts?q=nmax ===")
    
    resp = requests.get(f"{API_BASE}/spareparts", params={"q": "nmax"}, timeout=10)
    
    if resp.status_code != 200:
        log_test("10", "FAIL", f"GET /api/spareparts?q=nmax returned {resp.status_code}")
        return False
    
    data = resp.json()
    total_items = data.get("total_items", 0)
    
    if total_items == 0:
        log_test("10", "FAIL", "Expected total_items > 0 for query 'nmax'")
        return False
    
    # Verify every returned item contains "nmax" (case-insensitive)
    for group in data.get("groups", []):
        for category in group.get("categories", []):
            for item in category.get("items", []):
                searchable = f"{item.get('category', '')} {item.get('motor', '')} {item.get('variant', '')} {item.get('group', '')} {item.get('description', '')}".lower()
                if "nmax" not in searchable:
                    log_test("10", "FAIL", f"Item doesn't contain 'nmax': {item.get('motor')} - {item.get('category')}")
                    return False
    
    log_test("10", "PASS", f"Search 'nmax' returned {total_items} items, all contain 'nmax'")
    return total_items


def test_spareparts_search_nmax_uppercase():
    """Test 11: GET /api/spareparts?q=NMAX (uppercase) - should return same count"""
    print("\n=== TEST 11: GET /api/spareparts?q=NMAX (uppercase) ===")
    
    resp = requests.get(f"{API_BASE}/spareparts", params={"q": "NMAX"}, timeout=10)
    
    if resp.status_code != 200:
        log_test("11", "FAIL", f"GET /api/spareparts?q=NMAX returned {resp.status_code}")
        return False
    
    data = resp.json()
    uppercase_count = data.get("total_items", 0)
    
    # Get lowercase count from previous test
    resp_lower = requests.get(f"{API_BASE}/spareparts", params={"q": "nmax"}, timeout=10)
    lowercase_count = resp_lower.json().get("total_items", 0)
    
    if uppercase_count != lowercase_count:
        log_test("11", "FAIL", f"Uppercase 'NMAX' returned {uppercase_count} items, lowercase 'nmax' returned {lowercase_count}")
        return False
    
    log_test("11", "PASS", f"Search 'NMAX' (uppercase) returned same count as lowercase: {uppercase_count} items")
    return True


def test_spareparts_filter_group_ban():
    """Test 12: GET /api/spareparts?group=Ban"""
    print("\n=== TEST 12: GET /api/spareparts?group=Ban ===")
    
    resp = requests.get(f"{API_BASE}/spareparts", params={"group": "Ban"}, timeout=10)
    
    if resp.status_code != 200:
        log_test("12", "FAIL", f"GET /api/spareparts?group=Ban returned {resp.status_code}")
        return False
    
    data = resp.json()
    groups = data.get("groups", [])
    
    # Should have only 1 group
    if len(groups) != 1:
        log_test("12", "FAIL", f"Expected 1 group, got {len(groups)}")
        return False
    
    # Group should be "Ban"
    if groups[0].get("group") != "Ban":
        log_test("12", "FAIL", f"Expected group 'Ban', got '{groups[0].get('group')}'")
        return False
    
    # Check categories
    categories = groups[0].get("categories", [])
    category_names = [c.get("category") for c in categories]
    
    expected_categories = ["Ban Depan", "Ban Belakang"]
    if not all(cat in category_names for cat in expected_categories):
        log_test("12", "FAIL", f"Expected categories {expected_categories}, got {category_names}")
        return False
    
    # Verify items have size, description, price_prefix
    for category in categories:
        for item in category.get("items", []):
            if "size" not in item:
                log_test("12", "FAIL", f"Item missing 'size': {item.get('motor')}")
                return False
            if "description" not in item:
                log_test("12", "FAIL", f"Item missing 'description': {item.get('motor')}")
                return False
            if item.get("price_prefix") != "Mulai dari":
                log_test("12", "FAIL", f"Expected price_prefix='Mulai dari', got '{item.get('price_prefix')}'")
                return False
    
    log_test("12", "PASS", f"Filter group=Ban: 1 group with Ban Depan & Ban Belakang, items have size/description/price_prefix")
    return True


def test_spareparts_filter_category_busi():
    """Test 13: GET /api/spareparts?category=Busi NGK"""
    print("\n=== TEST 13: GET /api/spareparts?category=Busi NGK ===")
    
    resp = requests.get(f"{API_BASE}/spareparts", params={"category": "Busi NGK"}, timeout=10)
    
    if resp.status_code != 200:
        log_test("13", "FAIL", f"GET /api/spareparts?category=Busi NGK returned {resp.status_code}")
        return False
    
    data = resp.json()
    total_items = data.get("total_items", 0)
    
    # Should have 8 items
    if total_items != 8:
        log_test("13", "FAIL", f"Expected 8 items for 'Busi NGK', got {total_items}")
        return False
    
    # Verify each item has variant starting with "NGK "
    for group in data.get("groups", []):
        for category in group.get("categories", []):
            for item in category.get("items", []):
                variant = item.get("variant", "")
                if not variant.startswith("NGK "):
                    log_test("13", "FAIL", f"Variant doesn't start with 'NGK ': {variant}")
                    return False
    
    log_test("13", "PASS", f"Filter category='Busi NGK': 8 items, all variants start with 'NGK '")
    return True


def test_spareparts_filter_category_aki():
    """Test 14: GET /api/spareparts?category=Aki GS Astra"""
    print("\n=== TEST 14: GET /api/spareparts?category=Aki GS Astra ===")
    
    resp = requests.get(f"{API_BASE}/spareparts", params={"category": "Aki GS Astra"}, timeout=10)
    
    if resp.status_code != 200:
        log_test("14", "FAIL", f"GET /api/spareparts?category=Aki GS Astra returned {resp.status_code}")
        return False
    
    data = resp.json()
    total_items = data.get("total_items", 0)
    
    # Should have 4 items
    if total_items != 4:
        log_test("14", "FAIL", f"Expected 4 items for 'Aki GS Astra', got {total_items}")
        return False
    
    # Verify each item has variant and capacity
    gtz8v_item = None
    for group in data.get("groups", []):
        for category in group.get("categories", []):
            for item in category.get("items", []):
                if "variant" not in item:
                    log_test("14", "FAIL", f"Item missing 'variant': {item.get('motor')}")
                    return False
                if "capacity" not in item:
                    log_test("14", "FAIL", f"Item missing 'capacity': {item.get('motor')}")
                    return False
                
                # Find GTZ8V item
                if "GTZ8V" in item.get("variant", ""):
                    gtz8v_item = item
    
    # Check GTZ8V price_label
    if not gtz8v_item:
        log_test("14", "FAIL", "GTZ8V item not found")
        return False
    
    expected_price_label = "Rp 500.000 – Rp 815.000"
    if gtz8v_item.get("price_label") != expected_price_label:
        log_test("14", "FAIL", f"GTZ8V price_label: expected '{expected_price_label}', got '{gtz8v_item.get('price_label')}'")
        return False
    
    log_test("14", "PASS", f"Filter category='Aki GS Astra': 4 items with variant/capacity, GTZ8V price correct")
    return True


def test_spareparts_search_empty():
    """Test 15: GET /api/spareparts?q=zzzz (no results)"""
    print("\n=== TEST 15: GET /api/spareparts?q=zzzz (empty) ===")
    
    resp = requests.get(f"{API_BASE}/spareparts", params={"q": "zzzz"}, timeout=10)
    
    if resp.status_code != 200:
        log_test("15", "FAIL", f"GET /api/spareparts?q=zzzz returned {resp.status_code}")
        return False
    
    data = resp.json()
    
    if data.get("total_items") != 0:
        log_test("15", "FAIL", f"Expected total_items=0, got {data.get('total_items')}")
        return False
    
    if data.get("total_categories") != 0:
        log_test("15", "FAIL", f"Expected total_categories=0, got {data.get('total_categories')}")
        return False
    
    if len(data.get("groups", [])) != 0:
        log_test("15", "FAIL", f"Expected empty groups array, got {len(data.get('groups', []))} groups")
        return False
    
    log_test("15", "PASS", "Search 'zzzz' returned 0 items, 0 categories, empty groups")
    return True


def test_spareparts_meta():
    """Test 16: GET /api/spareparts/meta"""
    print("\n=== TEST 16: GET /api/spareparts/meta ===")
    
    resp = requests.get(f"{API_BASE}/spareparts/meta", timeout=10)
    
    if resp.status_code != 200:
        log_test("16", "FAIL", f"GET /api/spareparts/meta returned {resp.status_code}")
        return False
    
    data = resp.json()
    
    # Check total_items == 268
    if data.get("total_items") != 268:
        log_test("16", "FAIL", f"Expected total_items=268, got {data.get('total_items')}")
        return False
    
    # Check 6 groups
    groups = data.get("groups", [])
    if len(groups) != 6:
        log_test("16", "FAIL", f"Expected 6 groups, got {len(groups)}")
        return False
    
    # Verify each group has group, categories (list of str), count
    total_count = 0
    for group in groups:
        if "group" not in group:
            log_test("16", "FAIL", f"Group missing 'group' field")
            return False
        
        if "categories" not in group or not isinstance(group["categories"], list):
            log_test("16", "FAIL", f"Group '{group.get('group')}' missing or invalid 'categories' field")
            return False
        
        # Check categories are strings
        if not all(isinstance(cat, str) for cat in group["categories"]):
            log_test("16", "FAIL", f"Group '{group.get('group')}' has non-string categories")
            return False
        
        if "count" not in group:
            log_test("16", "FAIL", f"Group '{group.get('group')}' missing 'count' field")
            return False
        
        total_count += group["count"]
    
    # Sum of counts should equal 268
    if total_count != 268:
        log_test("16", "FAIL", f"Sum of group counts is {total_count}, expected 268")
        return False
    
    log_test("16", "PASS", f"GET /api/spareparts/meta: 268 items, 6 groups with categories/count, sum=268")
    return True


def test_spareparts_combined_filter():
    """Test 17: GET /api/spareparts?group=Kelistrikan&q=aerox"""
    print("\n=== TEST 17: GET /api/spareparts?group=Kelistrikan&q=aerox ===")
    
    resp = requests.get(f"{API_BASE}/spareparts", params={"group": "Kelistrikan", "q": "aerox"}, timeout=10)
    
    if resp.status_code != 200:
        log_test("17", "FAIL", f"GET /api/spareparts?group=Kelistrikan&q=aerox returned {resp.status_code}")
        return False
    
    data = resp.json()
    
    # Verify all items are in Kelistrikan group and match aerox
    for group in data.get("groups", []):
        if group.get("group") != "Kelistrikan":
            log_test("17", "FAIL", f"Found group '{group.get('group')}', expected only 'Kelistrikan'")
            return False
        
        for category in group.get("categories", []):
            for item in category.get("items", []):
                # Check group
                if item.get("group") != "Kelistrikan":
                    log_test("17", "FAIL", f"Item has group '{item.get('group')}', expected 'Kelistrikan'")
                    return False
                
                # Check contains aerox
                searchable = f"{item.get('category', '')} {item.get('motor', '')} {item.get('variant', '')} {item.get('group', '')} {item.get('description', '')}".lower()
                if "aerox" not in searchable:
                    log_test("17", "FAIL", f"Item doesn't contain 'aerox': {item.get('motor')} - {item.get('category')}")
                    return False
    
    total_items = data.get("total_items", 0)
    log_test("17", "PASS", f"Combined filter group=Kelistrikan&q=aerox: {total_items} items, all match both filters")
    return True


def test_regression_mechanics_with_photo():
    """Test 18: Regression - GET /api/mechanics (5 with photo)"""
    print("\n=== TEST 18: Regression - GET /api/mechanics ===")
    
    resp = requests.get(f"{API_BASE}/mechanics", timeout=10)
    
    if resp.status_code != 200:
        log_test("18", "FAIL", f"GET /api/mechanics returned {resp.status_code}")
        return False
    
    mechanics = resp.json()
    
    # Should have at least 5 mechanics
    if len(mechanics) < 5:
        log_test("18", "FAIL", f"Expected at least 5 mechanics, got {len(mechanics)}")
        return False
    
    # Check each has photo
    mechanics_without_photo = [m.get("name") for m in mechanics if "photo" not in m or not m["photo"]]
    if mechanics_without_photo:
        log_test("18", "FAIL", f"Mechanics without photo: {mechanics_without_photo}")
        return False
    
    log_test("18", "PASS", f"GET /api/mechanics: {len(mechanics)} mechanics, all have photo field")
    return True


def test_regression_services_no_price():
    """Test 19: Regression - GET /api/services (4, no price)"""
    print("\n=== TEST 19: Regression - GET /api/services ===")
    
    resp = requests.get(f"{API_BASE}/services", timeout=10)
    
    if resp.status_code != 200:
        log_test("19", "FAIL", f"GET /api/services returned {resp.status_code}")
        return False
    
    services = resp.json()
    
    # Should have 4 services
    if len(services) != 4:
        log_test("19", "FAIL", f"Expected 4 services, got {len(services)}")
        return False
    
    # Check no service has price
    services_with_price = [s.get("name") for s in services if "price" in s]
    if services_with_price:
        log_test("19", "FAIL", f"Services with price field: {services_with_price}")
        return False
    
    log_test("19", "PASS", f"GET /api/services: 4 services, none have price field")
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
    print("ALDI MOTOR - Backend API Test Suite")
    print("="*60)
    
    try:
        # Login
        login()
        
        # NEW SPAREPARTS TESTS (Priority)
        print("\n" + "="*60)
        print("SPAREPARTS API TESTS")
        print("="*60)
        
        test_spareparts_basic()
        test_spareparts_search_nmax_lowercase()
        test_spareparts_search_nmax_uppercase()
        test_spareparts_filter_group_ban()
        test_spareparts_filter_category_busi()
        test_spareparts_filter_category_aki()
        test_spareparts_search_empty()
        test_spareparts_meta()
        test_spareparts_combined_filter()
        
        # REGRESSION TESTS
        print("\n" + "="*60)
        print("REGRESSION TESTS")
        print("="*60)
        
        test_regression_mechanics_with_photo()
        test_regression_services_no_price()
        
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
