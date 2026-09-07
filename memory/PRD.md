# ALDI MOTOR - Sistem Reservasi Servis Motor

## Problem Statement
Website reservasi/booking servis motor untuk bengkel ALDI MOTOR. Customer bisa memilih tanggal, jam, jenis servis. Sistem mengalokasikan mekanik otomatis dari 5 mekanik aktif. Ada dashboard admin untuk mengelola reservasi.

## Architecture
- Backend: FastAPI + MongoDB (motor async), JWT auth, timezone Asia/Makassar
- Frontend: React 19 + Vite/CRA + Tailwind + Shadcn UI + react-day-picker + sonner
- Auth: JWT Bearer token (localStorage) — admin only
- Notifikasi: wa.me link fallback (bukan API)

## Personas
- **Customer**: pemilik motor yang butuh booking sebelum ke bengkel
- **Admin**: pemilik/staf bengkel yang mengelola reservasi

## Core Requirements
1. Reservasi window H+1 s/d H+7, tutup Minggu + hari libur khusus
2. Jam operasional Senin–Sabtu 08:30–16:30, Jumat istirahat 11:00–14:00 (bisa diubah admin, termasuk jam istirahat per hari)
3. Servis: Ringan 1j, Berat 2j, Overhaul 4j, Request 1j (custom)
4. 5 mekanik (bisa CRUD), otomatis alokasi
5. Slot: max 5 customer/jam (= 5 mekanik). Sistem mencegah double booking
6. Nomor reservasi format RSV-YYYYMMDD-NNNN

## Implemented (v1 - 2026-08-29)
- Backend endpoints (18/18 passed):
  - Auth: login/logout/me
  - Public: /services, /mechanics, /business-hours (dengan today/min/max), /holidays, /availability, /bookings
  - Admin: /admin/bookings (list + PATCH status/mechanic/duration), /admin/stats, /admin/mechanics CRUD, /admin/services PATCH, /admin/business-hours PUT, /admin/holidays POST/DELETE
- Frontend:
  - Landing: Hero + 4 service cards + Cara Reservasi + Kontak (blue+white premium theme, Outfit/Manrope fonts)
  - Reservasi 4-step flow dengan progress stepper, calendar timezone-aware, slot capacity badges
  - Admin login (JWT)
  - Admin Dashboard: overview stats, bookings list dengan action buttons (Konfirmasi, Mulai Servis, Selesaikan, Batalkan), mekanik CRUD, pengaturan jam operasional/durasi/hari libur

## Update 2026-09-06 (v1.1)
- Semua fitur harga/pendapatan dihapus (sistem fokus reservasi, tanpa payment): field `price` dihapus dari services & bookings (migrasi $unset saat startup), laporan bulanan memakai `active_total`/`completed_total` (tanpa revenue), PDF tanpa kolom Harga, UI admin tanpa input/tampilan harga.
- Nomor WA konfirmasi bengkel diganti ke 6285657237827 (backend/.env WORKSHOP_WHATSAPP + default di server.py + teks kontak di Landing).

