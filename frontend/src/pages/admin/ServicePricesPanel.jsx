import { useEffect, useMemo, useState } from "react";
import api, { formatApiError } from "@/lib/apiClient";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Plus, Trash2, Search, Loader2, Bike, X, Pencil } from "lucide-react";

const TYPES = [
  { key: "ringan", label: "Servis Ringan", short: "Ringan" },
  { key: "berat", label: "Servis Berat", short: "Berat" },
  { key: "overhaul", label: "Overhaul", short: "Overhaul" },
];
const rupiah = (n) => (n == null ? "—" : "Rp " + Math.round(Number(n)).toLocaleString("id-ID"));

function PriceCell({ item, typeKey, onSave, saving }) {
  const [val, setVal] = useState(item[typeKey] ?? "");
  useEffect(() => { setVal(item[typeKey] ?? ""); }, [item, typeKey]);
  const commit = () => {
    if (val === "" || val === null) return;
    const n = Number(val);
    if (isNaN(n) || n < 0) { toast.error("Harga harus angka positif"); setVal(item[typeKey] ?? ""); return; }
    if (n !== Number(item[typeKey])) onSave(item, typeKey, n);
  };
  const dirty = val !== "" && Number(val) !== Number(item[typeKey]);
  return (
    <div className="flex flex-col items-end gap-0.5">
      <div className="relative">
        {saving && <Loader2 className="absolute -left-5 top-2 h-3.5 w-3.5 animate-spin text-slate-400" />}
        <Input
          type="number" min="0" step="500"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur(); if (e.key === "Escape") setVal(item[typeKey] ?? ""); }}
          className={`h-8 w-28 text-right ${dirty ? "border-amber-400 bg-amber-50" : ""}`}
          data-testid={`price-${typeKey}-${item.id}`}
        />
      </div>
      <span className="text-[10px] text-slate-400">{rupiah(item[typeKey])}</span>
    </div>
  );
}

