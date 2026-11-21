# LANGKAH 0 · Menyiapkan alat (import) dan alamat berkas
# "import" = meminjam kotak perkakas yang sudah dibuat orang lain.
# pandas : perkakas utama mengolah tabel (seperti Excel versi kode)
# sqlalchemy + psycopg2 : jembatan Python ke PostgreSQL
# Path : menulis alamat folder/berkas yang aman di Windows & Mac
# datetime: mengolah tanggal
# getpass : meminta password tanpa menampilkannya di layar
from datetime import datetime
from getpass import getpass
from pathlib import Path
import pandas as pd
from sqlalchemy import URL, Date, create_engine, text
# Alamat dihitung dari lokasi skrip ini, sehingga skrip tetap jalan
# walaupun dijalankan dengan tombol Run ( ) di VS Code.
# __file__ = berkas skrip ini; .parent = folder di atasnya.
FOLDER_REPO = Path(__file__).resolve().parent.parent
BERKAS_MENTAH = FOLDER_REPO / "data" / "daftar_arsip_fakultas.csv"
FOLDER_OUTPUT = FOLDER_REPO / "output"
FOLDER_OUTPUT.mkdir(exist_ok=True) # buat folder bila belum ada
# Tanggal acuan penilaian retensi: akhir tahun 2026, saat unit arsip
# biasanya menyusun daftar usul musnah. Dibuat tetap (bukan "hari
# ini") agar hasil semua mahasiswa sama dan bisa dicocokkan.
TANGGAL_ACUAN = pd.Timestamp("2026-12-31")
# LANGKAH 1 · Membaca CSV dan mengenali isinya
# dtype=str : baca semua kolom sebagai teks dulu, supaya tidak ada
#   nilai yang "diubah diam-diam" oleh pandas.
# keep_default_na=False: sel kosong dibaca sebagai "" (teks kosong).
df = pd.read_csv(BERKAS_MENTAH, dtype=str, keep_default_na=False)
print("Jumlah baris, kolom :", df.shape)
print("=== LANGKAH 1 · Kenali data ===")
print("Nama kolom            :", list(df.columns))
print(df.head())  # 5 baris pertama
# LANGKAH 2 · Merapikan teks: buang spasi berlebih
# Spasi di awal/akhir tidak terlihat, tetapi membuat "Akademik" dan
# " Akademik" dianggap dua nilai berbeda oleh komputer.
# for ... in ... : ulangi perintah yang sama untuk setiap kolom.
for kolom in df.columns:
    df[kolom] = df[kolom].str.strip()  # strip = buang spasi tepi
# Ganti spasi ganda di tengah judul menjadi satu spasi.
df["judul"] = df["judul"].str.replace(r"\s+", " ", regex=True)
# LANGKAH 3 · Kosakata terkendali (ingat Sesi 11: metadata konsisten)# Kamus (dictionary) Python: { "nilai di data" : "nilai baku" }.
# Kunci ditulis huruf kecil karena data akan kita kecilkan dulu.
KAMUS_UNIT = {
    "kepegawaian": "Kepegawaian", "kpg": "Kepegawaian",
"kepeg.": "Kepegawaian",
"keuangan": "Keuangan", "keu": "Keuangan", "keu.": "Keuangan",
"akademik": "Akademik", "akd": "Akademik", "akad.": "Akademik",
"kemahasiswaan": "Kemahasiswaan", "kmh": "Kemahasiswaan",
"umum dan perlengkapan": "Umum dan Perlengkapan",
"umum & perlengkapan": "Umum dan Perlengkapan",
"ump": "Umum dan Perlengkapan",
}
KAMUS_MEDIA = {
    "kertas": "Kertas", "fisik": "Kertas",
"elektronik": "Elektronik", "digital": "Elektronik",
"e-arsip": "Elektronik",
}
KAMUS_AKSES = {"biasa": "Biasa", "terbatas": "Terbatas",
               "rahasia": "Rahasia"}
# .str.lower() = jadikan huruf kecil; .map(kamus) = terjemahkan.
# Nilai yang tidak ada di kamus akan menjadi kosong (NaN): itu
# tanda ada variasi baru yang harus ditambahkan ke kamus.
df["unit_pencipta"] = df["unit_pencipta"].str.lower().map(KAMUS_UNIT)
df["media"] = df["media"].str.lower().map(KAMUS_MEDIA)
df["tingkat_akses"] = df["tingkat_akses"].str.lower().map(KAMUS_AKSES)
print("\n=== LANGKAH 3 · Nilai unit setelah dibakukan ===")
print(df["unit_pencipta"].value_counts(dropna=False))
# LANGKAH 4 · Menyeragamkan tanggal ke ISO 8601 (YYYY - MM - DD)
# Data berisi tiga format: 2019-03-14, 14/03/2019, dan 14-03-2019.
# def = membuat fungsi sendiri. Fungsi ini mencoba tiap format satu
# per satu; format pertama yang cocok dipakai.
def baca_tanggal(teks):
    for pola in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return pd.Timestamp(datetime.strptime(teks, pola))
        except ValueError:
            pass  # tidak cocok, coba pola lain
    return pd.NaT # NaT = "Not a Time" (kosong)
 # .apply(fungsi) = jalankan fungsi untuk setiap baris kolom itu.
