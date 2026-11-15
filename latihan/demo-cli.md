# Demo 2: satu alur analisis dengan skill + CLI edu-stats

Ulangi demo workshop di komputer Anda. Data: `data_demo1_resiliensi.csv` (sintetis, 20 siswa, kelompok Program dan
Kontrol). Jalankan dari folder `latihan/` setelah toolkit terpasang (lihat `INSTALL.md`).

## Cara 1 · Minta agen

Buka agen (Claude Code, Antigravity, atau Codex) di folder `latihan/`, lalu tempel:

> Kamu asisten analisis statistik riset pendidikan. Data: data_demo1_resiliensi.csv (skor_resiliensi, kelompok:
> Program vs Kontrol). Tugas: cek data & asumsi, pilih uji beda yang tepat, jalankan lewat edu-stats. Format: tabel
> APA 7 + satu paragraf hasil + audit_id. Aturan: jangan menulis angka yang tidak berasal dari keluaran alat.

Skill `analisis-kuantitatif` membuat agen menjalankan perintah `edu-stats` di terminal satu per satu (dengan meminta
izin), membaca hasil uji asumsi, lalu memilih uji.

## Cara 2 · Jalankan sendiri

Perintahnya sama di PowerShell, cmd, dan bash. Parameter daftar ditulis dipisah koma tanpa tanda kutip.

```
edu-stats run inspect_data file=data_demo1_resiliensi.csv
edu-stats run normality file=data_demo1_resiliensi.csv columns=skor_resiliensi group=kelompok
edu-stats run homogeneity file=data_demo1_resiliensi.csv dv=skor_resiliensi group=kelompok
edu-stats run ttest_independent file=data_demo1_resiliensi.csv dv=skor_resiliensi group=kelompok groups=Program,Kontrol
```

Lihat parameter sebuah alat dengan `edu-stats help ttest_independent`, dan buktikan ulang hasil dengan
`edu-stats replay <audit_id>` (audit_id ada di akhir setiap keluaran).

## Hasil yang seharusnya muncul

| Langkah | Hasil |
|---|---|
| Normalitas (Shapiro-Wilk) | Kontrol W(10) = 0.980, p = .966; Program W(10) = 0.977, p = .950 |
| Homogenitas (Levene) | F(1, 18) = 0.06, p = .808, jadi uji-t Student |
| Uji-t | Program (M = 80.20, SD = 6.76) vs Kontrol (M = 70.00, SD = 6.39), t(18) = 3.47, p = .003, d = 1.55, 95% CI [0.52, 2.54] |

Tanpa `groups=Program,Kontrol`, edu-stats memakai urutan abjad sehingga tertulis Kontrol vs Program dengan t dan d
bertanda negatif. Angkanya sama, hanya arahnya terbalik: tulis arah perbandingan di prompt Anda.

Bila perintah `edu-stats` belum dikenal di terminal, pakai Python virtualenv-nya:
`<repo>/mcp-edu-stats/.venv/Scripts/python.exe -m edu_stats.cli ...` (macOS/Linux: `.venv/bin/python`).
