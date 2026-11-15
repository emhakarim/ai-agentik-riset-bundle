---
name: pelaporan-hasil
description: Menulis hasil analisis statistik riset pendidikan dalam format APA 7 — Bab IV skripsi/tesis (deskripsi data, uji prasyarat, uji hipotesis), bagian Results artikel jurnal SINTA/internasional, tabel dan narasi bahasa Indonesia atau Inggris — memakai angka dari keluaran edu-stats saja. Pakai saat pengguna minta menuliskan, menarasikan, membuat tabel, atau memformat hasil uji statistik, atau menyusun Bab IV / hasil penelitian.
---

# Pelaporan Hasil Statistik (APA 7)

Skill ini mengubah keluaran alat `edu-stats` menjadi tabel dan narasi siap pakai. Skill ini **tidak
menghitung apa pun**; bila suatu angka belum ada, jalankan dulu alatnya (lihat skill `analisis-kuantitatif`).

## 1. Aturan keras

1. **Setiap angka harus bisa ditunjuk asalnya** di keluaran alat (`result`, `effect_size`, `assumptions`,
   `apa`). Jangan menghitung, menaksir, atau "melengkapi" angka yang tidak ada.
2. **Kalimat di field `apa` dari alat boleh dikutip apa adanya**; bila ditulis ulang, angkanya harus identik.
3. **Simpulan mengikuti `significant` / `keputusan`.** Tidak boleh menulis "signifikan" bila alat menyatakan
   tidak signifikan, dan tidak boleh mengubah arah efek.
4. **Laporkan apa adanya**, termasuk asumsi yang dilanggar, data yang dibuang (`input.n_dropped`), uji yang
   tidak signifikan, dan peringatan di `notes`.
5. **Simpan `audit_id`** setiap analisis di catatan kerja / lampiran (bukan di badan teks naskah), agar hasil
   bisa dibuktikan ulang dengan alat `replay`.

## 2. Format angka APA 7

| Aturan | Benar | Salah |
| :-- | :-- | :-- |
| Statistik dibulatkan 2 desimal (M, SD, t, F, d, B) | *M* = 75.42, *SD* = 8.10 | *M* = 75.4166 |
| Nilai p: 3 desimal, tanpa nol di depan | *p* = .032 | *p* = 0.032, *p* = .0320 |
| p sangat kecil | *p* < .001 | *p* = .000, *p* = 0.000 |
| Statistik yang tidak bisa > 1 (r, p, α, η², R²): tanpa nol di depan | *r* = .45, α = .87 | *r* = 0.45 |
| Statistik yang bisa > 1 (t, F, d, M, SD): dengan nol di depan | *d* = 0.62 | *d* = .62 |
| Derajat kebebasan di dalam kurung | *t*(58) = 2.31, *F*(2, 87) = 4.12 | t = 2.31 (df 58) |
| df Welch / koreksi: 2 desimal | *t*(51.37) = 2.05 | |
| Interval kepercayaan | 95% CI [0.12, 1.04] | (0.12–1.04) |
| Simbol statistik ditulis miring | *M*, *SD*, *t*, *F*, *p*, *r*, *d*, *n*, *N* | |
| Huruf Yunani tegak | α, η², ω², χ², β | |

Modul `fmt` di edu-stats sudah memakai aturan ini di field `apa`, sehingga mengutip field itu paling aman.

**Pemisah desimal.** APA memakai titik. Banyak pedoman skripsi berbahasa Indonesia memakai koma
(75,42). Ikuti pedoman kampus/jurnal pengguna; bila memakai koma, ubah **konsisten** di seluruh naskah dan
pakai titik koma sebagai pemisah antar-angka dalam kurung (95% CI [0,12; 1,04]). Ini hanya perubahan
tampilan, bukan perhitungan ulang.

## 3. Struktur Bab IV (skripsi/tesis)

1. **Deskripsi data** — tabel deskriptif (`descriptives`): n, M, SD, min, maks per kelompok/variabel;
   untuk skala angket sertakan reliabilitas (`reliability`).
2. **Uji prasyarat analisis** — normalitas (sebutkan uji dan pada apa diuji: tiap kelompok / selisih /
   residu), homogenitas, dan asumsi khusus uji (linearitas, multikolinearitas, homogenitas kemiringan regresi,
   sferisitas). Satu tabel ringkas + satu paragraf keputusan.
3. **Uji hipotesis** — untuk tiap hipotesis: tulis H0 dan H1, uji yang dipakai dan alasannya, hasil
   (statistik, df, p, ukuran efek + CI), keputusan (H0 ditolak / tidak ditolak), kalimat simpulan.
4. **Analisis lanjutan** — post hoc, rerata terkoreksi, N-Gain, dsb.
5. **Pembahasan** — kaitkan dengan teori dan penelitian terdahulu (sitasi hanya dari sumber terverifikasi;
   lihat alat `verify_crossref_doi` / `search_openalex_works` milik Zetta), sebutkan keterbatasan.

Artikel jurnal: gabungkan 1–4 menjadi bagian *Results* yang ringkas (biasanya tanpa subbab uji prasyarat
terpisah; asumsi disebut dalam satu-dua kalimat), lalu *Discussion*.

## 4. Templat narasi (isi semua `{…}` dari keluaran alat)

**Uji-t independen** (`ttest_independent`; pakai baris `welch` atau `student` sesuai `recommended`)
> Hasil uji-t {Welch/Student} menunjukkan {terdapat/tidak terdapat} perbedaan yang signifikan antara
> {grup1} (*M* = {m1}, *SD* = {sd1}) dan {grup2} (*M* = {m2}, *SD* = {sd2}), *t*({df}) = {t}, *p* {p},
> *d* = {d}, 95% CI [{lo}, {hi}], dengan ukuran efek {label}.

