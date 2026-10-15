import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from astar_engine import proses_cari_rute
from fuzzy_engine import hitung_skor_kos

# Path ke file dataset excel baru
DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset_kost_astar_polindra (1).xlsx")


def _init_db_kos() -> dict:
    """
    Membaca dataset Excel (sheet Graf_Edge_Lohbener dan Dataset_Kost_Lohbener_15) di global scope.
    Memetakan data kos di Lohbener dengan harga_bulanan dan nama_kost.
    
    Returns:
        dict: Dictionary db_kos dengan ID Kost/Node sebagai key dan {nama, harga} sebagai value.
    """
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"File dataset tidak ditemukan pada lokasi: {DATASET_PATH}")

    xl = pd.ExcelFile(DATASET_PATH)
    df_edge = pd.read_excel(xl, "Graf_Edge_Lohbener")
    df_kost = pd.read_excel(xl, "Dataset_Kost_Lohbener_15")

    # Ambil daftar node asal dari Graf_Edge_Lohbener
    edge_nodes = [str(n).strip() for n in df_edge['node_asal']]

    db = {}
    for idx, row in df_kost.iterrows():
        nama_kost = str(row['nama_kost']).strip()
        kost_id = str(row.get('id', idx + 1))

        # Mencari node yang cocok di Graf_Edge_Lohbener
        if nama_kost in edge_nodes:
            matching_node = nama_kost
        else:
            matching_node = next((n for n in edge_nodes if nama_kost.lower() in n.lower()), nama_kost)

        # Konversi harga_bulanan
        harga_raw = row.get('harga_bulanan')
        try:
            harga_val = float(harga_raw)
        except (ValueError, TypeError):
            harga_val = 500000.0  # Standar harga fallback jika data tidak tersedia

        # Pembacaan kolom ekstra dari dataset
        alamat_area = str(row.get('alamat_area', '')).strip() if pd.notna(row.get('alamat_area')) else ""
        target_penghuni = str(row.get('target_penghuni', '')).strip() if pd.notna(row.get('target_penghuni')) else "Campur"
        fasilitas_utama = str(row.get('fasilitas_utama', '')).strip() if pd.notna(row.get('fasilitas_utama')) else ""

        entry = {
            "nama": nama_kost,
            "harga": harga_val,
            "harga_display": str(harga_raw),
            "alamat_area": alamat_area,
            "target_penghuni": target_penghuni,
            "fasilitas_utama": fasilitas_utama,
            "node_id": matching_node
        }

        # Key utama: Nama node kos (misal: "Rumah Kos SS Kos 2", "Kos H. Deri")
        db[matching_node] = entry

        # Key alias (misal: "1", "01", "K01") untuk kemudahan query
        db[str(kost_id)] = entry
        db[f"K{int(kost_id):02d}"] = entry

    return db


# Global State: Load Database Kost saat server menyala
db_kos = _init_db_kos()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Engine Smart Kost Polindra",
    description="Backend Sistem Rekomendasi Kost berbasis Pathfinding A* dan Fuzzy Logic Sugeno",
    version="2.1.0"
)

# Enable CORS for cross-origin frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Engine A* dan Fuzzy Logic Smart Kost Polindra siap berjalan!",
        "total_kost_terdaftar": len(set(v['node_id'] for v in db_kos.values()))
    }


def _resolve_db_key(id_kost: str) -> str:
    """
    Helper untuk mencocokkan input id_kost dengan key yang ada pada db_kos.
    """
    id_str = str(id_kost).strip()
    
    if id_str in db_kos:
        return db_kos[id_str]["node_id"]
        
    if id_str.isdigit():
        prefix = f"K{int(id_str):02d}"
        if prefix in db_kos:
            return db_kos[prefix]["node_id"]

    id_upper = id_str.upper()
    for k in db_kos:
        if k.upper() == id_upper or id_upper in k.upper():
            return db_kos[k]["node_id"]
            
    return None