function MotorForm({ open, onOpenChange, initial, categories, onSaved }) {
  const isEdit = !!initial?.id;
  const [form, setForm] = useState({ category: "", motor: "", ringan: "", berat: "", overhaul: "" });
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) setForm({
      category: initial?.category || "",
      motor: initial?.motor || "",
      ringan: initial?.ringan ?? "",
      berat: initial?.berat ?? "",
      overhaul: initial?.overhaul ?? "",
    });
  }, [open, initial]);
  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));
  const submit = async () => {
    if (!form.category.trim() || !form.motor.trim()) { toast.error("Kategori dan tipe motor wajib diisi"); return; }
    const payload = { category: form.category.trim(), motor: form.motor.trim() };
    for (const t of TYPES) {
      if (form[t.key] !== "" && form[t.key] !== null) {
        const n = Number(form[t.key]);
        if (isNaN(n) || n < 0) { toast.error(`Harga ${t.label} tidak valid`); return; }
        payload[t.key] = n;
      }
    }
    setSaving(true);
    try {
      if (isEdit) { await api.patch(`/admin/service-prices/${initial.id}`, payload); toast.success("Data diperbarui"); }
      else { await api.post("/admin/service-prices", payload); toast.success("Tipe motor ditambahkan"); }
      onSaved(); onOpenChange(false);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSaving(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="service-price-form">
        <DialogHeader>
          <DialogTitle className="font-display">{isEdit ? "Edit Tipe Motor" : "Tambah Tipe Motor"}</DialogTitle>
          <DialogDescription>Biaya jasa servis per tipe motor (Rp). Kosongkan jika belum ada harga.</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label>Kategori Motor</Label>
            <Input list="sp-cats" value={form.category} onChange={(e) => set("category", e.target.value)} placeholder="mis. Matic Premium" className="mt-1.5" data-testid="spf-category" />
            <datalist id="sp-cats">{categories.map((c) => <option key={c} value={c} />)}</datalist>
          </div>
          <div>
            <Label>Tipe Motor</Label>
            <Input value={form.motor} onChange={(e) => set("motor", e.target.value)} placeholder="mis. NMAX Neo" className="mt-1.5" data-testid="spf-motor" />
          </div>
          {TYPES.map((t) => (
            <div key={t.key} className={t.key === "overhaul" ? "sm:col-span-2" : ""}>
              <Label>{t.label} (Rp)</Label>
              <Input type="number" min="0" step="500" value={form[t.key]} onChange={(e) => set(t.key, e.target.value)} placeholder="0" className="mt-1.5" data-testid={`spf-${t.key}`} />
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-full">Batal</Button>
          <Button onClick={submit} disabled={saving} className="rounded-full bg-blue-600 hover:bg-blue-700" data-testid="spf-submit">
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{isEdit ? "Simpan" : "Tambah"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function ServicePricesPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [savingKey, setSavingKey] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = async () => {
    setLoading(true);
    try { setItems((await api.get("/admin/service-prices")).data); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const categories = useMemo(() => [...new Set(items.map((i) => i.category))], [items]);
  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    return items.filter((i) => !ql || i.motor.toLowerCase().includes(ql) || i.category.toLowerCase().includes(ql));
  }, [items, q]);
  const grouped = useMemo(() => {
    const map = new Map();
    for (const it of filtered) {
      if (!map.has(it.category)) map.set(it.category, []);
      map.get(it.category).push(it);
    }
    return [...map.entries()];
  }, [filtered]);

  const savePrice = async (item, key, value) => {
    setSavingKey(`${item.id}-${key}`);
    try {
      const r = await api.patch(`/admin/service-prices/${item.id}`, { [key]: value });
      setItems((prev) => prev.map((i) => (i.id === item.id ? r.data : i)));
      toast.success(`${item.motor} · ${TYPES.find((t) => t.key === key).label} → ${rupiah(value)}`);
    } catch (e) { toast.error(formatApiError(e)); load(); }
    finally { setSavingKey(null); }
  };

  const remove = async (item) => {
    if (!window.confirm(`Hapus ${item.motor} (${item.category})?`)) return;
    try { await api.delete(`/admin/service-prices/${item.id}`); toast.success("Tipe motor dihapus"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="space-y-4" data-testid="admin-service-prices">
      <Card className="border-slate-200 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="flex-1 md:max-w-sm">
            <Label className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Cari Tipe Motor</Label>
            <div className="relative mt-2">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="mis. NMAX, Vixion" className="pl-9" data-testid="sp-price-search" />
              {q && <button onClick={() => setQ("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"><X className="h-4 w-4" /></button>}
            </div>
          </div>
          <Button onClick={() => { setEditing(null); setFormOpen(true); }} className="rounded-full bg-blue-600 hover:bg-blue-700" data-testid="add-service-price-btn">
            <Plus className="mr-2 h-4 w-4" /> Tambah Tipe Motor
          </Button>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Ubah harga langsung di kolom, lalu tekan <kbd className="rounded border bg-slate-50 px-1">Enter</kbd> atau klik di luar untuk menyimpan. Perubahan langsung tampil di halaman Biaya Servis publik.
        </p>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Memuat…</div>
      ) : grouped.length === 0 ? (
        <Card className="p-10 text-center text-sm text-slate-500">Tidak ada tipe motor yang cocok.</Card>
      ) : (
        <div className="space-y-4">
          {grouped.map(([category, rows]) => (
            <Card key={category} className="overflow-hidden border-slate-200" data-testid={`sp-price-cat-${category}`}>
              <div className="flex items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/60 px-5 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600"><Bike strokeWidth={1.5} className="h-4 w-4" /></div>
                  <div>
                    <div className="font-display font-semibold">{category}</div>
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Kategori Motor</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="rounded-full bg-white">{rows.length} tipe</Badge>
                  <Button variant="outline" size="sm" className="rounded-full" onClick={() => { setEditing({ category }); setFormOpen(true); }} data-testid={`sp-price-add-${category}`}>
                    <Plus className="mr-1 h-3.5 w-3.5" /> Tipe
                  </Button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      <th className="px-5 py-2">Tipe Motor</th>
                      {TYPES.map((t) => <th key={t.key} className="px-3 py-2 text-right">{t.label}</th>)}
                      <th className="px-3 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((it) => (
                      <tr key={it.id} className="border-t border-slate-100" data-testid={`sp-price-row-${it.id}`}>
                        <td className="px-5 py-2 font-medium text-slate-800">{it.motor}</td>
                        {TYPES.map((t) => (
                          <td key={t.key} className="px-3 py-2 text-right">
                            <PriceCell item={it} typeKey={t.key} onSave={savePrice} saving={savingKey === `${it.id}-${t.key}`} />
                          </td>
                        ))}
                        <td className="px-3 py-2">
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="icon" title="Edit" onClick={() => { setEditing(it); setFormOpen(true); }} data-testid={`sp-price-edit-${it.id}`}>
                              <Pencil className="h-4 w-4 text-slate-600" />
                            </Button>
                            <Button variant="ghost" size="icon" title="Hapus" onClick={() => remove(it)} data-testid={`sp-price-delete-${it.id}`}>
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

      <MotorForm open={formOpen} onOpenChange={setFormOpen} initial={editing} categories={categories} onSaved={load} />
    </div>
  );
}
