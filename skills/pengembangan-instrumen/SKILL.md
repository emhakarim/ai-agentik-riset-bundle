---
name: pengembangan-instrumen
description: Alur pengembangan dan validasi instrumen penelitian pendidikan (angket/skala Likert, tes pilihan ganda, lembar validasi produk R&D) memakai MCP edu-stats — kisi-kisi, validitas isi oleh ahli (Aiken's V, CVR Lawshe), uji coba, validitas butir, reliabilitas (α, ω, KR-20), tingkat kesukaran, daya beda, dan analisis pengecoh. Pakai saat pengguna menyusun, memvalidasi, atau menganalisis hasil uji coba instrumen, atau menyebut validasi ahli, expert judgment, uji validitas, uji reliabilitas, analisis butir/item.
---

# Pengembangan & Validasi Instrumen (edu-stats)

Semua angka dari alat `edu-stats`; jangan menghitung sendiri. Aturan keras dari skill `analisis-kuantitatif`
(§1) berlaku juga di sini. Untuk menuliskan hasilnya pakai skill `pelaporan-hasil`.

## 1. Tahapan

1. **Definisi konstruk & kisi-kisi** — definisi konseptual dan operasional, dimensi → indikator → butir.
   Untuk angket, rencanakan butir positif dan negatif (unfavorable) dan catat mana yang negatif.
   Untuk tes, buat tabel spesifikasi (indikator × level kognitif) dan kunci jawaban.
2. **Validitas isi oleh ahli** (sebelum uji coba) — §2.
3. **Revisi** berdasarkan penilaian dan komentar ahli.
4. **Uji coba lapangan** — sampel di luar sampel penelitian dengan karakteristik serupa (minimal 30; untuk
   analisis faktor jauh lebih banyak).
5. **Analisis butir & reliabilitas** — §3 (angket) atau §4 (tes).
6. **Keputusan butir** — pertahankan / revisi / buang, satu per satu, lalu hitung ulang reliabilitas.
7. **Dokumentasi** — tabel hasil validasi ahli, tabel analisis butir, reliabilitas akhir, dan `audit_id`.

## 2. Validitas isi (penilaian ahli)

Format data: **satu baris per butir, satu kolom per ahli**, opsional satu kolom label butir.

| Kebutuhan | Alat | Catatan |
| :-- | :-- | :-- |
| Skor relevansi/kelayakan berskala (mis. 1–4 atau 1–5) | `aiken_v(file, raters, scale_min, scale_max, item_col)` | Butir valid bila p ≤ α (= V ≥ V kritis Aiken, 1985). Banyak penelitian Indonesia juga memakai kategori deskriptif (V > .8 tinggi) — sebutkan kriteria yang dipakai. |
| Penilaian esensial / berguna / tidak perlu | `cvr_lawshe(file, raters, essential, item_col)` | `essential` = kode jawaban "esensial", mis. `[3]` atau `["E"]`. Butir dipertahankan bila CVR ≥ CVR kritis (Ayre & Scally, 2014); CVI = rerata CVR butir yang dipertahankan. |

- Tanyakan **rentang skala** dan **kode "esensial"** bila tidak jelas; jangan menebak dari data.
- Jumlah ahli menentukan batas kritis: dengan 3 ahli, Aiken's V hampir tidak mungkin signifikan dan CVR
  butuh kesepakatan penuh. Sampaikan ini ke pengguna; sarankan 5–10 ahli bila memungkinkan.
- Komentar kualitatif ahli tetap harus ditindaklanjuti walau indeksnya memenuhi.

**Kesepakatan antar-penilai** (mis. dua guru menilai esai/kinerja yang sama, atau keajekan pengamat):

| Data penilaian | Alat |
| :-- | :-- |
| Kategori, 2 penilai | `inter_rater_kappa(file, raters)`; untuk kategori berurutan pakai `weights="quadratic"` |
| Kategori, ≥ 3 penilai | `inter_rater_kappa(file, raters)` (otomatis Fleiss' κ) |
| Skor kontinu / rubrik banyak tingkat, ≥ 2 penilai | `icc(file, raters)` — pilih bentuk ICC sesuai desain **sebelum** melihat hasil (lihat `notes`) |

## 3. Angket / skala Likert (uji coba)

1. `reliability(file, items)` — periksa `notes`: butir berkorelasi negatif dengan total biasanya butir
   negatif yang belum dibalik.
2. `prepare_scale(file, items, name, reverse, scale_min, scale_max)` — balik butir negatif ke file baru.
3. `reliability(file, items)` lagi, dengan `file` = `result.output_path` dari langkah 2 dan butir negatif
   diganti kolom `_R`-nya — α + CI, ω, r item-total terkoreksi vs `r_table(n)`, α jika butir dihapus.
4. Buang/revisi butir **satu per satu** (yang paling lemah dulu), jalankan ulang `reliability`. Jangan
   membuang butir hanya demi menaikkan α bila butir itu penting bagi isi konstruk (cek kisi-kisi).

Kriteria validitas butir yang lazim: r item-total terkoreksi ≥ r tabel (uji signifikansi) dan/atau ≥ .30.
Sebutkan kriteria yang dipakai. α ≥ .70 lazim dianggap dapat diterima untuk penelitian.

## 4. Tes pilihan ganda / benar–salah (uji coba)

`item_analysis_cognitive(file, items, key)`
- `key` = kunci jawaban `{"S1": "B", "S2": "D", ...}` bila data berisi opsi (A/B/C/D) — ini juga
  menghasilkan analisis pengecoh. Tanpa `key`, data harus sudah 0/1.
- Hasil per butir: P (kesukaran), D (daya beda kelompok atas–bawah 27%), r point-biserial terkoreksi,
  keputusan (diterima / revisi / dibuang), dan untuk tiap pengecoh: berfungsi atau tidak.
- Reliabilitas tes: KR-20.

Pertimbangan keputusan:
- Keputusan alat didasarkan pada D. Butir dengan D baik tetapi P sangat ekstrem (< .10 atau > .90) tetap
  layak ditinjau.
- **D negatif** → periksa kunci jawaban dulu sebelum membuang butir.
- **Pengecoh tidak berfungsi** (dipilih < 5% peserta, atau lebih banyak dipilih kelompok atas) → ganti
  pengecohnya, butir tidak harus dibuang.
- Butir uraian/politomus: pakai `reliability` (α) dan r item-total, bukan `item_analysis_cognitive`.

## 5. Bila alat MCP edu-stats tidak tersedia

Cek di awal apakah alat edu-stats (`aiken_v`, `reliability`, dst.) ada di sesi ini (di Claude Code bisa berstatus
*ditunda* dan dimuat saat dibutuhkan; itu berarti aktif). Bila tidak ada, ikuti prosedur §7 skill
`analisis-kuantitatif`: jangan menghitung sendiri, lanjutkan lewat CLI edu-stats dari virtualenv-nya, lalu tawarkan
mengaktifkan server MCP (tingkat pengguna) untuk sesi berikutnya. Contoh CLI:

```
<venv-python> -m edu_stats.cli run aiken_v file=validasi_ahli.csv raters='["Ahli1","Ahli2","Ahli3"]' scale_min=1 scale_max=5
<venv-python> -m edu_stats.cli run reliability file=ujicoba.csv items='["B1","B2","B3","B4"]'
```

## 6. Yang belum tersedia

- EFA/CFA dan Rasch/IRT belum ada di edu-stats (rencana Fase 2–3). Katakan terus terang bila diminta;
  jangan menghitung sendiri.
- Penyaringan responden asal-asalan (straight-lining, IRV, jarak Mahalanobis) tersedia di alat Zetta
  `screen_careless_responders` — jalankan sebelum analisis butir angket bila data dari survei daring.
