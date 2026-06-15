import csv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata

nomeArquivoComDados =  "/home/ajm/Desktop/Projetos/RFMapper32/python/Data/gps_251006_223355.csv"


# =============================
# 1. PROCESSAMENTO DIRETO DO CSV BRUTO
# =============================
def process_line(parts):
    fixed_fields = parts[:8]
    networks = parts[8:]
    nets = []
    for i in range(0, len(networks), 2):
        if i + 1 < len(networks):
            ssid = networks[i].strip()
            try:
                rssi = int(networks[i + 1])
                nets.append((ssid, rssi))
            except:
                continue

    macari_rssi = -200
    for ssid, rssi in nets:
        if ssid == "MACARI":
            macari_rssi = rssi
            break

    other_ssid = "NONE"
    other_rssi = -200
    for ssid, rssi in nets:
        if ssid and ssid != "MACARI":
            if rssi > other_rssi:
                other_ssid, other_rssi = ssid, rssi

    return fixed_fields + ["2", "MACARI", str(macari_rssi), other_ssid, str(other_rssi)]


def load_and_process(input_file):
    processed = []
    with open(input_file, "r", newline="", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        for row in reader:
            if not row:
                continue
            # pular cabeçalho ou linhas com lat/lng não numéricos
            try:
                # garante que há pelo menos 3 colunas e que lat/lng são float
                if len(row) < 3:
                    continue
                float(row[1])
                float(row[2])
            except Exception:
                continue
            processed.append(process_line(row))
    return processed


# =============================
# 2. GERA DATAFRAME
# =============================
print("🔍 Lendo e processando o arquivo bruto...")

raw_data = load_and_process(nomeArquivoComDados)

# converte para dataframe
df = pd.DataFrame(raw_data)

# colunas relevantes
df_processed = pd.DataFrame({
    'lat': df[1].astype(float),
    'lng': df[2].astype(float),
    'rssi_lora': df[5].astype(float),
    'rssi_macari': df[10].astype(float),
    'rssi_other_best': df[12].astype(float)
})

print(f"✅ Processadas {len(df_processed)} linhas válidas.")
print("\n📋 Amostra dos dados processados:")
print(df_processed.head())


# =============================
# 3. FUNÇÃO HEATMAP ESTÁTICO
# =============================
def create_heatmap(x, y, z, title, filename):
    if len(x) < 2:
        print(f"⚠️ Poucos pontos para gerar heatmap: {title}")
        return

    try:
        xi = np.linspace(min(x), max(x), 100)
        yi = np.linspace(min(y), max(y), 100)
        Xi, Yi = np.meshgrid(xi, yi)
        Zi = griddata((x, y), z, (Xi, Yi), method='linear')

        plt.figure(figsize=(10, 8))
        plt.contourf(Xi, Yi, Zi, levels=50, cmap='RdYlBu_r')
        plt.colorbar(label='RSSI (dBm)')
        plt.scatter(x, y, c='black', s=10, alpha=0.6, label='Pontos de medição')
        plt.title(title)
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.legend()
        plt.axis('equal')
        plt.grid(True, alpha=0.3)
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✅ Gráfico salvo: {filename}")
    except Exception as e:
        print(f"❌ Erro ao gerar gráfico {title}: {e}")


# =============================
# 4. GERA OS MAPAS
# =============================
print("\n📊 Gerando gráficos estáticos...")

# LoRa
create_heatmap(
    df_processed['lng'].values,
    df_processed['lat'].values,
    df_processed['rssi_lora'].values,
    "Mapa de Calor - RSSI LoRa",
    "heatmap_lora_static.png"
)

# MACARI
if not df_processed[df_processed['rssi_macari'] > -200].empty:
    create_heatmap(
        df_processed['lng'].values,
        df_processed['lat'].values,
        df_processed['rssi_macari'].values,
        "Mapa de Calor - RSSI Rede MACARI",
        "heatmap_macari_static.png"
    )

# Outras Redes
if not df_processed[df_processed['rssi_other_best'] > -200].empty:
    create_heatmap(
        df_processed['lng'].values,
        df_processed['lat'].values,
        df_processed['rssi_other_best'].values,
        "Mapa de Calor - Melhor RSSI (Outras Redes)",
        "heatmap_other_static.png"
    )

print("\n🎉 Todos os mapas foram gerados com sucesso!")
print("📁 Arquivos gerados:")
print("   - heatmap_lora_static.png")
print("   - heatmap_macari_static.png")
print("   - heatmap_other_static.png")
