import os
import math
import pandas as pd
import networkx as nx
from networkx.exception import NetworkXNoPath, NodeNotFound

# Path ke file dataset excel baru
DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset_kost_astar_polindra (1).xlsx")
TARGET_NODE = "N0_Gerbang_Polindra"


def hitung_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Menghitung jarak lurus (meter) antara 2 titik koordinat bumi menggunakan rumus Haversine.
    Fungsi ini menentukan nilai Heuristik (H) agar A* dapat memperkirakan jarak ke target.
    """
    R = 6371000.0  # Jari-jari bumi dalam meter
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2.0) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def muat_peta_dari_excel() -> nx.Graph:
    """
    Membaca dataset Excel (sheet Graf_Node_Lohbener dan Graf_Edge_Lohbener)
    serta membangun NetworkX Graph di global scope.
    """
    G = nx.Graph()
    
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"File dataset tidak ditemukan pada lokasi: {DATASET_PATH}")
        
    xl = pd.ExcelFile(DATASET_PATH)
    df_node = pd.read_excel(xl, "Graf_Node_Lohbener")
    df_edge = pd.read_excel(xl, "Graf_Edge_Lohbener")
    
    # 1. Tambah Node Simpang dari Graf_Node_Lohbener
    for _, row in df_node.iterrows():
        node_id = str(row['node_id']).strip()
        G.add_node(
            node_id,
            latitude=float(row['latitude']),
            longitude=float(row['longitude']),
            nama=node_id,
            tipe=str(row.get('tipe', ''))
        )
        
    # 2. Tambah data koordinat untuk Node Kost jika sheet Dataset_Kost_Lohbener_15 tersedia
    if "Dataset_Kost_Lohbener_15" in xl.sheet_names:
        df_kost = pd.read_excel(xl, "Dataset_Kost_Lohbener_15")
        for _, row in df_kost.iterrows():
            kost_nama = str(row['nama_kost']).strip()
            G.add_node(
                kost_nama,
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                nama=kost_nama
            )
                    
    # 3. Tambah Edge dari Graf_Edge_Lohbener
    for _, row in df_edge.iterrows():
        G.add_edge(
            str(row['node_asal']).strip(),
            str(row['node_tujuan']).strip(),
            weight=float(row['bobot_meter']),
            jenis_edge=str(row.get('jenis_edge', '')),
            keterangan=str(row.get('keterangan', ''))
        )
        
    return G


# Inisialisasi Graf di Global Scope (hanya di-load sekali saat server menyala)
G = muat_peta_dari_excel()


def _heuristic_astar(u: str, v: str) -> float:
    """
    Fungsi Heuristik internal untuk nx.astar_path.
    Mengambil koordinat node u dan v untuk dihitung dengan hitung_haversine.
    """
    node_u = G.nodes[u]
    node_v = G.nodes[v]
    
    if 'latitude' in node_u and 'longitude' in node_u and 'latitude' in node_v and 'longitude' in node_v:
        return hitung_haversine(
            node_u['latitude'], node_u['longitude'],
            node_v['latitude'], node_v['longitude']
        )
    return 0.0


def _resolve_node_id(id_kost: str) -> str:
    """
    Helper untuk mencocokkan input id_kost dengan node_id yang ada pada Graf NetworkX.
    Mendukung format ID angka ('1', '2', dll) maupun nama persis kost.
    """
    id_str = str(id_kost).strip()
    
    if id_str in G.nodes:
        return id_str
        
    # Jika input berupa nomor urut (1-15)
    if id_str.isdigit():
        try:
            xl = pd.ExcelFile(DATASET_PATH)
            if "Dataset_Kost_Lohbener_15" in xl.sheet_names:
                df_kost = pd.read_excel(xl, "Dataset_Kost_Lohbener_15")
                idx = int(id_str) - 1
                if 0 <= idx < len(df_kost):
                    matched_name = str(df_kost.iloc[idx]['nama_kost']).strip()
                    if matched_name in G.nodes:
                        return matched_name
        except Exception:
            pass

    # Case-insensitive / prefix matching
    id_upper = id_str.upper()
    for node in G.nodes:
        if node.upper() == id_upper or id_upper in node.upper():
            return node
            
    return id_str


def proses_cari_rute(id_kost: str) -> dict:
    """
    Menjalankan algoritma A* Pathfinding dari node id_kost ke target N0_Gerbang_Polindra.
    Menangkap exception NetworkXNoPath dan NodeNotFound.
    
    Returns:
        dict: { status, asal, tujuan, rute, total_jarak, jarak_meter } atau error dictionary.
    """
    target_kampus = TARGET_NODE  # N0_Gerbang_Polindra
    start_node = _resolve_node_id(id_kost)
    
    try:
        if start_node not in G.nodes:
            raise NodeNotFound(f"Node atau Kost dengan ID '{id_kost}' tidak ditemukan dalam graf.")
            
        rute = nx.astar_path(
            G,
            source=start_node,
            target=target_kampus,
            heuristic=_heuristic_astar,
            weight='weight'
        )
        
        total_jarak = nx.astar_path_length(
            G,
            source=start_node,
            target=target_kampus,
            heuristic=_heuristic_astar,
            weight='weight'
        )
        
        jarak_rounded = round(total_jarak, 2)

        # Hitung segmen rute antar node
        segmen_edges = []
        for i in range(len(rute) - 1):
            u, v = rute[i], rute[i+1]
            edge_data = G.get_edge_data(u, v) or {}
            w = edge_data.get('weight', 0.0)
            segmen_edges.append({
                "asal": u,
                "tujuan": v,
                "jarak_meter": round(w, 2)
            })
        
        return {
            "status": "success",
            "asal": start_node,
            "tujuan": target_kampus,
            "rute": rute,
            "segmen": segmen_edges,
            "total_jarak": jarak_rounded,
            "jarak_meter": jarak_rounded
        }
        
    except NodeNotFound as e:
        return {
            "status": "error",
            "message": str(e),
            "rute": [],
            "total_jarak": 0,
            "jarak_meter": 0
        }
    except NetworkXNoPath:
        return {
            "status": "error",
            "message": f"Tidak ditemukan rute yang menghubungkan '{start_node}' ke '{target_kampus}'.",
            "rute": [],
            "total_jarak": 0,
            "jarak_meter": 0
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Terjadi kesalahan saat memproses rute: {str(e)}",
            "rute": [],
            "total_jarak": 0,
            "jarak_meter": 0
        }
