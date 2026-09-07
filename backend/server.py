from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import logging
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta, date, time
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict


# ----------------- Setup -----------------
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "adminaldimotor")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "aldimotorjaya")
WORKSHOP_WHATSAPP = os.environ.get("WORKSHOP_WHATSAPP", "6285657237827")
WORKSHOP_NAME = os.environ.get("WORKSHOP_NAME", "ALDI MOTOR")

JWT_ALG = "HS256"
TZ = ZoneInfo("Asia/Makassar")

# Persistent upload storage (served at /api/uploads/...)
UPLOAD_DIR = ROOT_DIR / "uploads"
MECHANIC_PHOTO_DIR = UPLOAD_DIR / "mechanics"
MECHANIC_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB
PHOTO_SIZE = 480

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="ALDI MOTOR API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ----------------- Helpers -----------------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def create_access_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id, "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def normalize_wa(phone: str) -> str:
    p = "".join(c for c in phone if c.isdigit())
    if p.startswith("0"):
        p = "62" + p[1:]
    elif p.startswith("62"):
        pass
    elif p.startswith("8"):
        p = "62" + p
    return p


def today_local() -> date:
    return datetime.now(TZ).date()


# ----------------- Models -----------------
class LoginReq(BaseModel):
    username: str
    password: str

class MechanicIn(BaseModel):
    name: str
    status: Optional[str] = "active"  # active | inactive
    photo: Optional[str] = None  # URL/path foto profil

class MechanicUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    photo: Optional[str] = None

class ServiceUpdate(BaseModel):
    duration_hours: Optional[float] = None
    description: Optional[str] = None

class HolidayIn(BaseModel):
    date: str  # YYYY-MM-DD
    description: str

class BreakIn(BaseModel):
    weekday: int  # 0=Senin ... 6=Minggu
    start: str  # "11:00"
    end: str  # "14:00"
    label: Optional[str] = "Istirahat"

class BusinessHoursUpdate(BaseModel):
    opening_time: str  # "08:30"
    closing_time: str  # "16:30"
    breaks: Optional[List[BreakIn]] = None

class SparepartIn(BaseModel):
    category: str = Field(min_length=2)
    group: str = Field(min_length=2)
    motor: str = Field(min_length=1)
    price: Optional[float] = None
    price_label: Optional[str] = None  # jika kosong, dibuat dari price
    price_prefix: Optional[str] = None
    description: Optional[str] = None
    size: Optional[str] = None
    variant: Optional[str] = None
    capacity: Optional[str] = None

class ServicePriceIn(BaseModel):
    category: str = Field(min_length=2)
    motor: str = Field(min_length=1)
    ringan: Optional[float] = None
    berat: Optional[float] = None
    overhaul: Optional[float] = None

class ServicePriceUpdate(BaseModel):
    category: Optional[str] = None
    motor: Optional[str] = None
    ringan: Optional[float] = None
    berat: Optional[float] = None
    overhaul: Optional[float] = None

class SparepartUpdate(BaseModel):
    category: Optional[str] = None
    group: Optional[str] = None
    motor: Optional[str] = None
    price: Optional[float] = None
    price_label: Optional[str] = None
    price_prefix: Optional[str] = None
    description: Optional[str] = None
    size: Optional[str] = None
    variant: Optional[str] = None
    capacity: Optional[str] = None

class BookingCreate(BaseModel):
    customer_name: str = Field(min_length=3)
    whatsapp: str
    plate_number: str
    motor_type: str = Field(min_length=2, max_length=80)  # jenis/tipe motor customer, mis. "NMAX 155"
    complaint: str
    service_id: str
    booking_date: str  # YYYY-MM-DD
    start_time: str  # "HH:MM"

class BookingUpdate(BaseModel):
    status: Optional[str] = None
    duration_hours: Optional[float] = None
    mechanic_id: Optional[str] = None


