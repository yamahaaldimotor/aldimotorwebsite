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
2. Jam operasional Senin–Sabtu 08:00–16:00 (bisa diubah admin)
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
