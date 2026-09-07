import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import PublicHeader from "@/components/PublicHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/apiClient";
import {
  Search, X, Loader2, Wrench, Cog, Settings2, Info, ArrowRight,
  MessageCircle, Bike, Clock, Package,
} from "lucide-react";

const rupiah = (n) => (n == null ? "—" : "Rp " + Math.round(Number(n)).toLocaleString("id-ID"));
const TYPE_ICON = { ringan: Wrench, berat: Cog, overhaul: Settings2 };
const TYPE_COLOR = {
  ringan: "bg-blue-50 text-blue-700 border-blue-100",
  berat: "bg-indigo-50 text-indigo-700 border-indigo-100",
  overhaul: "bg-slate-100 text-slate-800 border-slate-200",
};
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

function useDebounced(value, delay = 250) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), delay); return () => clearTimeout(t); }, [value, delay]);
  return v;
}

export default function BiayaServis() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("all");
  const dq = useDebounced(q);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params = {};
    if (dq.trim()) params.q = dq.trim();
    if (category !== "all") params.category = category;
    api.get("/service-prices", { params })
      .then((r) => { if (!cancelled) setData(r.data); })
      .catch(() => { if (!cancelled) setData({ total_motors: 0, types: [], categories: [], summary: {}, all_categories: [] }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [dq, category]);

  const types = useMemo(() => data?.types || [], [data]);

  return (
    <div className="min-h-screen bg-slate-50">
      <PublicHeader />

      {/* HERO */}
      <section className="relative overflow-hidden bg-[#0A192F] text-white">
        <div className="pointer-events-none absolute -left-32 top-0 h-96 w-96 rounded-full bg-blue-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -right-32 bottom-0 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl" />
        <div className="relative mx-auto max-w-7xl px-4 py-16 md:px-8 md:py-20">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs uppercase tracking-[0.2em] text-blue-200 backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
            Informasi Biaya Servis
          </div>
          <h1 className="font-display text-4xl font-bold leading-[1.05] tracking-tighter md:text-6xl">
            Biaya Jasa Servis <br />
            <span className="text-blue-400">Transparan & Jelas.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-slate-300 md:text-lg">
            Estimasi biaya jasa Servis Ringan, Servis Berat, dan Overhaul untuk setiap tipe motor Yamaha.
            Belum termasuk sparepart dan oli.
          </p>

          {/* Type summary cards */}
          {data && types.length > 0 && (
            <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3" data-testid="type-summary">
              {types.map((t) => {
                const Icon = TYPE_ICON[t.key] || Wrench;
                const sm = data.summary?.[t.key] || {};
                return (
                  <div key={t.key} className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/20 text-blue-300">
                        <Icon strokeWidth={1.5} className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="font-display text-lg font-semibold leading-tight">{t.name}</div>
                        {t.duration_hours && (
                          <div className="flex items-center gap-1 text-xs text-slate-300">
                            <Clock className="h-3 w-3" /> Estimasi {t.duration_hours % 1 === 0 ? t.duration_hours : t.duration_hours.toFixed(1)} jam
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="mt-4 text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Mulai dari</div>
                    <div className="font-display text-2xl font-bold text-white">{rupiah(sm.min)}</div>
                    <div className="text-xs text-slate-400">s/d {rupiah(sm.max)}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* FILTER BAR */}
      <div className="sticky top-[73px] z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-3 md:px-8">
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <div className="relative w-full md:max-w-md">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Cari tipe motor, mis. NMAX, Vixion, Mio…"
                className="h-11 rounded-full pl-10 pr-10"
                data-testid="biaya-search"
              />
              {q && (
                <button onClick={() => setQ("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700" aria-label="Hapus pencarian" data-testid="biaya-search-clear">
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:px-0 md:pb-0">
              <button
                onClick={() => setCategory("all")}
                data-testid="cat-chip-all"
                className={`shrink-0 rounded-full border px-4 py-2 text-xs font-semibold transition-colors ${category === "all" ? "border-blue-600 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-blue-300"}`}
              >
                Semua Kategori
              </button>
              {(data?.all_categories || []).map((c) => {
                const active = category === c;
                return (
                  <button
                    key={c}
                    onClick={() => setCategory(active ? "all" : c)}
                    data-testid={`cat-chip-${slug(c)}`}
                    className={`flex shrink-0 items-center gap-1.5 rounded-full border px-4 py-2 text-xs font-semibold transition-colors ${active ? "border-blue-600 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-blue-300"}`}
                  >
                    <Bike strokeWidth={1.5} className="h-3.5 w-3.5" /> {c}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* CONTENT */}
      <section className="mx-auto max-w-7xl px-4 py-10 md:px-8 md:py-14">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm text-slate-600" data-testid="biaya-result-count">
            {loading ? "Memuat…" : (
              <>Menampilkan <span className="font-semibold text-slate-900">{data?.total_motors || 0}</span> tipe motor dalam <span className="font-semibold text-slate-900">{data?.categories?.length || 0}</span> kategori{dq.trim() ? <> untuk “<span className="font-semibold text-blue-700">{dq.trim()}</span>”</> : null}</>
            )}
          </div>
          {(q || category !== "all") && (
            <Button variant="outline" size="sm" className="rounded-full" onClick={() => { setQ(""); setCategory("all"); }} data-testid="biaya-reset">
              Reset filter
            </Button>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24 text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Memuat biaya servis…</div>
        ) : !data || data.categories.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center" data-testid="biaya-empty">
            <Search className="mx-auto h-8 w-8 text-slate-300" />
            <div className="mt-3 font-display text-lg font-semibold">Tipe motor tidak ditemukan</div>
            <p className="mt-1 text-sm text-slate-500">Coba kata kunci lain atau hubungi bengkel untuk tipe motor di luar daftar.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {data.categories.map((cat) => (
              <div
                key={cat.category}
                id={`cat-${slug(cat.category)}`}
                data-testid={`biaya-category-${slug(cat.category)}`}
                className="overflow-hidden rounded-2xl border border-slate-200 bg-white"
              >
                <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                      <Bike strokeWidth={1.5} className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="font-display text-lg font-semibold leading-tight">{cat.category}</h3>
                      <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Kategori Motor</div>
                    </div>
                  </div>
                  <Badge variant="secondary" className="rounded-full bg-slate-100 text-slate-600">{cat.items.length} tipe</Badge>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-[11px] font-bold uppercase tracking-wider text-slate-500">
                        <th className="px-5 py-3">Tipe Motor</th>
                        {types.map((t) => (
                          <th key={t.key} className="px-3 py-3 text-right">
                            <span className="hidden sm:inline">{t.name}</span>
                            <span className="sm:hidden">{t.key === "ringan" ? "Ringan" : t.key === "berat" ? "Berat" : "Overhaul"}</span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {cat.items.map((it) => (
                        <tr key={it.id} className="border-t border-slate-100 transition-colors hover:bg-blue-50/40" data-testid={`biaya-row-${slug(it.motor)}`}>
                          <td className="px-5 py-3 font-medium text-slate-800">{it.motor}</td>
                          {types.map((t) => (
                            <td key={t.key} className="whitespace-nowrap px-3 py-3 text-right">
                              <span className={`inline-block rounded-md border px-2 py-0.5 font-display text-sm font-semibold ${TYPE_COLOR[t.key]}`}>
                                {rupiah(it.prices[t.key])}
                              </span>
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Notes */}
        <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-5 text-sm text-slate-700">
            <Info strokeWidth={1.5} className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
            <div>
              <div className="font-semibold text-slate-900">Biaya jasa saja</div>
              {data?.note || "Harga di atas adalah biaya jasa servis, belum termasuk sparepart dan oli. Harga dapat berubah sewaktu-waktu."}
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-700">
            <Package strokeWidth={1.5} className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
            <div>
              <div className="font-semibold text-slate-900">Butuh estimasi sparepart?</div>
              Cek harga sparepart original Yamaha sesuai tipe motor Anda di{" "}
              <Link to="/sparepart" className="font-semibold text-blue-600 underline-offset-4 hover:underline" data-testid="biaya-link-sparepart">halaman Sparepart</Link>.
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-white py-16">
        <div className="mx-auto max-w-7xl px-4 md:px-8">
          <div className="flex flex-col items-start justify-between gap-6 rounded-3xl bg-[#0A192F] p-8 text-white md:flex-row md:items-center md:p-12">
            <div>
              <div className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-blue-400">Sudah tahu biayanya?</div>
              <h3 className="font-display text-3xl font-semibold tracking-tight">Reservasi sekarang, datang tanpa antre.</h3>
              <p className="mt-2 max-w-xl text-slate-300">Pilih jenis servis dan jadwal yang tersedia. Mekanik kami siap menangani motor Anda tepat waktu.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to="/reservasi">
                <Button size="lg" className="rounded-full bg-blue-600 px-8 hover:bg-blue-700" data-testid="biaya-cta-reservasi">
                  Buat Reservasi <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <a href="https://wa.me/6285657237827?text=Halo%20ALDI%20MOTOR%2C%20saya%20ingin%20menanyakan%20biaya%20servis." target="_blank" rel="noreferrer">
                <Button size="lg" variant="outline" className="rounded-full border-white/30 bg-transparent px-8 text-white hover:bg-white/10 hover:text-white" data-testid="biaya-cta-wa">
                  <MessageCircle className="mr-2 h-4 w-4" /> Tanya via WhatsApp
                </Button>
              </a>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