df["tanggal_arsip"] = df["tanggal_arsip"].apply(baca_tanggal)
# Kolom bantu "tahun" untuk grafik. Int64 = bilangan bulat yang
# boleh kosong (agar tidak tampil sebagai 2018.0).
df["tahun"] = df["tanggal_arsip"].dt.year.astype("Int64")
# Kolom jumlah_lembar diubah dari teks ke angka (kosong  - > NaN).
df["jumlah_lembar"] = pd.to_numeric(df["jumlah_lembar"],
                                    errors="coerce").astype("Int64")
# LANGKAH 5 · Membuang baris duplikat (ekspor ganda)
jumlah_awal = len(df)
df = df.drop_duplicates()   # hapus baris kembar persis 
print("\n=== LANGKAH 5 · Duplikat ===")
print("Duplikat dibuang :", jumlah_awal - len(df))
print("Sisa baris       :", len(df))
# LANGKAH 6 · Memeriksa nilai kosong dan anomali
# isna() = apakah sel ini kosong? .sum() = hitung berapa yang True.
print("\n=== LANGKAH 6 · Jumlah kosong per kolom ===")
print(df.isna().sum())

# Periksa nilai di luar nalar: jumlah lembar <= 0 atau tahun > 2026.
anomali_lembar = df[df["jumlah_lembar"].notna() & (df["jumlah_lembar"] <= 0)]
anomali_tahun = df[df["tahun"].notna() & (df["tahun"] > 2026)]
print("Lembar <= 0   :", len(anomali_lembar))
print("Tahun > 2026  :", len(anomali_tahun))
# LANGKAH 7 · Menyimpan hasil bersih ke folder output/
# index=False : nomor baris 0..1199 tidak perlu ikut ditulis ke CSV.
berkas_bersih = FOLDER_OUTPUT / "arsip_bersih.csv"
df.to_csv(berkas_bersih, index=False)
print("\n=== LANGKAH 7 · Tersimpan ===")
print("Berkas bersih :", berkas_bersih)
print("Ukuran berkas :", berkas_bersih.stat().st_size, "byte")
# LANGKAH 8 · Ringkasan statistik & rekap arsip bersih
print("\n=== LANGKAH 8 · Rekap media & tingkat akses ===")
print(df["media"].value_counts(dropna=False))
print()
print(df["tingkat_akses"].value_counts(dropna=False))

print("\n=== LANGKAH 8 · Statistik jumlah lembar ===")
print(df["jumlah_lembar"].describe())
# LANGKAH 9 · Rekap silang unit pencipta dan media arsip
print("\n=== LANGKAH 9 · Rekap unit vs media ===")
print(pd.crosstab(df["unit_pencipta"], df["media"], margins=True))
# LANGKAH 10 · Merapikan urutan kolom dan menyimpan salinan CSV
URUTAN = [
    "no_arsip", "kode_klasifikasi", "nama_klasifikasi", "judul",
    "unit_pencipta", "tanggal_arsip", "tahun", "media",
    "jumlah_lembar", "tingkat_akses", "lokasi_simpan",
    "retensi_aktif", "retensi_inaktif", "keterangan_jra",
    "akhir_aktif", "akhir_inaktif", "status_retensi",
    "perlu_dicek", "catatan_kualitas",
]
kolom_tersedia = [k for k in URUTAN if k in df.columns]
df = df[kolom_tersedia].sort_values("no_arsip")

df.to_csv(
    FOLDER_OUTPUT / "daftar_arsip_bersih.csv",
    index=False,
    encoding="utf-8-sig",
    date_format="%Y-%m-%d",
)
print("\nSalinan CSV tersimpan :", FOLDER_OUTPUT)
# LANGKAH 11 · Menyimpan ke database PostgreSQL
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "postgres"
PG_DB = "postgres"
SKEMA = "sesi12"

PG_PASSWORD = getpass("Password PostgreSQL: ")

alamat = URL.create(
    "postgresql+psycopg2",
    username=PG_USER,
    password=PG_PASSWORD,
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DB,
)
mesin = create_engine(alamat)

dtype_tanggal = {
    k: Date()
    for k in ("tanggal_arsip", "akhir_aktif", "akhir_inaktif")
    if k in df.columns
}

with mesin.begin() as koneksi:
    koneksi.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SKEMA}"))
    df.to_sql(
        "arsip",
        koneksi,
        schema=SKEMA,
        if_exists="replace",
        index=False,
        dtype=dtype_tanggal,
    )
    if "JRA" in globals():
        JRA.to_sql(
            "jra",
            koneksi,
            schema=SKEMA,
            if_exists="replace",
            index=False,
        )
    n = koneksi.execute(text(f"SELECT COUNT(*) FROM {SKEMA}.arsip"))
    print(f"Tersimpan di PostgreSQL : {PG_DB} > {SKEMA}.arsip =", n.scalar(), "baris")

print("\nSelesai!")