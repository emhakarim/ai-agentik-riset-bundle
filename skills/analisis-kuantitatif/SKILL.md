---
name: analisis-kuantitatif
description: Alur analisis statistik kuantitatif untuk riset pendidikan (skripsi, tesis, artikel) memakai MCP edu-stats — cek data, uji asumsi, pilih uji yang tepat, ukuran efek, dan tafsir — tanpa AI menghitung sendiri. Pakai saat pengguna meminta uji-t, ANOVA, ANCOVA, korelasi, regresi, chi-square, uji nonparametrik, uji normalitas/homogenitas, uji prasyarat, uji hipotesis, reliabilitas/validitas angket, N-Gain, atau ukuran sampel/power, atau menyerahkan file data (.csv, .xlsx, .sav, .dta) untuk dianalisis.
---

# Analisis Kuantitatif Pendidikan (edu-stats)

Skill ini memandu memilih dan menjalankan analisis statistik. **Semua angka dihitung oleh alat
`edu-stats`, bukan oleh Anda.** Peran Anda: memahami pertanyaan riset, memilih uji, memanggil alat,
membaca asumsi, dan menafsirkan. Untuk menulis Bab IV / bagian Hasil, lanjutkan dengan skill
`pelaporan-hasil`.

## 1. Aturan keras (tidak boleh dilanggar)

1. **Jangan menghitung sendiri.** Rerata, SD, t, F, p, r, d, α, N-Gain, ukuran sampel — semuanya dari
   keluaran alat. Bila alat tidak tersedia, katakan begitu dan tawarkan CLI cadangan (§7); jangan menaksir.
2. **Jangan menulis angka yang tidak ada di keluaran alat.** Bulatkan dari nilai presisi penuh di `result`,
   jangan menghitung ulang turunan (mis. jangan menghitung η² dari F sendiri).
3. **Kata "signifikan" hanya mengikuti field `significant` / `keputusan`.** Jangan menulis "signifikan" bila
   `significant` = false, "hampir signifikan", atau "sangat signifikan".
4. **Pilih uji sebelum melihat p.** Jangan mengganti uji, membuang data, atau mengganti α setelah melihat
   hasil agar menjadi signifikan (p-hacking). Bila ada perubahan rencana, laporkan terang-terangan.
5. **Sampaikan pelanggaran asumsi** yang tercantum di `assumptions` dan `notes`, beserta konsekuensinya.
6. **Sertakan `audit_id`** setiap hasil, agar bisa dibuktikan ulang dengan alat `replay`.
7. **File asli tidak diubah.** Penyiapan skor memakai `prepare_scale`, yang menulis file baru.

## 2. Alur kerja

1. **Pahami riset dulu** (tanya bila belum jelas, maksimal satu kali, sekaligus):
   rumusan masalah / hipotesis, desain (eksperimen, kuasi-eksperimen, korelasional, survei, PTK),
   variabel bebas & terikat beserta skala ukurnya, kelompok, α (default .05), satu atau dua sisi
   (default dua sisi; satu sisi hanya bila hipotesisnya terarah *dan* ditetapkan sebelum melihat data).
2. **Kenali data:** `inspect_data(file)` — nama kolom persis, tipe, data kosong, value label SPSS.
   Pakai nama kolom persis seperti hasil ini.
3. **Siapkan skor** bila data berupa butir angket:
   `reliability(file, items)` → periksa butir berkorelasi negatif (kemungkinan butir terbalik) →
   `prepare_scale(file, items, name, reverse, scale_min, scale_max)` → analisis selanjutnya memakai
   file baru di `result.output_path`. Tanyakan rentang skala bila tidak diketahui; jangan menebak.
4. **Deskripsikan:** `descriptives(file, columns, group)`.
5. **Pilih uji** dengan tabel §3, **cek asumsi** dengan §4.
6. **Jalankan uji**, baca `result`, `effect_size`, `assumptions`, `notes`.
7. **Tafsirkan** dengan §5, lalu serahkan ke skill `pelaporan-hasil` bila pengguna butuh naskah.

## 3. Memilih uji

