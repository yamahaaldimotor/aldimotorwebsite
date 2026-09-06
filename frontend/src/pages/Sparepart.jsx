import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import PublicHeader from "@/components/PublicHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/apiClient";
import {
  Search, Package, Cog, Fuel, Zap, CircleDot, Gauge, Shapes,
  ArrowRight, Loader2, X, Info, MessageCircle,
} from "lucide-react";

const GROUP_ICON = {
  "CVT & Transmisi": Cog,
  "Mesin & Bahan Bakar": Fuel,
  "Kelistrikan": Zap,
  "Ban": CircleDot,
  "Rem, Kemudi & Suspensi": Gauge,
  "Body & Aksesori": Shapes,
};

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

function useDebounced(value, delay = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

function CategoryCard({ cat }) {
  const hasDesc = cat.items.some((i) => i.description);
  const hasVariant = cat.items.some((i) => i.variant);
  const hasSize = cat.items.some((i) => i.size);
  const hasCapacity = cat.items.some((i) => i.capacity);
  return (
    <div
      id={`cat-${slug(cat.category)}`}
      data-testid={`sparepart-category-${slug(cat.category)}`}
      className="scroll-mt-28 overflow-hidden rounded-2xl border border-slate-200 bg-white"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
            <Package strokeWidth={1.5} className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold leading-tight">{cat.category}</h3>
            <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">{cat.group}</div>
          </div>
        </div>
        <Badge variant="secondary" className="rounded-full bg-slate-100 text-slate-600">
          {cat.items.length} varian
        </Badge>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] font-bold uppercase tracking-wider text-slate-500">
              {hasVariant && <th className="px-5 py-3">Tipe</th>}
              {hasCapacity && <th className="px-5 py-3">Kapasitas</th>}
              {hasSize && <th className="px-5 py-3">Ukuran</th>}
              <th className="px-5 py-3">Cocok untuk Motor</th>
              {hasDesc && <th className="hidden px-5 py-3 md:table-cell">Keterangan</th>}
              <th className="px-5 py-3 text-right">Harga</th>
            </tr>
          </thead>
          <tbody>
            {cat.items.map((it) => (
              <tr key={it.id} className="border-t border-slate-100 transition-colors hover:bg-blue-50/40">
                {hasVariant && <td className="px-5 py-3 font-semibold text-slate-800">{it.variant || "—"}</td>}
                {hasCapacity && <td className="px-5 py-3 text-slate-600">{it.capacity || "—"}</td>}
                {hasSize && <td className="px-5 py-3 font-medium text-slate-800">{it.size || "—"}</td>}
                <td className="px-5 py-3 font-medium text-slate-800">
                  {it.motor}
                  {hasDesc && it.description && (
                    <div className="mt-1 text-xs leading-relaxed text-slate-500 md:hidden">{it.description}</div>
                  )}
                </td>
                {hasDesc && (
                  <td className="hidden max-w-md px-5 py-3 text-xs leading-relaxed text-slate-500 md:table-cell">
                    {it.description || "—"}
                  </td>
                )}
                <td className="whitespace-nowrap px-5 py-3 text-right">
                  {it.price_prefix && (
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{it.price_prefix}</div>
                  )}
                  <span className="font-display font-semibold text-blue-700">{it.price_label}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Sparepart() {
  const [meta, setMeta] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("all");
  const dq = useDebounced(q);

  useEffect(() => {
    api.get("/spareparts/meta").then((r) => setMeta(r.data)).catch(() => setMeta(null));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params = {};
    if (dq.trim()) params.q = dq.trim();
    if (group !== "all") params.group = group;
    api.get("/spareparts", { params })
      .then((r) => { if (!cancelled) setData(r.data); })
      .catch(() => { if (!cancelled) setData({ total_items: 0, total_categories: 0, groups: [] }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [dq, group]);

  const flatCategories = useMemo(
    () => (data?.groups || []).flatMap((g) => g.categories),
    [data]
  );

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
            Informasi Sparepart
          </div>
          <h1 className="font-display text-4xl font-bold leading-[1.05] tracking-tighter md:text-6xl">
            Sparepart Original <br />
            <span className="text-blue-400">Yamaha Tersedia.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-slate-300 md:text-lg">
            Cek ketersediaan dan estimasi harga sparepart di ALDI MOTOR sesuai tipe motor Anda.
            Harga dapat berubah sewaktu-waktu — konfirmasi ke bengkel untuk kepastian stok.
          </p>

          {meta && (
            <div className="mt-8 flex flex-wrap gap-6 text-sm text-white/90">
              <div><span className="font-display text-2xl font-bold text-white">{meta.total_items}</span> <span className="text-slate-300">varian sparepart</span></div>
              <div><span className="font-display text-2xl font-bold text-white">{meta.groups.reduce((a, g) => a + g.categories.length, 0)}</span> <span className="text-slate-300">jenis sparepart</span></div>
              <div><span className="font-display text-2xl font-bold text-white">{meta.groups.length}</span> <span className="text-slate-300">kelompok</span></div>
            </div>
          )}
        </div>
      </section>

      {/* SEARCH + FILTER (sticky) */}
      <div className="sticky top-[73px] z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-3 md:px-8">
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <div className="relative w-full md:max-w-md">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Cari sparepart atau tipe motor, mis. NMAX, V-Belt, Aki…"
                className="h-11 rounded-full pl-10 pr-10"
                data-testid="sparepart-search"
              />
              {q && (
                <button
                  onClick={() => setQ("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                  aria-label="Hapus pencarian"
                  data-testid="sparepart-search-clear"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:px-0 md:pb-0">
              <button
                onClick={() => setGroup("all")}
                data-testid="group-chip-all"
                className={`shrink-0 rounded-full border px-4 py-2 text-xs font-semibold transition-colors ${group === "all" ? "border-blue-600 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-blue-300"}`}
              >
                Semua
              </button>
              {(meta?.groups || []).map((g) => {
                const Icon = GROUP_ICON[g.group] || Package;
                const active = group === g.group;
                return (
                  <button
                    key={g.group}
                    onClick={() => setGroup(active ? "all" : g.group)}
                    data-testid={`group-chip-${slug(g.group)}`}
                    className={`flex shrink-0 items-center gap-1.5 rounded-full border px-4 py-2 text-xs font-semibold transition-colors ${active ? "border-blue-600 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-blue-300"}`}
                  >
                    <Icon strokeWidth={1.5} className="h-3.5 w-3.5" /> {g.group}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* CONTENT */}
      <section className="mx-auto max-w-7xl px-4 py-10 md:px-8 md:py-14">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Sidebar quick-jump */}
          <aside className="hidden lg:col-span-3 lg:block">
            <div className="sticky top-40 space-y-5">
              {(data?.groups || []).map((g) => {
                const Icon = GROUP_ICON[g.group] || Package;
                return (
                  <div key={g.group}>
                    <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
                      <Icon strokeWidth={1.5} className="h-3.5 w-3.5 text-blue-600" /> {g.group}
                    </div>
                    <ul className="space-y-1 border-l border-slate-200 pl-3">
                      {g.categories.map((c) => (
                        <li key={c.category}>
                          <a
                            href={`#cat-${slug(c.category)}`}
                            className="block text-sm text-slate-600 transition-colors hover:text-blue-600"
                          >
                            {c.category}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </aside>

          {/* Main list */}
          <div className="lg:col-span-9">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm text-slate-600" data-testid="sparepart-result-count">
                {loading ? "Memuat…" : (
                  <>Menampilkan <span className="font-semibold text-slate-900">{data?.total_items || 0}</span> varian dalam <span className="font-semibold text-slate-900">{data?.total_categories || 0}</span> jenis sparepart{dq.trim() ? <> untuk “<span className="font-semibold text-blue-700">{dq.trim()}</span>”</> : null}</>
                )}
              </div>
              {(q || group !== "all") && (
                <Button variant="outline" size="sm" className="rounded-full" onClick={() => { setQ(""); setGroup("all"); }} data-testid="sparepart-reset">
                  Reset filter
                </Button>
              )}
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-24 text-slate-500">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Memuat data sparepart…
              </div>
            ) : flatCategories.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center" data-testid="sparepart-empty">
                <Search className="mx-auto h-8 w-8 text-slate-300" />
                <div className="mt-3 font-display text-lg font-semibold">Sparepart tidak ditemukan</div>
                <p className="mt-1 text-sm text-slate-500">Coba kata kunci lain, misalnya nama sparepart atau tipe motor.</p>
              </div>
            ) : (
              <div className="space-y-10">
                {data.groups.map((g) => {
                  const Icon = GROUP_ICON[g.group] || Package;
                  return (
                    <div key={g.group} id={`group-${slug(g.group)}`} className="scroll-mt-32">
                      <div className="mb-4 flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#0A192F] text-white">
                          <Icon strokeWidth={1.5} className="h-4 w-4" />
                        </div>
                        <h2 className="font-display text-2xl font-semibold tracking-tight">{g.group}</h2>
                        <span className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">{g.categories.length} jenis</span>
                      </div>
                      <div className="space-y-4">
                        {g.categories.map((c) => <CategoryCard key={c.category} cat={c} />)}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="mt-10 flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-5 text-sm text-slate-700">
              <Info strokeWidth={1.5} className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
              <div>
                Harga yang tercantum adalah estimasi dan dapat berubah mengikuti harga dari distributor.
                Untuk sparepart di luar daftar, silakan tanyakan langsung ke bengkel.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-white py-16">
        <div className="mx-auto max-w-7xl px-4 md:px-8">
          <div className="flex flex-col items-start justify-between gap-6 rounded-3xl bg-[#0A192F] p-8 text-white md:flex-row md:items-center md:p-12">
            <div>
              <div className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-blue-400">Butuh Penggantian Sparepart?</div>
              <h3 className="font-display text-3xl font-semibold tracking-tight">Reservasi servis, sparepart kami siapkan.</h3>
              <p className="mt-2 max-w-xl text-slate-300">Sebutkan sparepart yang dibutuhkan pada kolom keluhan saat reservasi agar mekanik dapat menyiapkannya.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to="/reservasi">
                <Button size="lg" className="rounded-full bg-blue-600 px-8 hover:bg-blue-700" data-testid="sparepart-cta-reservasi">
                  Buat Reservasi <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <a href="https://wa.me/6285657237827?text=Halo%20ALDI%20MOTOR%2C%20saya%20ingin%20menanyakan%20ketersediaan%20sparepart." target="_blank" rel="noreferrer">
                <Button size="lg" variant="outline" className="rounded-full border-white/30 bg-transparent px-8 text-white hover:bg-white/10 hover:text-white" data-testid="sparepart-cta-wa">
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
