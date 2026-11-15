# Dataset Latihan Kualitatif Sintetis — PUI Educational Resilience

Dataset pendamping kualitatif untuk [`data_survei_resiliensi_300.csv`](../data_survei_resiliensi_300.csv), dirancang untuk pelatihan **Analisis Tematik Berbantuan AI**, **AI sebagai Koder Kedua**, **Audit Anonimisasi PII**, dan **Uji Kesepakatan Antar-Koder (`inter_rater_kappa`)**.

- **Lisensi:** MIT
- **Sifat Data:** 100% Sintetis & Fiktif (aman untuk demonstrasi publik dan eksperimen prompt).
- **Dasar Hitung Panjang Transkrip:** Seluruh 12 transkrip memenuhi batas **600–900 kata** baik untuk **dialog tanya-jawab murni** (`Jumlah_Kata_Dialog`: **607–674 kata**, tanpa *header* metadata, label pembicara, penanda `[SEG_...]`, maupun catatan lapangan) maupun **total berkas Markdown** (`Jumlah_Kata`: **738–808 kata**).

## A. Paket Distribusi Peserta Workshop (*Blind Coding* & Praktik Langsung)
Berkas berikut disiapkan untuk dibagikan kepada peserta pelatihan:
1. `metadata_partisipan.csv`: Metadata 12 partisipan (6 siswa SMP/SMA, 4 guru, 2 orang tua; zona `Urban` dan `Rural`, lengkap dengan kolom `Jumlah_Kata` dan `Jumlah_Kata_Dialog`).
2. `transkrip/P01_...md` s.d. `P12_...md`: 12 transkrip wawancara mendalam berbahasa Indonesia percakapan.
3. `codebook_resiliensi_kualitatif.csv`: Buku kode (12 kode: 10 kode dari 5 tema resiliensi utama, 1 kode kasus pembantah `BANTAH_NEG`, dan 1 kode pengecoh `GAMI_KECOH`).
4. `pengodean_dua_koder.csv`: Hasil pengodean 40 segmen **kutipan verbatim persis** dari transkrip (`P01`, `P02`, `P07`, `P11`) lengkap dengan kolom penanda `Penanda_Transkrip` (`SEG_P01_01`, dst.) oleh `Koder_1` dan `Koder_2` ($\kappa = 0.580$, 62.5% kesepakatan). *(Catatan latihan "AI sebagai Koder Kedua": salin tabel dengan mengosongkan/menyembunyikan `Koder_2` agar AI mengode segmen verbatim yang sama persis).*
5. `transkrip_mentah_belum_anonim/RAW_P12_belum_anonim.md`: Transkrip mentah berisi 8 identitas fiktif (PII) untuk latihan de-identifikasi sebelum analisis AI.

## B. Berkas Khusus Pemateri / Instruktur (Keluarkan Sebelum Dibagikan ke Peserta)
> **Peringatan Distribusi:** Saat mendistribusikan paket data ke peserta untuk sesi *blind coding*, **keluarkan/pisahkan** kedua berkas kunci di bawah ini terlebih dahulu agar kunci tema pengecoh, letak kasus pembantah, kunci anonimisasi, dan statistik acuan tidak membocori latihan peserta sebelum diskusi pleno:
- `kunci_pemateri_instruktur.md`: Kunci jawaban lengkap & panduan diskusi instruktur workshop.
- `kunci_pemateri_acuan.json`: Kunci jawaban terstruktur JSON & parameter eksak $\kappa$ acuan.