| Pertanyaan riset | Desain / data | Alat edu-stats | Alternatif bila asumsi berat dilanggar |
| :-- | :-- | :-- | :-- |
| Beda rerata 2 kelompok independen | mis. kelas eksperimen vs kontrol, skor posttest | `ttest_independent(file, dv, group)` | `mann_whitney(file, dv, group)` |
| Efektivitas perlakuan dengan pretest | pretest–posttest control group design | `ancova(file, dv, group, covariates)` (kovariat = pretest) | uji-t/Mann-Whitney pada N-Gain bila asumsi ANCOVA gagal (§4) |
| Beda sebelum–sesudah, satu kelompok | one-group pretest–posttest | `ttest_paired(file, var1, var2)` + `n_gain(file, pre, post, max_score)` | `wilcoxon(file, var1, var2)` |
| Rerata vs nilai acuan (KKM, norma) | satu sampel | `ttest_one_sample(file, column, mu)` | — |
| Beda rerata > 2 kelompok | mis. 3 model pembelajaran | `anova_oneway(file, dv, group)` | `kruskal_wallis(file, dv, group)` |
| Dua faktor atau lebih (+ interaksi) | mis. model × gender | `anova_factorial(file, dv, factors)` | — (laporkan keterbatasan) |
| > 2 pengukuran pada subjek sama | siklus PTK, pengukuran berulang (format lebar) | `anova_rm(file, columns)` | `friedman(file, columns)` |
| Hubungan dua variabel | korelasional | `correlation(file, columns, method="pearson")` | `method="spearman"` (ordinal / tidak normal) atau `"kendall"` (n kecil, banyak ties) |
| Pengaruh beberapa prediktor | regresi | `regression(file, dv, predictors)` | — (laporkan; pertimbangkan transformasi) |
| Pengaruh X ke Y melalui variabel perantara M | mediasi (mis. dukungan guru → efikasi diri → hasil belajar) | `mediation(file, x, m, y, covariates)` | — (keputusan dari CI bootstrap, bukan Sobel) |
| Pengaruh X ke Y bergantung pada W | moderasi (mis. metode × motivasi awal) | `moderation(file, y, x, w, covariates)` | — |
| Hubungan dua variabel kategorik | tabel silang | `chi_square(file, row, col)` | Fisher otomatis untuk 2×2 bila frekuensi harapan kecil |
| Reliabilitas & validitas butir | uji coba angket/tes | `reliability(file, items)`; `r_table(n)` | — |
| Peningkatan hasil belajar | pretest–posttest | `n_gain(file, pre, post, max_score, group)` | — |
| Ukuran sampel sebelum penelitian | perencanaan | `power_ttest(d, design, power=0.8)`, `power_anova(k, f, power=0.8)`, `power_correlation(r, power=0.8)`, `sample_size_survey(population)` | — |

Catatan pemilihan:
- **Pretest–posttest dua kelompok:** ANCOVA dengan pretest sebagai kovariat lebih kuat dan lebih tepat
  daripada uji-t pada posttest saja atau uji-t pada selisih. Uji-t pada posttest saja hanya layak bila
  pretest setara dan pengguna memang merencanakannya.
- **N-Gain bersifat deskriptif.** Untuk menguji beda N-Gain antarkelompok, uji g per siswa dengan
  `ttest_independent` / `mann_whitney`.
- **Format data:** uji antar-kelompok butuh format panjang (satu kolom nilai + satu kolom grup);
  uji berpasangan / berulang butuh format lebar (satu kolom per pengukuran). Bila format tidak cocok,
  jelaskan cara menyusunnya; jangan mengubah data diam-diam.
- **Skor Likert per butir** adalah ordinal; skor total/rerata skala umumnya diperlakukan interval.
  Analisis per butir → nonparametrik atau `chi_square`.

## 4. Uji asumsi — apa, di mana, dan bagaimana menyikapinya

Sebagian besar alat sudah menjalankan uji asumsinya sendiri dan melaporkannya di `assumptions`.
Jalankan `normality` / `homogeneity` terpisah hanya bila pengguna meminta "uji prasyarat" tersendiri
(lazim di skripsi).