# ----------------- Seed / Init -----------------
async def seed_data():
    # Admin user (login via username)
    # Migrate: delete any old admin whose username does NOT match ADMIN_USERNAME (e.g. email-based admins)
    await db.users.delete_many({
        "role": "admin",
        "$or": [
            {"username": {"$ne": ADMIN_USERNAME}},
            {"username": {"$exists": False}},
        ],
    })
    existing = await db.users.find_one({"username": ADMIN_USERNAME})
    if existing is None:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "username": ADMIN_USERNAME,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one({"username": ADMIN_USERNAME}, {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}})

    # Services
    default_services = [
        {"code": "ringan", "name": "Servis Ringan", "description": "Servis berkala dan pemeriksaan ringan kendaraan.", "duration_hours": 1.0},
        {"code": "berat", "name": "Servis Berat", "description": "Penanganan kerusakan atau servis dengan tingkat pengerjaan lebih kompleks.", "duration_hours": 2.0},
        {"code": "overhaul", "name": "Overhaul", "description": "Pengerjaan pembongkaran dan pemeriksaan komponen mesin secara menyeluruh.", "duration_hours": 4.0},
        {"code": "request", "name": "Request Customer", "description": "Customer dapat menjelaskan kebutuhan atau pekerjaan khusus.", "duration_hours": 1.0},
    ]
    for svc in default_services:
        exists = await db.services.find_one({"code": svc["code"]})
        if not exists:
            await db.services.insert_one({
                "id": str(uuid.uuid4()),
                **svc,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    # Migrate: hapus field harga (sistem tidak memakai pembayaran/harga)
    await db.services.update_many({"price": {"$exists": True}}, {"$unset": {"price": ""}})
    await db.bookings.update_many({"price": {"$exists": True}}, {"$unset": {"price": ""}})

    # Mechanics (profil asli tim ALDI MOTOR)
    default_mechanics = [
        {"name": "Andi Muh Wahidin", "photo": "/mechanics/andi-muh-wahidin.jpg"},
        {"name": "Ahmad Balla", "photo": "/mechanics/ahmad-balla.jpg"},
        {"name": "Kasim", "photo": "/mechanics/kasim.jpg"},
        {"name": "Ansar", "photo": "/mechanics/ansar.jpg"},
        {"name": "Muh Risal", "photo": "/mechanics/muh-risal.jpg"},
    ]
    count = await db.mechanics.count_documents({})
    if count == 0:
        for i, m in enumerate(default_mechanics):
            await db.mechanics.insert_one({
                "id": str(uuid.uuid4()),
                **m,
                "status": "active",
                "created_at": (datetime.now(timezone.utc) + timedelta(seconds=i)).isoformat(),
            })
    else:
        # Migrate: ganti nama placeholder "Mekanik N" ke profil asli + foto (berurutan)
        placeholders = await db.mechanics.find({"name": {"$regex": r"^Mekanik \d+$"}}, {"_id": 0}).to_list(100)
        placeholders.sort(key=lambda m: m.get("name", ""))
        for m, real in zip(placeholders, default_mechanics):
            await db.mechanics.update_one({"id": m["id"]}, {"$set": real})
        # Lengkapi foto untuk mekanik dengan nama asli yang belum punya foto
        for real in default_mechanics:
            await db.mechanics.update_one(
                {"name": real["name"], "photo": {"$exists": False}}, {"$set": {"photo": real["photo"]}}
            )
        # Sinkronkan nama mekanik pada booking lama
        for m in await db.mechanics.find({}, {"_id": 0}).to_list(100):
            await db.bookings.update_many({"mechanic_id": m["id"]}, {"$set": {"mechanic_name": m["name"]}})

    # Spareparts (dari spreadsheet "Data untuk web.xlsx" sheet Sparepart)
    if await db.spareparts.count_documents({}) == 0:
        seed_file = ROOT_DIR / "spareparts_seed.json"
        if seed_file.exists():
            import json
            with open(seed_file, encoding="utf-8") as f:
                parts = json.load(f)
            if parts:
                await db.spareparts.insert_many(parts)
                logger.info("Seeded %d spareparts", len(parts))

    # Biaya jasa servis per tipe motor (sheet "Data Service Ringan dan Berat")
    if await db.service_prices.count_documents({}) == 0:
        seed_file = ROOT_DIR / "service_prices_seed.json"
        if seed_file.exists():
            import json
            with open(seed_file, encoding="utf-8") as f:
                rows = json.load(f)
            if rows:
                await db.service_prices.insert_many(rows)
                logger.info("Seeded %d service prices", len(rows))

    # Business hours (Senin-Sabtu 08:30-16:30, Jumat istirahat 11:00-14:00)
    default_breaks = [{"weekday": 4, "start": "11:00", "end": "14:00", "label": "Istirahat Sholat Jumat"}]
    bh_doc = await db.settings.find_one({"key": "business_hours"})
    if not bh_doc:
        await db.settings.insert_one({
            "key": "business_hours",
            "opening_time": "08:30",
            "closing_time": "16:30",
            "closed_days": [6],  # Sunday (Python: Mon=0, Sun=6)
            "breaks": default_breaks,
            "schedule_version": 2,
        })
    elif bh_doc.get("schedule_version", 1) < 2:
        # Migrate jadwal lama (08:00-16:00 tanpa istirahat) ke jadwal baru
        await db.settings.update_one(
            {"key": "business_hours"},
            {"$set": {"opening_time": "08:30", "closing_time": "16:30", "breaks": default_breaks, "schedule_version": 2}},
        )


@app.on_event("startup")
async def startup():
    # Drop legacy email index if present, ensure username index
    try:
        await db.users.drop_index("email_1")
    except Exception:
        pass
    await db.users.create_index("username", unique=True)
    await db.bookings.create_index([("booking_date", 1), ("mechanic_id", 1)])
    await seed_data()
    logger.info("ALDI MOTOR API started")


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ----------------- Auth -----------------
@api.post("/auth/login")
async def login(body: LoginReq, response: Response):
    user = await db.users.find_one({"username": body.username.lower().strip()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    token = create_access_token(user["id"], user["username"])
    response.set_cookie(
        key="access_token", value=token, httponly=True, secure=True,
        samesite="none", max_age=7 * 24 * 3600, path="/",
    )
    return {
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "name": user["name"], "role": user["role"]},
    }


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# ----------------- Public: services, mechanics, business hours, holidays -----------------
@api.get("/services")
async def list_services():
    docs = await db.services.find({"status": "active"}, {"_id": 0}).to_list(100)
    order = {"ringan": 1, "berat": 2, "overhaul": 3, "request": 4}
    docs.sort(key=lambda d: order.get(d.get("code"), 99))
    return docs


@api.get("/mechanics")
async def list_mechanics():
    docs = await db.mechanics.find({}, {"_id": 0}).to_list(100)
    return docs


@api.get("/business-hours")
async def get_business_hours():
    doc = await db.settings.find_one({"key": "business_hours"}, {"_id": 0})
    today = today_local()
    return {
        **(doc or {}),
        "today": today.isoformat(),
        "min_date": (today + timedelta(days=1)).isoformat(),
        "max_date": (today + timedelta(days=7)).isoformat(),
    }


@api.get("/holidays")
async def list_holidays():
    docs = await db.holidays.find({}, {"_id": 0}).to_list(500)
    docs.sort(key=lambda d: d.get("date", ""))
    return docs


# ----------------- Public: biaya servis -----------------
SERVICE_PRICE_TYPES = [
    {"code": "ringan", "key": "ringan", "name": "Servis Ringan"},
    {"code": "berat", "key": "berat", "name": "Servis Berat"},
    {"code": "overhaul", "key": "overhaul", "name": "Overhaul"},
]


@api.get("/service-prices")
async def list_service_prices(q: Optional[str] = None, category: Optional[str] = None):
    """Biaya jasa servis (ringan/berat/overhaul) per tipe motor, dikelompokkan per kategori motor."""
    query = {}
    if category:
        query["category"] = category
    docs = await db.service_prices.find(query, {"_id": 0}).to_list(1000)
    if q:
        ql = q.lower().strip()
        docs = [d for d in docs if ql in d.get("motor", "").lower() or ql in d.get("category", "").lower()]
    docs.sort(key=lambda d: (d.get("category_order", 0), d.get("order", 0)))

    services = await db.services.find({"status": "active"}, {"_id": 0, "code": 1, "name": 1, "duration_hours": 1, "description": 1}).to_list(50)
    svc_by_code = {s_["code"]: s_ for s_ in services}
    types = []
    for t in SERVICE_PRICE_TYPES:
        svc = svc_by_code.get(t["code"], {})
        types.append({**t, "duration_hours": svc.get("duration_hours"), "description": svc.get("description")})

    categories = []
    index = {}
    for d in docs:
        c = d["category"]
        if c not in index:
            index[c] = {"category": c, "items": []}
            categories.append(index[c])
        index[c]["items"].append({
            "id": d["id"], "motor": d["motor"],
            "prices": {k: d.get(k) for k in ("ringan", "berat", "overhaul")},
        })
    all_docs = docs if not (q or category) else await db.service_prices.find({}, {"_id": 0}).to_list(1000)
    summary = {}
    for k in ("ringan", "berat", "overhaul"):
        vals = [d[k] for d in all_docs if d.get(k) is not None]
        summary[k] = {"min": min(vals) if vals else None, "max": max(vals) if vals else None}
    return {
        "total_motors": len(docs),
        "types": types,
        "categories": categories,
        "summary": summary,
        "all_categories": sorted({d["category"] for d in all_docs}, key=lambda c: next((d["category_order"] for d in all_docs if d["category"] == c), 99)),
        "note": "Harga di atas adalah biaya jasa servis, belum termasuk sparepart dan oli. Harga dapat berubah sewaktu-waktu.",
    }


# ----------------- Admin: biaya servis -----------------
def _validate_prices(payload: dict):
    for k in ("ringan", "berat", "overhaul"):
        v = payload.get(k)
        if v is not None and v < 0:
            raise HTTPException(400, f"Harga {k} tidak boleh negatif")


async def _category_order_for(category: str) -> int:
    existing = await db.service_prices.find_one({"category": category}, {"_id": 0, "category_order": 1})
    if existing:
        return existing.get("category_order", 0)
    last = await db.service_prices.find({}, {"_id": 0, "category_order": 1}).sort("category_order", -1).to_list(1)
    return (last[0].get("category_order", 0) + 1) if last else 0


@api.get("/admin/service-prices")
async def admin_list_service_prices(user: dict = Depends(get_current_user)):
    docs = await db.service_prices.find({}, {"_id": 0}).to_list(1000)
    docs.sort(key=lambda d: (d.get("category_order", 0), d.get("order", 0)))
    return docs


@api.post("/admin/service-prices")
async def admin_create_service_price(body: ServicePriceIn, user: dict = Depends(get_current_user)):
    payload = body.model_dump()
    _validate_prices(payload)
    category = payload["category"].strip()
    motor = payload["motor"].strip()
    if await db.service_prices.find_one({"category": category, "motor": {"$regex": f"^{motor}$", "$options": "i"}}):
        raise HTTPException(400, "Tipe motor tersebut sudah ada di kategori ini")
    last = await db.service_prices.find({}, {"_id": 0, "order": 1}).sort("order", -1).to_list(1)
    doc = {
        "id": str(uuid.uuid4()),
        "category": category,
        "category_order": await _category_order_for(category),
        "motor": motor,
        "ringan": payload.get("ringan"),
        "berat": payload.get("berat"),
        "overhaul": payload.get("overhaul"),
        "order": (last[0].get("order", 0) + 1) if last else 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.service_prices.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@api.patch("/admin/service-prices/{pid}")
async def admin_update_service_price(pid: str, body: ServicePriceUpdate, user: dict = Depends(get_current_user)):
    existing = await db.service_prices.find_one({"id": pid}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Data biaya servis tidak ditemukan")
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(400, "Tidak ada perubahan")
    _validate_prices(payload)
    if "category" in payload:
        payload["category"] = payload["category"].strip()
        payload["category_order"] = await _category_order_for(payload["category"])
    if "motor" in payload:
        payload["motor"] = payload["motor"].strip()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.service_prices.update_one({"id": pid}, {"$set": payload})
    return await db.service_prices.find_one({"id": pid}, {"_id": 0})


@api.delete("/admin/service-prices/{pid}")
async def admin_delete_service_price(pid: str, user: dict = Depends(get_current_user)):
    r = await db.service_prices.delete_one({"id": pid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Data biaya servis tidak ditemukan")
    return {"ok": True}


# ----------------- Public: spareparts -----------------
GROUP_ORDER = ["CVT & Transmisi", "Mesin & Bahan Bakar", "Kelistrikan", "Ban", "Rem, Kemudi & Suspensi", "Body & Aksesori"]


@api.get("/spareparts")
async def list_spareparts(q: Optional[str] = None, group: Optional[str] = None, category: Optional[str] = None):
    """Daftar sparepart dikelompokkan per kategori. Filter opsional: q (cari), group, category."""
    query = {}
    if group:
        query["group"] = group
    if category:
        query["category"] = category
    docs = await db.spareparts.find(query, {"_id": 0}).to_list(2000)
    if q:
        ql = q.lower().strip()
        docs = [
            d for d in docs
            if ql in d.get("category", "").lower()
            or ql in d.get("motor", "").lower()
            or ql in d.get("variant", "").lower()
            or ql in d.get("group", "").lower()
            or ql in (d.get("description") or "").lower()
        ]
    docs.sort(key=lambda d: d.get("order", 0))

    categories = []
    index = {}
    for d in docs:
        key = d["category"]
        if key not in index:
            index[key] = {"category": key, "group": d["group"], "items": []}
            categories.append(index[key])
        index[key]["items"].append(d)

    groups = []
    gindex = {}
    for c in categories:
        g = c["group"]
        if g not in gindex:
            gindex[g] = {"group": g, "categories": []}
            groups.append(gindex[g])
        gindex[g]["categories"].append(c)
    groups.sort(key=lambda g: GROUP_ORDER.index(g["group"]) if g["group"] in GROUP_ORDER else 99)

    return {
        "total_items": len(docs),
        "total_categories": len(categories),
        "groups": groups,
    }


@api.get("/spareparts/meta")
async def spareparts_meta():
    docs = await db.spareparts.find({}, {"_id": 0, "group": 1, "category": 1, "order": 1}).to_list(2000)
    docs.sort(key=lambda d: d.get("order", 0))
    groups = []
    seen = {}
    for d in docs:
        g = d["group"]
        if g not in seen:
            seen[g] = {"group": g, "categories": [], "count": 0}
            groups.append(seen[g])
        if d["category"] not in seen[g]["categories"]:
            seen[g]["categories"].append(d["category"])
        seen[g]["count"] += 1
    groups.sort(key=lambda g: GROUP_ORDER.index(g["group"]) if g["group"] in GROUP_ORDER else 99)
    return {"total_items": len(docs), "groups": groups}


def _fmt_rp(n: float) -> str:
    return "Rp " + f"{int(round(n)):,}".replace(",", ".")


def _sparepart_doc_from(body: dict, existing: Optional[dict] = None) -> dict:
    doc = dict(existing or {})
    for k, v in body.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            if v == "" and k in ("description", "size", "variant", "capacity", "price_prefix", "price_label"):
                doc.pop(k, None)
                continue
        doc[k] = v
    if "price" in body and body["price"] is not None:
        doc["price"] = float(body["price"])
        if not body.get("price_label"):
            doc["price_label"] = _fmt_rp(doc["price"])
    if not doc.get("price_label"):
        doc["price_label"] = _fmt_rp(doc.get("price") or 0)
    return doc


@api.get("/admin/spareparts")
async def admin_list_spareparts(user: dict = Depends(get_current_user), q: Optional[str] = None, group: Optional[str] = None):
    query = {}
    if group:
        query["group"] = group
    docs = await db.spareparts.find(query, {"_id": 0}).to_list(3000)
    if q:
        ql = q.lower().strip()
        docs = [d for d in docs if ql in d.get("category", "").lower() or ql in d.get("motor", "").lower() or ql in d.get("variant", "").lower()]
    docs.sort(key=lambda d: d.get("order", 0))
    return docs


@api.post("/admin/spareparts")
async def admin_create_sparepart(body: SparepartIn, user: dict = Depends(get_current_user)):
    last = await db.spareparts.find({}, {"_id": 0, "order": 1}).sort("order", -1).to_list(1)
    next_order = (last[0].get("order", 0) + 1) if last else 0
    doc = _sparepart_doc_from(body.model_dump())
    doc["id"] = str(uuid.uuid4())
    doc["order"] = next_order
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.spareparts.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@api.patch("/admin/spareparts/{sid}")
async def admin_update_sparepart(sid: str, body: SparepartUpdate, user: dict = Depends(get_current_user)):
    existing = await db.spareparts.find_one({"id": sid}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Sparepart tidak ditemukan")
    payload = body.model_dump()
    if all(v is None for v in payload.values()):
        raise HTTPException(400, "Tidak ada perubahan")
    doc = _sparepart_doc_from(payload, existing)
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.spareparts.replace_one({"id": sid}, doc)
    return await db.spareparts.find_one({"id": sid}, {"_id": 0})


@api.delete("/admin/spareparts/{sid}")
async def admin_delete_sparepart(sid: str, user: dict = Depends(get_current_user)):
    r = await db.spareparts.delete_one({"id": sid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Sparepart tidak ditemukan")
    return {"ok": True}


# ----------------- Customer plate history (public, minimal fields) -----------------
@api.get("/customer/history")
async def customer_history(plate: str = Query(..., min_length=3)):
    plate_up = plate.upper().strip()
    docs = await db.bookings.find(
        {"plate_number": plate_up},
        {"_id": 0, "whatsapp": 0, "customer_id": 0},
    ).to_list(50)
    docs.sort(key=lambda x: (x["booking_date"], x["start_time"]), reverse=True)
    # Return only last 5, minimal fields for privacy
    result = []
    for b in docs[:5]:
        result.append({
            "booking_number": b["booking_number"],
            "booking_date": b["booking_date"],
            "start_time": b["start_time"],
            "service_name": b["service_name"],
            "mechanic_name": b["mechanic_name"],
            "motor_type": b.get("motor_type"),
            "complaint": b["complaint"],
            "status": b["status"],
        })
    return {"plate_number": plate_up, "count": len(docs), "recent": result}


# ----------------- Availability -----------------
def parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


async def get_active_mechanics() -> List[dict]:
    return await db.mechanics.find({"status": "active"}, {"_id": 0}).to_list(100)


async def get_bookings_for_date(booking_date: str) -> List[dict]:
    return await db.bookings.find(
        {"booking_date": booking_date, "status": {"$ne": "Dibatalkan"}},
        {"_id": 0},
    ).to_list(500)


def to_min(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def from_min(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"


def day_windows(bh: dict, weekday: int) -> List[tuple]:
    """Sesi buka pada hari tertentu setelah dikurangi jam istirahat. Return list of (start_min, end_min)."""
    open_m, close_m = to_min(bh["opening_time"]), to_min(bh["closing_time"])
    windows = [(open_m, close_m)]
    for br in bh.get("breaks", []) or []:
        if int(br.get("weekday", -1)) != weekday:
            continue
        bs, be = to_min(br["start"]), to_min(br["end"])
        new = []
        for ws, we in windows:
            if be <= ws or bs >= we:
                new.append((ws, we))
                continue
            if bs > ws:
                new.append((ws, bs))
            if be < we:
                new.append((be, we))
        windows = new
    return [(a, b) for a, b in windows if b > a]


def slot_starts(bh: dict, weekday: int) -> List[dict]:
    """Kandidat jam mulai (tiap 1 jam dari awal sesi). Tiap item: {time, window_end}."""
    out = []
    for ws, we in day_windows(bh, weekday):
        t = ws
        while t < we:
            out.append({"time": from_min(t), "window_end": from_min(we)})
            t += 60
    return out


def fits_windows(bh: dict, weekday: int, start: str, end: str) -> bool:
    sm, em = to_min(start), to_min(end)
    return any(ws <= sm and em <= we for ws, we in day_windows(bh, weekday))


def hour_range(open_t: str, close_t: str) -> List[str]:
    # Kompatibilitas: daftar jam mulai per 1 jam dari jam buka sampai sebelum jam tutup
    o, c = to_min(open_t), to_min(close_t)
    return [from_min(t) for t in range(o, c, 60)]


def slot_overlaps(slot_start: str, slot_end: str, existing_start: str, existing_end: str) -> bool:
    return not (slot_end <= existing_start or slot_start >= existing_end)


def add_hours_str(hhmm: str, hours: float) -> str:
    h, m = map(int, hhmm.split(":"))
    total_min = h * 60 + m + int(hours * 60)
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


@api.get("/availability")
async def availability(date_str: str = Query(..., alias="date"), service_id: str = Query(...)):
    # Validate date
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid")

    today = today_local()
    max_date = today + timedelta(days=7)
    if d <= today:
        raise HTTPException(status_code=400, detail="Reservasi hanya dapat dilakukan mulai H+1")
    if d > max_date:
        raise HTTPException(status_code=400, detail="Reservasi maksimal 7 hari ke depan")

    bh = await db.settings.find_one({"key": "business_hours"}, {"_id": 0})
    closed_days = bh.get("closed_days", [6])
    if d.weekday() in closed_days:
        raise HTTPException(status_code=400, detail="Bengkel tutup pada hari tersebut")

    # Holiday
    holiday = await db.holidays.find_one({"date": date_str})
    if holiday:
        raise HTTPException(status_code=400, detail=f"Bengkel tutup: {holiday.get('description','Hari Libur')}")

    service = await db.services.find_one({"id": service_id}, {"_id": 0})
    if not service:
        raise HTTPException(status_code=404, detail="Servis tidak ditemukan")
    duration = float(service["duration_hours"])

    mechanics = await get_active_mechanics()
    total_mechanics = len(mechanics)
    bookings = await get_bookings_for_date(date_str)

    slots = []
    weekday = d.weekday()
    for cand in slot_starts(bh, weekday):
        hhmm = cand["time"]
        slot_start = hhmm
        slot_end = add_hours_str(hhmm, duration)
        # jika servis melebihi akhir sesi (jam tutup / jam istirahat), tandai closed (tidak bisa dipilih)
        if slot_end > cand["window_end"]:
            slots.append({"time": hhmm, "available": 0, "total": total_mechanics, "status": "closed"})
            continue

        # count busy mechanics
        busy = set()
        for b in bookings:
            if slot_overlaps(slot_start, slot_end, b["start_time"], b["end_time"]):
                busy.add(b["mechanic_id"])
        available = max(0, total_mechanics - len(busy))
        if available == 0:
            status = "full"
        elif available <= max(1, total_mechanics // 3):
            status = "almost"
        else:
            status = "available"
        slots.append({"time": hhmm, "available": available, "total": total_mechanics, "status": status})

    breaks_today = [br for br in (bh.get("breaks", []) or []) if int(br.get("weekday", -1)) == weekday]
    return {
        "date": date_str, "service_id": service_id, "duration_hours": duration, "slots": slots,
        "windows": [{"start": from_min(a), "end": from_min(b)} for a, b in day_windows(bh, weekday)],
        "breaks": breaks_today,
    }


# ----------------- Bookings -----------------
async def next_booking_number(booking_date: str) -> str:
    date_compact = booking_date.replace("-", "")
    prefix = f"RSV-{date_compact}-"
    count = await db.bookings.count_documents({"booking_number": {"$regex": f"^{prefix}"}})
    return f"{prefix}{count + 1:04d}"


@api.post("/bookings")
async def create_booking(body: BookingCreate):
    # Validate date
    try:
        d = datetime.strptime(body.booking_date, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid")

    today = today_local()
    if d <= today:
        raise HTTPException(status_code=400, detail="Reservasi hanya untuk H+1")
    if d > today + timedelta(days=7):
        raise HTTPException(status_code=400, detail="Reservasi maksimal 7 hari ke depan")

    bh = await db.settings.find_one({"key": "business_hours"}, {"_id": 0})
    closed_days = bh.get("closed_days", [6])
    if d.weekday() in closed_days:
        raise HTTPException(status_code=400, detail="Bengkel tutup pada hari tersebut")

    if await db.holidays.find_one({"date": body.booking_date}):
        raise HTTPException(status_code=400, detail="Bengkel tutup pada tanggal tersebut")

    service = await db.services.find_one({"id": body.service_id}, {"_id": 0})
    if not service:
        raise HTTPException(status_code=404, detail="Servis tidak ditemukan")
    duration = float(service["duration_hours"])
    start = body.start_time
    end = add_hours_str(start, duration)
    if not fits_windows(bh, d.weekday(), start, end):
        raise HTTPException(status_code=400, detail="Jam tersebut di luar jam operasional atau bertabrakan dengan jam istirahat")

    mechanics = await get_active_mechanics()
    if not mechanics:
        raise HTTPException(status_code=400, detail="Tidak ada mekanik aktif")

    bookings = await get_bookings_for_date(body.booking_date)
    busy_ids = set()
    for b in bookings:
        if slot_overlaps(start, end, b["start_time"], b["end_time"]):
            busy_ids.add(b["mechanic_id"])

    available_mech = next((m for m in mechanics if m["id"] not in busy_ids), None)
    if not available_mech:
        raise HTTPException(status_code=409, detail="Maaf, slot tersebut baru saja penuh. Silakan pilih jam lainnya.")

    # Create customer record (or reuse)
    wa = normalize_wa(body.whatsapp)
    plate = body.plate_number.upper().strip()
    customer_id = str(uuid.uuid4())
    await db.customers.insert_one({
        "id": customer_id, "name": body.customer_name.strip(),
        "whatsapp": wa, "plate_number": plate, "motor_type": body.motor_type.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    booking_number = await next_booking_number(body.booking_date)
    booking = {
        "id": str(uuid.uuid4()),
        "booking_number": booking_number,
        "customer_id": customer_id,
        "customer_name": body.customer_name.strip(),
        "whatsapp": wa,
        "plate_number": plate,
        "motor_type": body.motor_type.strip(),
        "complaint": body.complaint.strip(),
        "service_id": service["id"],
        "service_name": service["name"],
        "service_code": service.get("code"),
        "duration_hours": duration,
        "mechanic_id": available_mech["id"],
        "mechanic_name": available_mech["name"],
        "booking_date": body.booking_date,
        "start_time": start,
        "end_time": end,
        "status": "Menunggu Konfirmasi",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.bookings.insert_one(booking.copy())
    booking.pop("_id", None)

    # WA link (customer sends confirmation TO the workshop's WhatsApp)
    customer_msg = (
        f"Halo *{WORKSHOP_NAME}*,%0A%0A"
        f"Saya baru saja membuat reservasi servis motor. Berikut detailnya:%0A%0A"
        f"Nama: {booking['customer_name']}%0A"
        f"Nomor Reservasi: *{booking['booking_number']}*%0A"
        f"Jenis Servis: {booking['service_name']}%0A"
        f"Tanggal: {booking['booking_date']}%0A"
        f"Jam: {booking['start_time']}%0A"
        f"Jenis Motor: {booking['motor_type']}%0A"
        f"Nomor Polisi: {booking['plate_number']}%0A"
        f"Keluhan: {booking['complaint']}%0A%0A"
        f"Mohon konfirmasi reservasi saya. Terima kasih."
    )
    admin_msg = (
        f"*Reservasi Baru!*%0A%0A"
        f"Nomor: {booking['booking_number']}%0A"
        f"Customer: {booking['customer_name']}%0A"
        f"WhatsApp: {booking['whatsapp']}%0A"
        f"Jenis Motor: {booking['motor_type']}%0A"
        f"Nomor Polisi: {booking['plate_number']}%0A"
        f"Jenis Servis: {booking['service_name']}%0A"
        f"Tanggal: {booking['booking_date']}%0A"
        f"Jam: {booking['start_time']}%0A"
        f"Mekanik: {booking['mechanic_name']}%0A"
        f"Keluhan: {booking['complaint']}"
    )

    return {
        "booking": booking,
        "workshop_whatsapp": WORKSHOP_WHATSAPP,
        # Primary link: customer sends confirmation to the workshop's WA
        "wa_customer_link": f"https://wa.me/{WORKSHOP_WHATSAPP}?text={customer_msg}",
        # Kept for admin internal use if needed
        "wa_admin_link": f"https://wa.me/{WORKSHOP_WHATSAPP}?text={admin_msg}",
    }


# ----------------- Admin Calendar -----------------
@api.get("/admin/calendar/day")
async def calendar_day(date_str: str = Query(..., alias="date"), user: dict = Depends(get_current_user)):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(400, "Format tanggal tidak valid")
    bh = await db.settings.find_one({"key": "business_hours"}, {"_id": 0}) or {"opening_time": "08:30", "closing_time": "16:30", "breaks": []}
    mechanics = await db.mechanics.find({}, {"_id": 0}).to_list(100)
    mechanics.sort(key=lambda m: m.get("created_at", ""))
    bookings = await db.bookings.find(
        {"booking_date": date_str, "status": {"$ne": "Dibatalkan"}}, {"_id": 0}
    ).to_list(500)

    weekday = d.weekday()
    # Kolom kalender: slot per jam di tiap sesi + kolom istirahat di antara sesi
    windows = day_windows(bh, weekday)
    columns = []
    for wi, (ws, we) in enumerate(windows):
        if wi > 0:
            prev_end = windows[wi - 1][1]
            columns.append({"type": "break", "time": from_min(prev_end), "label": f"Istirahat {from_min(prev_end)}–{from_min(ws)}"})
        t = ws
        while t < we:
            columns.append({"type": "slot", "time": from_min(t), "label": from_min(t)})
            t += 60
    hours = [c["time"] for c in columns if c["type"] == "slot"]
    slot_times = hours

    def col_index_for(start_time: str) -> int:
        # kolom slot yang tepat; jika tidak ada (booking lama/jam tidak standar), pakai slot terakhir <= start
        best = None
        for idx, c in enumerate(columns):
            if c["type"] != "slot":
                continue
            if c["time"] == start_time:
                return idx
            if c["time"] <= start_time:
                best = idx
        if best is None:
            best = next((idx for idx, c in enumerate(columns) if c["type"] == "slot"), 0)
        return best

    result_mechs = []
    for m in mechanics:
        my_bookings = sorted([b for b in bookings if b["mechanic_id"] == m["id"]], key=lambda b: b["start_time"])
        # map kolom -> booking yang mulai di sana
        start_map = {}
        for b in my_bookings:
            idx = col_index_for(b["start_time"])
            while idx in start_map and idx + 1 < len(columns):
                idx += 1
            start_map[idx] = b
        cells = []
        i = 0
        while i < len(columns):
            col = columns[i]
            if col["type"] == "break":
                cells.append({"type": "break", "time": col["time"], "span": 1, "label": col["label"]})
                i += 1
                continue
            b_here = start_map.get(i)
            if b_here:
                # span = jumlah kolom slot berurutan yang tercakup durasi (berhenti di kolom istirahat)
                span = 1
                end_m = to_min(b_here["end_time"])
                j = i + 1
                while j < len(columns) and columns[j]["type"] == "slot" and to_min(columns[j]["time"]) < end_m and j not in start_map:
                    span += 1
                    j += 1
                cells.append({"type": "booking", "time": col["time"], "span": span, "booking": b_here})
                i += span
                continue
            covered = any(b["start_time"] < col["time"] < b["end_time"] for b in my_bookings)
            cells.append({"type": "covered" if covered else "empty", "time": col["time"], "span": 1})
            i += 1
        result_mechs.append({
            "id": m["id"],
            "name": m["name"],
            "status": m.get("status", "active"),
            "cells": cells,
        })
    return {
        "date": date_str, "hours": slot_times, "columns": columns, "mechanics": result_mechs,
        "windows": [{"start": from_min(a), "end": from_min(b)} for a, b in windows],
    }


@api.get("/admin/calendar/week")
async def calendar_week(start: str = Query(...), user: dict = Depends(get_current_user)):
    try:
        d = datetime.strptime(start, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(400, "Format tanggal tidak valid")
    days = []
    bh = await db.settings.find_one({"key": "business_hours"}, {"_id": 0}) or {"opening_time": "08:30", "closing_time": "16:30", "breaks": []}
    mechanics_count = await db.mechanics.count_documents({"status": "active"})

    for i in range(7):
        di = d + timedelta(days=i)
        ds = di.isoformat()
        weekday = di.weekday()  # 0=Mon
        total_cap_per_day = mechanics_count * len(slot_starts(bh, weekday))
        is_closed_day = weekday in (bh.get("closed_days", [6]) or [6])
        is_holiday = bool(await db.holidays.find_one({"date": ds}))
        bookings = await db.bookings.find(
            {"booking_date": ds, "status": {"$ne": "Dibatalkan"}}, {"_id": 0, "booking_number": 1, "start_time": 1, "duration_hours": 1, "customer_name": 1, "service_name": 1, "mechanic_name": 1, "status": 1}
        ).to_list(500)
        # occupied cells = sum(duration_hours) of all bookings
        occupied = sum(int(round(float(b.get("duration_hours", 1)))) for b in bookings)
        days.append({
            "date": ds,
            "weekday": weekday,
            "is_closed": is_closed_day or is_holiday,
            "closed_reason": ("Libur" if is_holiday else "Tutup") if (is_holiday or is_closed_day) else None,
            "bookings_count": len(bookings),
            "occupied_slots": occupied,
            "capacity": 0 if (is_closed_day or is_holiday) else total_cap_per_day,
        })
    return {"start": start, "days": days}


# ----------------- Admin -----------------
@api.get("/admin/bookings")
async def admin_bookings(
    user: dict = Depends(get_current_user),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    plate: Optional[str] = None,
):
    q = {}
    if date_from or date_to:
        q["booking_date"] = {}
        if date_from:
            q["booking_date"]["$gte"] = date_from
        if date_to:
            q["booking_date"]["$lte"] = date_to
    if status:
        q["status"] = status
    if plate:
        q["plate_number"] = plate.upper().strip()
    docs = await db.bookings.find(q, {"_id": 0}).to_list(2000)
    docs.sort(key=lambda x: (x["booking_date"], x["start_time"]))
    return docs


@api.patch("/admin/bookings/{booking_id}")
async def update_booking(booking_id: str, body: BookingUpdate, user: dict = Depends(get_current_user)):
    b = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not b:
        raise HTTPException(404, "Reservasi tidak ditemukan")
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.status:
        allowed = ["Menunggu Konfirmasi", "Dikonfirmasi", "Sedang Diproses", "Selesai", "Dibatalkan"]
        if body.status not in allowed:
            raise HTTPException(400, "Status tidak valid")
        updates["status"] = body.status
    if body.duration_hours is not None:
        updates["duration_hours"] = float(body.duration_hours)
        updates["end_time"] = add_hours_str(b["start_time"], float(body.duration_hours))
    if body.mechanic_id:
        m = await db.mechanics.find_one({"id": body.mechanic_id}, {"_id": 0})
        if not m:
            raise HTTPException(404, "Mekanik tidak ditemukan")
        updates["mechanic_id"] = m["id"]
        updates["mechanic_name"] = m["name"]
    await db.bookings.update_one({"id": booking_id}, {"$set": updates})
    updated = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    return updated


@api.get("/admin/stats")
async def admin_stats(user: dict = Depends(get_current_user)):
    today = today_local().isoformat()
    tomorrow = (today_local() + timedelta(days=1)).isoformat()
    total = await db.bookings.count_documents({})
    today_count = await db.bookings.count_documents({"booking_date": today})
    tomorrow_count = await db.bookings.count_documents({"booking_date": tomorrow})
    by_status = {}
    for s in ["Menunggu Konfirmasi", "Dikonfirmasi", "Sedang Diproses", "Selesai", "Dibatalkan"]:
        by_status[s] = await db.bookings.count_documents({"status": s})
    return {
        "total": total,
        "today": today_count,
        "tomorrow": tomorrow_count,
        "by_status": by_status,
    }


@api.post("/admin/mechanics")
async def create_mechanic(body: MechanicIn, user: dict = Depends(get_current_user)):
    m = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "status": body.status or "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.mechanics.insert_one(m.copy())
    m.pop("_id", None)
    return m


@api.patch("/admin/mechanics/{mid}")
async def update_mechanic(mid: str, body: MechanicUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Tidak ada perubahan")
    r = await db.mechanics.update_one({"id": mid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(404, "Mekanik tidak ditemukan")
    return await db.mechanics.find_one({"id": mid}, {"_id": 0})


def _remove_uploaded_photo(mid: str):
    f = MECHANIC_PHOTO_DIR / f"{mid}.jpg"
    if f.exists():
        try:
            f.unlink()
        except OSError:
            pass


@api.delete("/admin/mechanics/{mid}")
async def delete_mechanic(mid: str, user: dict = Depends(get_current_user)):
    r = await db.mechanics.delete_one({"id": mid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Mekanik tidak ditemukan")
    _remove_uploaded_photo(mid)
    return {"ok": True}


@api.post("/admin/mechanics/{mid}/photo")
async def upload_mechanic_photo(mid: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    m = await db.mechanics.find_one({"id": mid}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Mekanik tidak ditemukan")
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
        raise HTTPException(400, "Format foto harus JPG, PNG, atau WEBP")
    raw = await file.read()
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(400, "Ukuran foto maksimal 5 MB")
    try:
        from io import BytesIO
        from PIL import Image, ImageOps
        img = Image.open(BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        # flatten transparency onto brand navy background
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGBA", img.size, (10, 25, 47, 255))
            bg.alpha_composite(img)
            img = bg.convert("RGB")
        else:
            img = img.convert("RGB")
        # center-crop to square then resize
        img = ImageOps.fit(img, (PHOTO_SIZE, PHOTO_SIZE), Image.LANCZOS, centering=(0.5, 0.35))
        out_path = MECHANIC_PHOTO_DIR / f"{mid}.jpg"
        img.save(out_path, "JPEG", quality=88, optimize=True)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "File foto tidak valid atau rusak")
    version = int(datetime.now(timezone.utc).timestamp())
    photo_url = f"/api/uploads/mechanics/{mid}.jpg?v={version}"
    await db.mechanics.update_one({"id": mid}, {"$set": {"photo": photo_url}})
    return await db.mechanics.find_one({"id": mid}, {"_id": 0})


@api.delete("/admin/mechanics/{mid}/photo")
async def delete_mechanic_photo(mid: str, user: dict = Depends(get_current_user)):
    m = await db.mechanics.find_one({"id": mid}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Mekanik tidak ditemukan")
    _remove_uploaded_photo(mid)
    await db.mechanics.update_one({"id": mid}, {"$unset": {"photo": ""}})
    return await db.mechanics.find_one({"id": mid}, {"_id": 0})


@api.patch("/admin/services/{sid}")
async def update_service(sid: str, body: ServiceUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Tidak ada perubahan")
    r = await db.services.update_one({"id": sid}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(404, "Servis tidak ditemukan")
    return await db.services.find_one({"id": sid}, {"_id": 0})


@api.put("/admin/business-hours")
async def update_business_hours(body: BusinessHoursUpdate, user: dict = Depends(get_current_user)):
    try:
        if to_min(body.opening_time) >= to_min(body.closing_time):
            raise HTTPException(400, "Jam buka harus lebih awal dari jam tutup")
    except ValueError:
        raise HTTPException(400, "Format jam tidak valid")
    updates = {"opening_time": body.opening_time, "closing_time": body.closing_time}
    if body.breaks is not None:
        cleaned = []
        for br in body.breaks:
            if not (0 <= br.weekday <= 6):
                raise HTTPException(400, "Hari istirahat tidak valid")
            try:
                if to_min(br.start) >= to_min(br.end):
                    raise HTTPException(400, "Jam istirahat: mulai harus lebih awal dari selesai")
            except ValueError:
                raise HTTPException(400, "Format jam istirahat tidak valid")
            cleaned.append({"weekday": br.weekday, "start": br.start, "end": br.end, "label": (br.label or "Istirahat").strip()})
        updates["breaks"] = cleaned
    await db.settings.update_one({"key": "business_hours"}, {"$set": updates}, upsert=True)
    return await db.settings.find_one({"key": "business_hours"}, {"_id": 0})


@api.post("/admin/holidays")
async def add_holiday(body: HolidayIn, user: dict = Depends(get_current_user)):
    h = {"id": str(uuid.uuid4()), "date": body.date, "description": body.description}
    await db.holidays.insert_one(h.copy())
    h.pop("_id", None)
    return h


@api.delete("/admin/holidays/{hid}")
async def delete_holiday(hid: str, user: dict = Depends(get_current_user)):
    r = await db.holidays.delete_one({"id": hid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Holiday tidak ditemukan")
    return {"ok": True}


# ----------------- Monthly Report -----------------
INDO_MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
               "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

async def _monthly_data(year: int, month: int):
    from calendar import monthrange
    if month < 1 or month > 12:
        raise HTTPException(400, "Bulan tidak valid")
    last_day = monthrange(year, month)[1]
    date_from = f"{year:04d}-{month:02d}-01"
    date_to = f"{year:04d}-{month:02d}-{last_day:02d}"
    bookings = await db.bookings.find(
        {"booking_date": {"$gte": date_from, "$lte": date_to}}, {"_id": 0}
    ).to_list(5000)
    bookings.sort(key=lambda x: (x["booking_date"], x["start_time"]))

    total = len(bookings)
    by_status = {s: 0 for s in ["Menunggu Konfirmasi", "Dikonfirmasi", "Sedang Diproses", "Selesai", "Dibatalkan"]}
    by_service = {}
    active_total = 0
    for b in bookings:
        by_status[b["status"]] = by_status.get(b["status"], 0) + 1
        by_service[b["service_name"]] = by_service.get(b["service_name"], 0) + 1
        if b["status"] != "Dibatalkan":
            active_total += 1

    return {
        "period": {"year": year, "month": month, "label": f"{INDO_MONTHS[month-1]} {year}",
                   "from": date_from, "to": date_to},
        "total": total,
        "active_total": active_total,
        "completed_total": by_status.get("Selesai", 0),
        "by_status": by_status,
        "by_service": by_service,
        "bookings": bookings,
    }


@api.get("/admin/reports/monthly")
async def monthly_report(year: int, month: int, user: dict = Depends(get_current_user)):
    return await _monthly_data(year, month)


@api.get("/admin/reports/monthly.pdf")
async def monthly_report_pdf(
    year: int, month: int,
    token: Optional[str] = Query(None),  # allow query token for download links
    request: Request = None,
):
    # Auth: cookie OR bearer OR ?token=
    try:
        await get_current_user(request)
    except HTTPException:
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            u = await db.users.find_one({"id": payload["sub"]})
            if not u:
                raise HTTPException(401, "Invalid token")
        except Exception:
            raise HTTPException(401, "Invalid token")

    data = await _monthly_data(year, month)

    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=f"Laporan {data['period']['label']}"
    )
    styles = getSampleStyleSheet()
    brand = colors.HexColor("#0052FF")
    dark = colors.HexColor("#0A192F")
    muted = colors.HexColor("#64748B")

    title_st = ParagraphStyle("t", parent=styles["Title"], textColor=dark, fontSize=22, leading=26, spaceAfter=4)
    sub_st = ParagraphStyle("s", parent=styles["Normal"], textColor=muted, fontSize=11, spaceAfter=14)
    h2_st = ParagraphStyle("h2", parent=styles["Heading2"], textColor=dark, fontSize=13, spaceBefore=10, spaceAfter=8)
    small_st = ParagraphStyle("sm", parent=styles["Normal"], textColor=muted, fontSize=9)
    cell_st = ParagraphStyle("cell", parent=styles["Normal"], textColor=dark, fontSize=8.5, leading=10)

    elems = []
    elems.append(Paragraph(f"{WORKSHOP_NAME}", title_st))
    elems.append(Paragraph(f"Laporan Reservasi — {data['period']['label']}", sub_st))

    # Summary boxes
    summary_rows = [
        ["Total Reservasi", str(data["total"]),
         "Reservasi Selesai", str(data["completed_total"])],
        ["Reservasi Aktif *", str(data["active_total"]),
         "Periode", f"{data['period']['from']} s/d {data['period']['to']}"],
    ]
    tbl = Table(summary_rows, colWidths=[4.2 * cm, 4.2 * cm, 4.2 * cm, 4.2 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TEXTCOLOR", (0, 0), (0, -1), muted),
        ("TEXTCOLOR", (2, 0), (2, -1), muted),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    elems.append(tbl)
    elems.append(Paragraph("* Aktif = semua reservasi kecuali Dibatalkan", small_st))

    # Status breakdown
    elems.append(Paragraph("Rekap Status", h2_st))
    status_rows = [["Status", "Jumlah"]]
    for s in ["Menunggu Konfirmasi", "Dikonfirmasi", "Sedang Diproses", "Selesai", "Dibatalkan"]:
        status_rows.append([s, str(data["by_status"].get(s, 0))])
    st = Table(status_rows, colWidths=[6 * cm, 3 * cm])
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(st)

    # Service breakdown
    elems.append(Paragraph("Rekap Jenis Servis", h2_st))
    svc_rows = [["Jenis Servis", "Jumlah"]]
    for k, v in data["by_service"].items():
        svc_rows.append([k, str(v)])
    if len(svc_rows) == 1:
        svc_rows.append(["—", "0"])
    svt = Table(svc_rows, colWidths=[6 * cm, 3 * cm])
    svt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(svt)

    # Detailed table
    elems.append(Paragraph("Detail Reservasi", h2_st))
    if not data["bookings"]:
        elems.append(Paragraph("Tidak ada reservasi pada periode ini.", small_st))
    else:
        det = [["No Reservasi", "Tanggal", "Jam", "Customer", "Motor", "Servis", "Mekanik", "Status"]]
        for b in data["bookings"]:
            det.append([
                b["booking_number"],
                b["booking_date"],
                f"{b['start_time']}-{b['end_time']}",
                Paragraph(b["customer_name"], cell_st),
                Paragraph(f"{b.get('motor_type') or '-'}<br/><font size=7 color='#64748B'>{b['plate_number']}</font>", cell_st),
                b["service_name"],
                b["mechanic_name"],
                b["status"],
            ])
        dt = Table(det, colWidths=[2.8*cm, 2.1*cm, 2.1*cm, 3*cm, 2.6*cm, 2.4*cm, 2.1*cm, 2.4*cm], repeatRows=1)
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), dark),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elems.append(dt)

    elems.append(Spacer(1, 10))
    elems.append(Paragraph(f"Dicetak: {datetime.now(TZ).strftime('%d %b %Y %H:%M')} · {WORKSHOP_NAME}", small_st))

    doc.build(elems)
    buf.seek(0)
    filename = f"Laporan-{year:04d}-{month:02d}-{WORKSHOP_NAME.replace(' ', '_')}.pdf"
    return StreamingResponse(
        buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ----------------- Root -----------------
@api.get("/")
async def root():
    return {"message": "ALDI MOTOR API", "workshop": WORKSHOP_NAME}


app.include_router(api)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