**ANCOVA** (`ancova`)
> Setelah mengontrol {kovariat}, terdapat/tidak terdapat perbedaan {dv} yang signifikan antarkelompok,
> *F*({df1}, {df2}) = {F}, *p* {p}, ηp² = {eta}. Rerata terkoreksi {grup1} = {adj1} (*SE* = {se1}) dan
> {grup2} = {adj2} (*SE* = {se2}). Asumsi homogenitas kemiringan regresi {terpenuhi/tidak terpenuhi},
> *F*({df}) = {F_int}, *p* {p_int}.

**ANOVA satu arah** (`anova_oneway`) — sebutkan klasik/Welch sesuai `recommended_test`, lalu post hoc
(Tukey / Games-Howell sesuai `posthoc.recommended`) hanya untuk pasangan yang relevan dengan hipotesis.

**Uji berpasangan** (`ttest_paired` / `wilcoxon`) — sebutkan arah selisih (kolom pertama − kedua) dengan
benar: bila posttest > pretest dan selisih dihitung pretest − posttest, nilai t negatif berarti meningkat.

**Korelasi** (`correlation`)
> Terdapat hubungan {positif/negatif} yang {label} dan {signifikan/tidak signifikan} antara {X} dan {Y},
> *r*({df}) = {r}, *p* {p}, 95% CI [{lo}, {hi}].

**Regresi** (`regression`)
> Model regresi {signifikan/tidak signifikan}, *F*({df1}, {df2}) = {F}, *p* {p}, dan menjelaskan {R² × 100}%
> varians {dv} (*R*² = {R2}, adj. *R*² = {adjR2}). {Prediktor} merupakan prediktor yang signifikan,
> *B* = {B}, *SE* = {se}, β = {beta}, *t*({df}) = {t}, *p* {p}.
(Persentase varians = R² × 100 — ini satu-satunya konversi tampilan yang diperbolehkan.)

**Chi-square** (`chi_square`)
> χ²({df}, *N* = {N}) = {chi2}, *p* {p}, Cramér's *V* = {V}. (Bila `recommended` = fisher_exact,
> laporkan Fisher's exact test, *p* {p_fisher}.)

**Reliabilitas** (`reliability`)
> Skala {nama} ({k} butir) memiliki reliabilitas {label}, α = {alpha}, 95% CI [{lo}, {hi}], ω = {omega}.
> {jumlah} dari {k} butir memenuhi kriteria (*r* item-total terkoreksi ≥ {r_table} / ≥ .30); butir
> {daftar} {perlu direvisi/dibuang}.

**N-Gain** (`n_gain`)
> Rerata N-Gain kelas {grup} sebesar {g} (kategori {kategori}; {pct}% — {tafsiran efektivitas}).

**Bahasa Inggris:** "a statistically significant difference", "was not statistically significant",
"after controlling for", "the null hypothesis was rejected / was not rejected".

## 5. Templat tabel

**Tabel deskriptif**

| Kelompok | *n* | *M* | *SD* | Min | Maks |
| :-- | --: | --: | --: | --: | --: |

**Tabel uji-t**

| Variabel | Kelompok 1 *M* (*SD*) | Kelompok 2 *M* (*SD*) | *t* | *df* | *p* | *d* [95% CI] |
| :-- | --: | --: | --: | --: | --: | --: |

**Tabel ANOVA / ANCOVA** (dari `anova_table`)

| Sumber | *SS* | *df* | *MS* | *F* | *p* | ηp² |
| :-- | --: | --: | --: | --: | --: | --: |

**Tabel regresi** (dari `coefficients`)

| Prediktor | *B* | *SE* | β | *t* | *p* | 95% CI *B* | VIF |
| :-- | --: | --: | --: | --: | --: | --: | --: |

**Tabel analisis butir** (dari `reliability.items`)

| Butir | *M* | *SD* | *r* item-total terkoreksi | α jika butir dihapus | Keterangan |
| :-- | --: | --: | --: | --: | :-- |

Format APA: judul tabel di atas ("**Tabel 1**" baris pertama, judul miring baris kedua), tanpa garis
vertikal, catatan di bawah tabel ("*Catatan.* …") untuk singkatan, kriteria, dan butir terbalik.
Bila alat `export_apa7_table` (Zetta) tersedia, boleh dipakai untuk membuat tabel Markdown dari keluaran
edu-stats; tetap periksa angkanya sama dengan keluaran alat.

## 6. Yang tidak boleh ditulis

- "sangat signifikan", "hampir signifikan", "cenderung signifikan", "p = .000".
- "H0 diterima", "H1 terbukti", "membuktikan bahwa" — pakai "H0 ditolak / tidak ditolak", "menunjukkan".
- Klaim kausal ("berpengaruh", "meningkatkan") pada desain korelasional/survei atau kuasi-eksperimen tanpa
  catatan keterbatasan.
- Ukuran efek tanpa label dan tanpa sumber patokannya (Cohen, 1988; George & Mallery, 2003 untuk α;
  Hake, 1999 untuk N-Gain).
- Sitasi yang tidak diverifikasi.

## 7. Daftar periksa sebelum menyerahkan

- [ ] Semua angka cocok dengan keluaran alat (cek ulang satu per satu dengan `result`).
- [ ] n yang dilaporkan = `input.n_used`; data yang dibuang disebutkan.
- [ ] Setiap uji punya statistik, df, p, ukuran efek (+ CI bila ada).
- [ ] Asumsi yang dilanggar disebutkan beserta penanganannya.
- [ ] Format p, nol di depan, desimal, dan cetak miring sesuai §2 dan konsisten.
- [ ] `audit_id` tercatat di lampiran / catatan kerja.