| Uji | Normalitas diuji pada | Asumsi lain | Bila dilanggar |
| :-- | :-- | :-- | :-- |
| `ttest_independent` | tiap kelompok | homogenitas varians (Levene) | varians tidak homogen → alat sudah merekomendasikan Welch; tidak normal dan n per grup < 30 → `mann_whitney` |
| `ttest_paired` | **selisih** pasangan (bukan tiap kolom) | — | tidak normal dan n < 30 → `wilcoxon` |
| `anova_oneway` | tiap kelompok | homogenitas | tidak homogen → alat memakai Welch + Games-Howell; tidak normal dan n kecil → `kruskal_wallis` |
| `ancova` | **residu** model | homogenitas kemiringan regresi, homogenitas varians residu | kemiringan tidak homogen → ANCOVA tidak tepat; laporkan, lalu pertimbangkan analisis N-Gain / gain score dengan uji-t |
| `anova_rm` | — | sferisitas (Mauchly) | alat otomatis memilih Greenhouse-Geisser / Huynh-Feldt |
| `regression` | **residu** | multikolinearitas (VIF), homoskedastisitas (Breusch-Pagan), autokorelasi (Durbin-Watson), outlier (Cook's D) | sebutkan setiap pelanggaran; jangan membuang outlier tanpa alasan substantif |
| `correlation` (Pearson) | tiap variabel + linearitas | — | `method="spearman"` |
| `chi_square` | — | frekuensi harapan < 5 maksimal 20% sel | 2×2 → Fisher (otomatis); tabel lebih besar → gabungkan kategori |

Prinsip:
- **Ukuran sampel menentukan bobot uji normalitas.** Untuk n per grup ≥ 30, uji-t dan ANOVA cukup tahan
  terhadap ketidaknormalan sedang; untuk n besar (> 300), Shapiro-Wilk hampir selalu signifikan — lihat
  juga `z_skewness`/`z_kurtosis`. Untuk n kecil, uji normalitas punya power rendah — "normal" tidak berarti
  terbukti normal.
- **Jangan menjalankan uji parametrik dan nonparametrik lalu memilih yang signifikan.** Tentukan dulu dari
  asumsi; boleh melaporkan keduanya sebagai analisis sensitivitas bila disebutkan sejak awal.
- Hasil uji asumsi dilaporkan apa adanya, termasuk yang dilanggar.

## 5. Menafsirkan

- **p bukan ukuran besarnya efek.** Selalu sebutkan ukuran efek dan labelnya dari `effect_size.label`
  (Cohen, 1988), serta CI bila ada.
- **Tidak signifikan ≠ tidak ada pengaruh / kedua kelompok sama.** Tulis "tidak terdapat bukti yang cukup";
  sebutkan kemungkinan power rendah bila n kecil (bisa dicek dengan `power_ttest(d, n=...)` memakai d yang
  ditetapkan dari literatur, bukan d dari data sendiri).
- **Bahasa kausal** ("berpengaruh", "efektif meningkatkan") hanya untuk eksperimen dengan penugasan acak.
  Kuasi-eksperimen: "terdapat perbedaan … setelah mengontrol pretest", sebutkan ancaman validitas.
  Korelasional/regresi data survei: "berhubungan" / "memprediksi", bukan "menyebabkan".
- **Hipotesis:** keputusan dinyatakan sebagai H0 ditolak / tidak ditolak (bukan "H0 diterima" atau
  "H1 terbukti").
- **Banyak uji sekaligus** (mis. korelasi banyak pasangan): sebutkan risiko kesalahan tipe I; post hoc di
  alat sudah terkoreksi (Tukey, Games-Howell, Bonferroni, Holm).
- Pakai `notes` dari alat — isinya catatan metodologis yang sengaja ditulis untuk ditafsirkan.

## 6. Contoh alur singkat

Pengguna: "Data saya pretest dan posttest kelas eksperimen (PBL) dan kontrol, apakah PBL efektif?"

1. `inspect_data(file="nilai.xlsx")` → kolom `pretest`, `posttest`, `kelas` (PBL/Konvensional).
2. `descriptives(file, columns=["pretest", "posttest"], group="kelas")`.
3. `ancova(file, dv="posttest", group="kelas", covariates=["pretest"])` → periksa
   `assumptions.homogeneity_of_regression_slopes`, normalitas residu, Levene residu.
4. `n_gain(file, pre="pretest", post="posttest", max_score=100, group="kelas")` sebagai deskripsi tambahan.
5. Tafsir: F, p, ηp² dan labelnya, rerata terkoreksi tiap kelas; karena kuasi-eksperimen (kelas utuh),
   hindari klaim kausal mutlak. Sertakan `audit_id`.

## 7. Bila MCP tidak tersedia

CLI cadangan (hasil sama, tercatat di audit yang sama):

```
python -m edu_stats.cli list
python -m edu_stats.cli run ancova file=nilai.csv dv=posttest group=kelas covariates='["pretest"]'
python -m edu_stats.cli replay <audit_id>
```

Bila edu-stats sama sekali tidak terpasang, katakan terus terang dan jangan menghitung sendiri.
Alat Zetta (`run_ancova_experiment`, `run_psychometrics`) memakai edu-stats bila terpasang dan sudah
diverifikasi setara (lihat `KOLABORASI.md` di root repo).
