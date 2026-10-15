"""
Engine Fuzzy Logic Metode Sugeno (Rata-rata Terbobot)
Sistem Rekomendasi Kost - Smart Mobility Polindra
"""


def fuzzifikasi_harga(harga: float) -> dict:
    """
    Menghitung derajat keanggotaan (mu) untuk variabel input Harga (Rupiah):
    - Murah: Trapesium Kiri (Batas bawah: 400.000, Batas atas: 600.000)
    - Sedang: Segitiga (Batas bawah: 400.000, Puncak: 600.000, Batas atas: 800.000)
    - Mahal: Trapesium Kanan (Batas bawah: 600.000, Batas atas: 800.000)
    """
    # Murah (Trapesium Kiri)
    if harga <= 400000:
        mu_murah = 1.0
    elif 400000 < harga < 600000:
        mu_murah = (600000 - harga) / (600000 - 400000)
    else:
        mu_murah = 0.0

    # Sedang (Segitiga)
    if harga <= 400000 or harga >= 800000:
        mu_sedang = 0.0
    elif 400000 < harga <= 600000:
        mu_sedang = (harga - 400000) / (600000 - 400000)
    else:  # 600000 < harga < 800000
        mu_sedang = (800000 - harga) / (800000 - 600000)

    # Mahal (Trapesium Kanan)
    if harga <= 600000:
        mu_mahal = 0.0
    elif 600000 < harga < 800000:
        mu_mahal = (harga - 600000) / (800000 - 600000)
    else:
        mu_mahal = 1.0

    return {
        "murah": round(max(0.0, mu_murah), 4),
        "sedang": round(max(0.0, mu_sedang), 4),
        "mahal": round(max(0.0, mu_mahal), 4)
    }


def fuzzifikasi_jarak(jarak: float) -> dict:
    """
    Menghitung derajat keanggotaan (mu) untuk variabel input Jarak (Meter):
    - Dekat: Trapesium Kiri (Batas bawah: 300, Batas atas: 800)
    - Lumayan: Segitiga (Batas bawah: 300, Puncak: 800, Batas atas: 1500)
    - Jauh: Trapesium Kanan (Batas bawah: 800, Batas atas: 1500)
    """
    # Dekat (Trapesium Kiri)
    if jarak <= 300:
        mu_dekat = 1.0
    elif 300 < jarak < 800:
        mu_dekat = (800 - jarak) / (800 - 300)
    else:
        mu_dekat = 0.0

    # Lumayan (Segitiga)
    if jarak <= 300 or jarak >= 1500:
        mu_lumayan = 0.0
    elif 300 < jarak <= 800:
        mu_lumayan = (jarak - 300) / (800 - 300)
    else:  # 800 < jarak < 1500
        mu_lumayan = (1500 - jarak) / (1500 - 800)

    # Jauh (Trapesium Kanan)
    if jarak <= 800:
        mu_jauh = 0.0
    elif 800 < jarak < 1500:
        mu_jauh = (jarak - 800) / (1500 - 800)
    else:
        mu_jauh = 1.0

    return {
        "dekat": round(max(0.0, mu_dekat), 4),
        "lumayan": round(max(0.0, mu_lumayan), 4),
        "jauh": round(max(0.0, mu_jauh), 4)
    }