@app.get("/api/rekomendasi/semua")
def get_semua_rekomendasi():
    """
    Endpoint untuk menghitung rute A* dan skor Fuzzy Sugeno untuk seluruh kos yang ada di db_kos.
    Hasil diurutkan secara descending berdasarkan skor_akhir_z.
    """
    # Ambil seluruh kos unik berdasarkan node_id agar tidak ada duplikasi
    unique_kosts = list({v["node_id"]: v for v in db_kos.values()}.values())
    
    hasil_list = []
    
    for kos_info in unique_kosts:
        node_id = kos_info["node_id"]
        harga = kos_info["harga"]
        
        # 1. Jalankan A* Pathfinding
        hasil_astar = proses_cari_rute(node_id)
        if hasil_astar.get("status") != "success":
            continue
            
        jarak = hasil_astar.get("jarak_meter") or hasil_astar.get("total_jarak", 0.0)
        
        # 2. Jalankan Fuzzy Logic Sugeno
        hasil_fuzzy = hitung_skor_kos(harga=harga, jarak=jarak)
        
        hasil_list.append({
            "id_kost": node_id,
            "info_kos": {
                "nama": kos_info["nama"],
                "harga": kos_info["harga"],
                "harga_display": kos_info.get("harga_display", str(kos_info["harga"])),
                "alamat_area": kos_info.get("alamat_area", ""),
                "target_penghuni": kos_info.get("target_penghuni", ""),
                "fasilitas_utama": kos_info.get("fasilitas_utama", "")
            },
            "info_rute": {
                "asal": hasil_astar.get("asal", node_id),
                "tujuan": hasil_astar.get("tujuan", "N0_Gerbang_Polindra"),
                "jarak_meter": jarak,
                "rute": hasil_astar.get("rute", []),
                "segmen": hasil_astar.get("segmen", [])
            },
            "skor_rekomendasi": {
                "skor_akhir_z": hasil_fuzzy["defuzzifikasi"]["skor_akhir_z"],
                "fuzzifikasi": hasil_fuzzy["fuzzifikasi"],
                "inferensi": hasil_fuzzy["inferensi"]
            }
        })
        
    # Urutkan berdasarkan skor_akhir_z secara descending (terbesar ke terkecil)
    ranking_kos = sorted(
        hasil_list,
        key=lambda x: x["skor_rekomendasi"]["skor_akhir_z"],
        reverse=True
    )
    
    return {
        "status": "success",
        "total_data": len(ranking_kos),
        "ranking_kos": ranking_kos
    }


@app.get("/api/rekomendasi/{id_kost}")
def get_rekomendasi(id_kost: str):
    """
    Endpoint utama rekomendasi kost tunggal:
    1. Memvalidasi id_kost pada db_kos.
    2. Mengambil harga kos dari db_kos.
    3. Menjalankan A* Pathfinding (proses_cari_rute) untuk menghitung rute dan jarak.
    4. Menjalankan Fuzzy Logic Sugeno (hitung_skor_kos) berdasarkan harga dan jarak.
    5. Mengembalikan JSON respons komprehensif.
    """
    # 1. Validasi keberadaan id_kost di db_kos
    resolved_node_id = _resolve_db_key(id_kost)
    if not resolved_node_id or resolved_node_id not in db_kos:
        raise HTTPException(
            status_code=404,
            detail=f"Kost dengan ID '{id_kost}' tidak ditemukan dalam basis data."
        )

    # 2. Ambil data harga kos
    kos_info = db_kos[resolved_node_id]
    harga = kos_info["harga"]

    # 3. Jalankan A* Pathfinding
    hasil_astar = proses_cari_rute(resolved_node_id)
    if hasil_astar.get("status") != "success":
        raise HTTPException(
            status_code=400,
            detail=f"Gagal menghitung rute A*: {hasil_astar.get('message', 'Rute tidak ditemukan')}"
        )

    # 4. Ekstrak nilai jarak (meter)
    jarak = hasil_astar.get("jarak_meter") or hasil_astar.get("total_jarak", 0.0)

    # 5. Jalankan Fuzzy Logic Sugeno
    hasil_fuzzy = hitung_skor_kos(harga=harga, jarak=jarak)

    # 6. Return JSON respons komprehensif
    return {
        "status": "success",
        "id_kost": resolved_node_id,
        "info_kos": {
            "nama": kos_info["nama"],
            "harga": kos_info["harga"],
            "harga_display": kos_info.get("harga_display", str(kos_info["harga"])),
            "alamat_area": kos_info.get("alamat_area", ""),
            "target_penghuni": kos_info.get("target_penghuni", ""),
            "fasilitas_utama": kos_info.get("fasilitas_utama", "")
        },
        "info_rute": {
            "asal": hasil_astar.get("asal", resolved_node_id),
            "tujuan": hasil_astar.get("tujuan", "N0_Gerbang_Polindra"),
            "jarak_meter": jarak,
            "rute": hasil_astar.get("rute", []),
            "segmen": hasil_astar.get("segmen", [])
        },
        "skor_rekomendasi": {
            "skor_akhir_z": hasil_fuzzy["defuzzifikasi"]["skor_akhir_z"],
            "fuzzifikasi": hasil_fuzzy["fuzzifikasi"],
            "inferensi": hasil_fuzzy["inferensi"]
        }
    }


@app.get("/api/rute/{id_kost}")
def get_rute(id_kost: str):
    """
    Endpoint khusus untuk mencari rute terpendek saja (A*).
    """
    return proses_cari_rute(id_kost)