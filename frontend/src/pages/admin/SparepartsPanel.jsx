import { useEffect, useMemo, useState } from "react";
import api, { formatApiError } from "@/lib/apiClient";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, Search, Loader2, Package, X } from "lucide-react";

const GROUPS = ["CVT & Transmisi", "Mesin & Bahan Bakar", "Kelistrikan", "Ban", "Rem, Kemudi & Suspensi", "Body & Aksesori"];
const rupiah = (n) => "Rp " + Math.round(Number(n) || 0).toLocaleString("id-ID");

const EMPTY = { category: "", group: GROUPS[0], motor: "", price: "", price_label: "", price_prefix: "", description: "", size: "", variant: "", capacity: "" };

function SparepartForm({ open, onOpenChange, initial, categories, onSaved }) {
  const isEdit = !!initial?.id;
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [showMore, setShowMore] = useState(false);

  useEffect(() => {
    if (open) {
      const f = { ...EMPTY, ...(initial || {}) };
      f.price = initial?.price ?? "";
      // hanya isi price_label kustom jika berbeda dengan format otomatis
      f.price_label = initial?.price_label && initial.price_label !== rupiah(initial.price) ? initial.price_label : "";
      setForm(f);
      setShowMore(!!(initial?.description || initial?.size || initial?.variant || initial?.capacity || initial?.price_prefix || f.price_label));
    }
  }, [open, initial]);

  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  const submit = async () => {
    if (!form.category.trim() || !form.motor.trim() || !form.group) {
      toast.error("Nama sparepart, kelompok, dan tipe motor wajib diisi"); return;
    }
    const priceNum = form.price === "" ? null : Number(form.price);
    if (priceNum === null || isNaN(priceNum) || priceNum < 0) { toast.error("Harga harus berupa angka"); return; }
    const payload = {
      category: form.category.trim(),
      group: form.group,
      motor: form.motor.trim(),
      price: priceNum,
      price_label: form.price_label?.trim() || null,
      price_prefix: form.price_prefix?.trim() || "",
      description: form.description?.trim() || "",
      size: form.size?.trim() || "",
      variant: form.variant?.trim() || "",
      capacity: form.capacity?.trim() || "",
    };
    setSaving(true);
    try {
      if (isEdit) {
        await api.patch(`/admin/spareparts/${initial.id}`, payload);
        toast.success("Sparepart diperbarui");
      } else {
        await api.post("/admin/spareparts", payload);
        toast.success("Sparepart ditambahkan");
      }
      onSaved();
      onOpenChange(false);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="sparepart-form-dialog">
        <DialogHeader>
          <DialogTitle className="font-display">{isEdit ? "Edit Sparepart" : "Tambah Sparepart"}</DialogTitle>
          <DialogDescription>Isi data sparepart. Harga akan diformat otomatis ke Rupiah.</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Label>Nama Sparepart</Label>
            <Input
              list="sparepart-categories"
              value={form.category}
              onChange={(e) => set("category", e.target.value)}
              placeholder="mis. V-Belt, Aki, Filter Oli"
              className="mt-1.5"
              data-testid="sp-category"
            />
            <datalist id="sparepart-categories">
              {categories.map((c) => <option key={c} value={c} />)}
            </datalist>
          </div>
          <div>
            <Label>Kelompok</Label>
            <Select value={form.group} onValueChange={(v) => set("group", v)}>
              <SelectTrigger className="mt-1.5" data-testid="sp-group"><SelectValue /></SelectTrigger>
              <SelectContent>{GROUPS.map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <Label>Harga (Rp)</Label>
            <Input type="number" min="0" step="500" value={form.price} onChange={(e) => set("price", e.target.value)} placeholder="150000" className="mt-1.5" data-testid="sp-price" />
          </div>
          <div className="sm:col-span-2">
            <Label>Cocok untuk Motor</Label>
            <Input value={form.motor} onChange={(e) => set("motor", e.target.value)} placeholder="mis. NMAX 155, Aerox 155" className="mt-1.5" data-testid="sp-motor" />
          </div>

          <button type="button" onClick={() => setShowMore(!showMore)} className="text-left text-xs font-semibold text-blue-600 hover:underline sm:col-span-2" data-testid="sp-toggle-more">
            {showMore ? "Sembunyikan detail tambahan" : "Tampilkan detail tambahan (tipe, ukuran, keterangan, dll.)"}
          </button>

          {showMore && (
            <>
              <div>
                <Label>Tipe / Varian</Label>
                <Input value={form.variant} onChange={(e) => set("variant", e.target.value)} placeholder="mis. NGK CPR8EA-9" className="mt-1.5" data-testid="sp-variant" />
              </div>
              <div>
                <Label>Kapasitas</Label>
                <Input value={form.capacity} onChange={(e) => set("capacity", e.target.value)} placeholder="mis. 12V 5Ah" className="mt-1.5" data-testid="sp-capacity" />
              </div>
              <div>
                <Label>Ukuran</Label>
                <Input value={form.size} onChange={(e) => set("size", e.target.value)} placeholder="mis. 110/70-13" className="mt-1.5" data-testid="sp-size" />
              </div>
              <div>
                <Label>Awalan Harga</Label>
                <Input value={form.price_prefix} onChange={(e) => set("price_prefix", e.target.value)} placeholder="mis. Mulai dari" className="mt-1.5" data-testid="sp-price-prefix" />
              </div>
              <div className="sm:col-span-2">
                <Label>Label Harga Kustom <span className="font-normal text-slate-400">(opsional, mis. rentang)</span></Label>
                <Input value={form.price_label} onChange={(e) => set("price_label", e.target.value)} placeholder="mis. Rp 100.000 – Rp 150.000" className="mt-1.5" data-testid="sp-price-label" />
              </div>
              <div className="sm:col-span-2">
                <Label>Keterangan</Label>
                <Textarea value={form.description} onChange={(e) => set("description", e.target.value)} rows={3} placeholder="Deskripsi singkat" className="mt-1.5" data-testid="sp-description" />
              </div>
            </>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-full">Batal</Button>
          <Button onClick={submit} disabled={saving} className="rounded-full bg-blue-600 hover:bg-blue-700" data-testid="sp-submit">
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {isEdit ? "Simpan Perubahan" : "Tambah"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function SparepartsPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [savingPriceId, setSavingPriceId] = useState(null);

  const load = async () => {
    setLoading(true);
    try { setItems((await api.get("/admin/spareparts")).data); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const categories = useMemo(() => [...new Set(items.map((i) => i.category))], [items]);

  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    return items.filter((i) =>
      (group === "all" || i.group === group) &&
      (!ql || i.category.toLowerCase().includes(ql) || i.motor.toLowerCase().includes(ql) || (i.variant || "").toLowerCase().includes(ql))
    );
  }, [items, q, group]);

  // kelompokkan per kategori untuk tampilan
  const grouped = useMemo(() => {
    const map = new Map();
    for (const it of filtered) {
      if (!map.has(it.category)) map.set(it.category, { category: it.category, group: it.group, items: [] });
      map.get(it.category).items.push(it);
    }
    return [...map.values()];
  }, [filtered]);

  const updatePrice = async (it, value) => {
    const v = Number(value);
    if (isNaN(v) || v < 0 || v === it.price) return;
    setSavingPriceId(it.id);
    try {
      await api.patch(`/admin/spareparts/${it.id}`, { price: v, price_label: null });
      toast.success(`Harga ${it.category} · ${it.motor} diperbarui`);
      load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSavingPriceId(null); }
  };

  const remove = async (it) => {
    if (!window.confirm(`Hapus ${it.category} untuk ${it.motor}?`)) return;
    try { await api.delete(`/admin/spareparts/${it.id}`); toast.success("Sparepart dihapus"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="space-y-4" data-testid="admin-spareparts">
      <Card className="border-slate-200 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex flex-1 flex-col gap-3 md:flex-row md:items-end">
            <div className="flex-1 md:max-w-sm">
              <Label className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Cari</Label>
              <div className="relative mt-2">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nama sparepart / tipe motor" className="pl-9" data-testid="sp-search" />
                {q && <button onClick={() => setQ("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"><X className="h-4 w-4" /></button>}
              </div>
            </div>
            <div>
              <Label className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Kelompok</Label>
              <Select value={group} onValueChange={setGroup}>
                <SelectTrigger className="mt-2 w-56" data-testid="sp-filter-group"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Semua Kelompok</SelectItem>
                  {GROUPS.map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button onClick={() => { setEditing(null); setFormOpen(true); }} className="rounded-full bg-blue-600 hover:bg-blue-700" data-testid="add-sparepart-btn">
            <Plus className="mr-2 h-4 w-4" /> Tambah Sparepart
          </Button>
        </div>
        <div className="mt-3 text-xs text-slate-500" data-testid="sp-count">
          {loading ? "Memuat…" : `${filtered.length} varian · ${grouped.length} jenis sparepart`}
        </div>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Memuat…</div>
      ) : grouped.length === 0 ? (
        <Card className="p-10 text-center text-sm text-slate-500">Tidak ada sparepart yang cocok.</Card>
      ) : (
        <div className="space-y-4">
          {grouped.map((g) => (
            <Card key={g.category} className="overflow-hidden border-slate-200" data-testid={`sp-cat-${g.category}`}>
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/60 px-5 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600"><Package strokeWidth={1.5} className="h-4 w-4" /></div>
                  <div>
                    <div className="font-display font-semibold">{g.category}</div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{g.group}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="rounded-full bg-white">{g.items.length} varian</Badge>
                  <Button
                    variant="outline" size="sm" className="rounded-full"
                    onClick={() => { setEditing({ category: g.category, group: g.group }); setFormOpen(true); }}
                    data-testid={`sp-add-variant-${g.category}`}
                  >
                    <Plus className="mr-1 h-3.5 w-3.5" /> Varian
                  </Button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      <th className="px-5 py-2">Motor</th>
                      <th className="px-5 py-2">Detail</th>
                      <th className="px-5 py-2 text-right">Harga (Rp)</th>
                      <th className="px-5 py-2 text-right">Label Tampil</th>
                      <th className="px-3 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.items.map((it) => (
                      <tr key={it.id} className="border-t border-slate-100" data-testid={`sp-row-${it.id}`}>
                        <td className="px-5 py-2 font-medium text-slate-800">{it.motor}</td>
                        <td className="px-5 py-2 text-xs text-slate-500">
                          {[it.variant, it.capacity, it.size].filter(Boolean).join(" · ") || (it.description ? it.description.slice(0, 60) + (it.description.length > 60 ? "…" : "") : "—")}
                        </td>
                        <td className="px-5 py-2 text-right">
                          <div className="inline-flex items-center gap-1">
                            {savingPriceId === it.id && <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-400" />}
                            <Input
                              type="number" min="0" step="500" defaultValue={it.price ?? 0}
                              key={`${it.id}-${it.price}`}
                              className="h-8 w-32 text-right"
                              onBlur={(e) => updatePrice(it, e.target.value)}
                              onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); }}
                              data-testid={`sp-price-input-${it.id}`}
                            />
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-5 py-2 text-right font-display font-semibold text-blue-700">
                          {it.price_prefix ? <span className="mr-1 text-[10px] font-bold uppercase text-slate-400">{it.price_prefix}</span> : null}
                          {it.price_label}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="icon" title="Edit" onClick={() => { setEditing(it); setFormOpen(true); }} data-testid={`sp-edit-${it.id}`}>
                              <Pencil className="h-4 w-4 text-slate-600" />
                            </Button>
                            <Button variant="ghost" size="icon" title="Hapus" onClick={() => remove(it)} data-testid={`sp-delete-${it.id}`}>
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ))}
        </div>
      )}

      <SparepartForm open={formOpen} onOpenChange={setFormOpen} initial={editing} categories={categories} onSaved={load} />
    </div>
  );
}