def inferensi_sugeno(fuzz_harga: dict, fuzz_jarak: dict) -> dict:
    """
    Evaluasi 9 aturan fuzzy (Rule Base) dengan operator MIN
    serta agregasi output (Tinggi, Sedang, Rendah) dengan operator MAX.
    """
    murah = fuzz_harga["murah"]
    sedang_h = fuzz_harga["sedang"]
    mahal = fuzz_harga["mahal"]

    dekat = fuzz_jarak["dekat"]
    lumayan = fuzz_jarak["lumayan"]
    jauh = fuzz_jarak["jauh"]

    # 9 Aturan Fuzzy (Operator MIN)
    r1 = min(murah, dekat)       # IF Harga Murah AND Jarak Dekat THEN Tinggi
    r2 = min(murah, lumayan)     # IF Harga Murah AND Jarak Lumayan THEN Tinggi
    r3 = min(murah, jauh)        # IF Harga Murah AND Jarak Jauh THEN Sedang
    r4 = min(sedang_h, dekat)    # IF Harga Sedang AND Jarak Dekat THEN Tinggi
    r5 = min(sedang_h, lumayan)  # IF Harga Sedang AND Jarak Lumayan THEN Sedang
    r6 = min(sedang_h, jauh)     # IF Harga Sedang AND Jarak Jauh THEN Rendah
    r7 = min(mahal, dekat)       # IF Harga Mahal AND Jarak Dekat THEN Sedang
    r8 = min(mahal, lumayan)     # IF Harga Mahal AND Jarak Lumayan THEN Rendah
    r9 = min(mahal, jauh)        # IF Harga Mahal AND Jarak Jauh THEN Rendah

    # Agregasi Output (Operator MAX)
    alpha_tinggi = max(r1, r2, r4)
    alpha_sedang = max(r3, r5, r7)
    alpha_rendah = max(r6, r8, r9)

    return {
        "rules": [
            {"rule": "R1: IF Harga Murah AND Jarak Dekat THEN Tinggi", "alpha": round(r1, 4)},
            {"rule": "R2: IF Harga Murah AND Jarak Lumayan THEN Tinggi", "alpha": round(r2, 4)},
            {"rule": "R3: IF Harga Murah AND Jarak Jauh THEN Sedang", "alpha": round(r3, 4)},
            {"rule": "R4: IF Harga Sedang AND Jarak Dekat THEN Tinggi", "alpha": round(r4, 4)},
            {"rule": "R5: IF Harga Sedang AND Jarak Lumayan THEN Sedang", "alpha": round(r5, 4)},
            {"rule": "R6: IF Harga Sedang AND Jarak Jauh THEN Rendah", "alpha": round(r6, 4)},
            {"rule": "R7: IF Harga Mahal AND Jarak Dekat THEN Sedang", "alpha": round(r7, 4)},
            {"rule": "R8: IF Harga Mahal AND Jarak Lumayan THEN Rendah", "alpha": round(r8, 4)},
            {"rule": "R9: IF Harga Mahal AND Jarak Jauh THEN Rendah", "alpha": round(r9, 4)},
        ],
        "agregasi": {
            "tinggi": round(alpha_tinggi, 4),
            "sedang": round(alpha_sedang, 4),
            "rendah": round(alpha_rendah, 4)
        }
    }


def defuzzifikasi_sugeno(agregasi: dict) -> float:
    """
    Defuzzifikasi Sugeno menggunakan rumus Rata-rata Terbobot (Weighted Average).
    Bobot Ketetapan:
    - Tinggi = 100
    - Sedang = 75
    - Rendah = 50
    """
    a_tinggi = agregasi["tinggi"]
    a_sedang = agregasi["sedang"]
    a_rendah = agregasi["rendah"]

    z_tinggi = 100.0
    z_sedang = 75.0
    z_rendah = 50.0

    total_alpha = a_tinggi + a_sedang + a_rendah

    if total_alpha == 0:
        return 0.0

    z = (a_tinggi * z_tinggi + a_sedang * z_sedang + a_rendah * z_rendah) / total_alpha
    return round(z, 2)


def hitung_skor_kos(harga: float, jarak: float) -> dict:
    """
    Fungsi utama yang membungkus Fuzzifikasi, Inferensi Sugeno, dan Defuzzifikasi.

    Parameters:
        harga (float): Harga sewa kost (Rupiah)
        jarak (float): Jarak kost ke kampus/titik tujuan (Meter)

    Returns:
        dict: Detail nilai Fuzzifikasi, hasil Inferensi, dan Skor Akhir Z.
    """
    fuzz_h = fuzzifikasi_harga(harga)
    fuzz_j = fuzzifikasi_jarak(jarak)

    inferensi = inferensi_sugeno(fuzz_h, fuzz_j)
    skor_z = defuzzifikasi_sugeno(inferensi["agregasi"])

    return {
        "input": {
            "harga": harga,
            "jarak": jarak
        },
        "fuzzifikasi": {
            "harga": fuzz_h,
            "jarak": fuzz_j
        },
        "inferensi": inferensi,
        "defuzzifikasi": {
            "skor_akhir_z": skor_z
        }
    }