## Update 2026-09-06 (v1.2) - Profil Mekanik
- 5 mekanik memakai nama & foto asli: Andi Muh Wahidin, Ahmad Balla, Kasim, Ansar, Muh Risal. Foto diproses (background merah -> gradien biru navy/brand) dan disimpan di frontend/public/mechanics/*.jpg; field `photo` di koleksi mechanics (MechanicIn/MechanicUpdate mendukung photo).
- Seed: migrasi otomatis nama placeholder "Mekanik N" -> nama asli + foto, dan sinkronisasi mechanic_name pada booking.
- Landing: section baru "Tim Mekanik" (#mekanik, bg navy) di bawah Layanan, data dari GET /api/mechanics (hanya status active). Link nav "Tim Mekanik" ditambahkan. Admin tab Mekanik menampilkan avatar foto.

## Update 2026-09-06 (v1.3) - Upload Foto Mekanik
- POST /api/admin/mechanics/{mid}/photo (multipart 'file', jpg/png/webp, max 5MB) -> crop persegi 480x480 JPEG, disimpan di backend/uploads/mechanics/{mid}.jpg, disajikan via StaticFiles /api/uploads. DELETE .../photo menghapus foto. Hapus mekanik ikut menghapus file.
- Admin tab Mekanik: klik foto -> pilih file -> upload dengan progress; tombol "Hapus Foto". Foto tampil di section Tim Mekanik beranda.

## Update 2026-09-06 (v1.4) - Halaman Sparepart
- Data dari "Data untuk web.xlsx" sheet Sparepart diparse -> backend/spareparts_seed.json (268 item, 36 jenis, 6 kelompok: CVT & Transmisi, Mesin & Bahan Bakar, Kelistrikan, Ban, Rem/Kemudi/Suspensi, Body & Aksesori). Seed ke koleksi `spareparts` saat startup jika kosong.
- API publik: GET /api/spareparts?q=&group=&category= (grouped), GET /api/spareparts/meta.
- Frontend: halaman /sparepart (hero, search debounce, chip kelompok, sidebar quick-jump, tabel per jenis dengan kolom dinamis: tipe/kapasitas/ukuran/keterangan/harga, CTA reservasi + WA). Link "Sparepart" di header, tombol "Info Sparepart" di hero beranda, banner sparepart di bawah Layanan.
- Harga sparepart DITAMPILKAN (sesuai Sheet4 spreadsheet: "Harga sparepart dan oli ditampilkan") — berbeda dengan harga jasa servis yang sudah dihapus.
- Sheet lain di spreadsheet belum dipakai: Yamalube (oli), Jadwal Operasional (08.30-16.30, Jumat istirahat 11.00-14.00), Data Mekanik (trained at / date of issue), Data Service (biaya jasa overhaul per tipe motor), Visi&Misi.

## Update 2026-09-06 (v1.5) - Jadwal Baru & Kelola Sparepart
- Jadwal: settings.business_hours {opening_time 08:30, closing_time 16:30, closed_days [6], breaks:[{weekday,start,end,label}], schedule_version 2}. Helper day_windows/slot_starts/fits_windows di server.py: slot per jam dari awal tiap sesi; slot yang melewati akhir sesi status "closed". Jumat (ringan): 08:30, 09:30, 14:00, 15:00. Kalender admin harian punya kolom "Istirahat". Admin Pengaturan: editor jam istirahat (hari, mulai, selesai, keterangan). Beranda & Reservasi menampilkan jadwal baru.
- Sparepart admin: tab "Sparepart" di dashboard (frontend/src/pages/admin/SparepartsPanel.jsx) — cari/filter, tambah (dialog dengan detail opsional), edit harga inline (blur/Enter), edit lengkap, hapus, tambah varian per jenis. API /api/admin/spareparts (GET/POST), /api/admin/spareparts/{id} (PATCH/DELETE).

## Update 2026-09-07 (v1.6) - Halaman Biaya Servis
- Data sheet "Data Service Ringan dan Berat" dirapikan -> backend/service_prices_seed.json (31 tipe motor, 8 kategori: Moped, Matic, Matic Classy, Matic Premium, Sport, Matic Premium 1, Matic Premium 2, Sport Premium; kolom ringan/berat/overhaul). Asumsi karena data kosong di sheet: Lexi LX 155 & NMAX Neo servis ringan = Rp100.000 (sama kategori). Seed ke koleksi `service_prices` jika kosong.
- API publik GET /api/service-prices?q=&category= (+ summary min/max, types dari koleksi services untuk durasi).
- Frontend: halaman /biaya-servis (hero dengan ringkasan 3 jenis servis, search tipe motor, chip kategori, tabel per kategori 3 kolom harga, catatan "biaya jasa belum termasuk sparepart/oli", CTA). Link "Biaya Servis" di header; link "Lihat biaya servis per tipe motor" di section Layanan beranda.
- Catatan: harga jasa servis hanya informasi; alur reservasi tetap tanpa harga/payment.

## Backlog (P1/P2)
- P1: Kalender view mingguan/bulanan untuk admin
- P1: Notifikasi Twilio WhatsApp API (kirim otomatis, bukan wa.me link)
- P2: Reminder H-1 otomatis
- P2: Riwayat servis per nomor polisi (customer history)
- P2: Export laporan reservasi bulanan ke CSV/PDF
- P2: Multi-cabang (multi-tenant)

## Credentials
Admin: username `adminaldimotor` / password `aldimotorjaya` (dari backend/.env ADMIN_USERNAME/ADMIN_PASSWORD)

## Import dari GitHub (2026-09-06)
- Project di-import ulang dari GitHub. File `.env` tidak ikut (gitignored) sehingga dibuat ulang:
  - backend/.env: MONGO_URL, DB_NAME=aldi_motor_db, JWT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD, WORKSHOP_WHATSAPP, WORKSHOP_NAME
  - frontend/.env: REACT_APP_BACKEND_URL, WDS_SOCKET_PORT=443
- Dependency backend (pip) & frontend (yarn) diinstall, kedua service berjalan normal.
- Fitur yang sudah ada sejak commit terakhir: export laporan PDF (reportlab), tombol simpan bukti reservasi, konfirmasi WA ke nomor bengkel.
