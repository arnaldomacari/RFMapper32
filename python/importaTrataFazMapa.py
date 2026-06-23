import csv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata

nomeArquivoComDados =  "/home/ajm/Desktop/Projetos/RFMapper32/python/Data/gps_260621_Interno.csv"
#nomeArquivoComDados =  "/home/ajm/Desktop/Projetos/RFMapper32/python/Data/gps_260621_InternoExterno.csv"
#nomeArquivoComDados =  "/home/ajm/Desktop/Projetos/RFMapper32/python/Data/gps_260621_171440.csv"


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
    interferents = []
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

            networks = row[8:]
            for i in range(0, len(networks), 2):
                if i + 1 >= len(networks):
                    continue
                ssid = networks[i].strip()
                try:
                    rssi = int(networks[i + 1])
                except Exception:
                    continue
                if ssid and ssid.upper() != "MACARI":
                    interferents.append([row[1], row[2], row[4], ssid, rssi])

    return processed, interferents


# =============================
# 2. GERA DATAFRAME
# =============================
print("🔍 Lendo e processando o arquivo bruto...")

raw_data, interferent_data = load_and_process(nomeArquivoComDados)

# converte para dataframe
if len(raw_data) == 0:
    print("Nenhum dado processado. Verifique o arquivo de entrada.")
    raise SystemExit(1)

df = pd.DataFrame(raw_data)

# colunas relevantes
df_processed = pd.DataFrame({
    'lat': df[1].astype(float),
    'lng': df[2].astype(float),
    'hdop': df[4].astype(float),
    'rssi_lora': df[5].astype(float),
    'rssi_macari': df[10].astype(float),
    'rssi_other_best': df[12].astype(float)
})

# dataframe de interferentes (uma linha por aparecimento de SSID não-MACARI)
df_interferents = pd.DataFrame(interferent_data, columns=['lat', 'lng', 'hdop', 'ssid', 'rssi'])
if not df_interferents.empty:
    df_interferents['lat'] = df_interferents['lat'].astype(float)
    df_interferents['lng'] = df_interferents['lng'].astype(float)
    df_interferents['hdop'] = df_interferents['hdop'].astype(float)
    df_interferents['rssi'] = df_interferents['rssi'].astype(float)

print(f"✅ Processadas {len(df_processed)} linhas válidas.")
print("\n📋 Amostra dos dados processados:")
print(df_processed.head())
if not df_interferents.empty:
    print("\n📋 Amostra dos interferentes detectados:")
    print(df_interferents.head())


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
# 4. MAPA DE INTERFERENTES
# =============================

def create_interferent_map(df, title, filename):
    if df.empty:
        print(f"⚠️ Nenhum interferente para gerar o mapa: {title}")
        return

    ssids = df['ssid'].unique()
    num_ssids = len(ssids)
    cmap = plt.cm.tab20 if num_ssids <= 20 else plt.cm.hsv
    colors = [cmap(i) for i in range(num_ssids)]
    color_map = {ssid: colors[i] for i, ssid in enumerate(ssids)}

    plt.figure(figsize=(10, 8))
    for ssid in ssids:
        df_ssid = df[df['ssid'] == ssid]
        plt.scatter(
            df_ssid['lng'],
            df_ssid['lat'],
            c=[color_map[ssid]],
            s=40,
            alpha=0.8,
            edgecolors='black',
            linewidths=0.3,
            label=ssid
        )

    # overlay main MACARI points if available
    if not df_processed[df_processed['rssi_macari'] > -200].empty:
        plt.scatter(
            df_processed['lng'],
            df_processed['lat'],
            c='black',
            s=10,
            alpha=0.4,
            marker='x',
            label='MACARI'
        )

    plt.title(title)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.legend(title='Interferentes', loc='best', fontsize='small')
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Gráfico salvo: {filename}")


# =============================
# 5. ESTIMADOR POR CENTROIDE PONDERADO
# =============================

def estimate_centroid_positions(df):
    """Estima a posição de cada SSID como centroide ponderado por RSSI.

    Usa conversão linear de potência: weight = 10^(rssi/10).
    Retorna DataFrame com colunas: ssid, lat, lng, spread, mean_rssi.
    """
    if df.empty:
        return pd.DataFrame(columns=['ssid', 'lat', 'lng', 'spread', 'mean_rssi'])

    estimates = []
    for ssid in df['ssid'].unique():
        sub = df[df['ssid'] == ssid]
        if sub.empty:
            continue
        # converter RSSI dBm para peso linear
        weights = 10 ** (sub['rssi'] / 10.0)
        wsum = weights.sum()
        if wsum <= 0:
            continue
        lat_est = (sub['lat'] * weights).sum() / wsum
        lng_est = (sub['lng'] * weights).sum() / wsum
        # dispersão/propagação: distância média ponderada ao centro
        dists = np.sqrt((sub['lat'] - lat_est) ** 2 + (sub['lng'] - lng_est) ** 2)
        spread = np.sqrt((weights * (dists ** 2)).sum() / wsum)
        mean_rssi = (sub['rssi'] * weights).sum() / wsum
        estimates.append({'ssid': ssid, 'lat': lat_est, 'lng': lng_est, 'spread': spread, 'mean_rssi': mean_rssi})

    return pd.DataFrame(estimates)


def create_estimated_positions_map(df_points, df_estimates, title, filename):
    """Gera mapa estático com pontos de medição e posições estimadas por SSID."""
    if df_estimates.empty:
        print(f"⚠️ Nada estimado para gerar o mapa: {title}")
        return

    # paleta para estimativas
    ssids = df_estimates['ssid'].values
    num = len(ssids)
    cmap = plt.cm.tab20 if num <= 20 else plt.cm.hsv
    colors = [cmap(i) for i in range(num)]
    color_map = {ssid: colors[i] for i, ssid in enumerate(ssids)}

    plt.figure(figsize=(10, 8))

    # desenha pontos de medição (interferentes) em transparência
    if not df_points.empty:
        for ssid in df_points['ssid'].unique():
            sub = df_points[df_points['ssid'] == ssid]
            plt.scatter(sub['lng'], sub['lat'], c='gray', s=15, alpha=0.25, marker='o')

    # desenha estimativas como estrelas grandes, com tamanho proporcional ao spread
    for _, row in df_estimates.iterrows():
        s = max(60, 2000 * row['spread']) if not np.isnan(row['spread']) else 100
        plt.scatter(row['lng'], row['lat'], marker='*', s=s, c=[color_map[row['ssid']]],
                    edgecolors='black', linewidths=0.6, label=f"{row['ssid']} (est)")
        plt.text(row['lng'], row['lat'], f" {row['ssid']}", fontsize=8, weight='bold', va='bottom')

    # overlay MACARI
    if not df_processed[df_processed['rssi_macari'] > -200].empty:
        plt.scatter(
            df_processed['lng'],
            df_processed['lat'],
            c='black',
            s=8,
            alpha=0.4,
            marker='x',
            label='MACARI'
        )

    plt.title(title)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize='small')
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Gráfico salvo: {filename}")


# =============================
# 6. ESTIMATIVA USANDO MODELO DE PERDA (RSSI -> DISTÂNCIA)
# =============================

def latlon_to_xy(lat, lon, lat0=None):
    """Converte arrays de lat/lon para coordenadas XY em metros usando projeção equiretangular."""
    R = 6371000.0
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    if lat0 is None:
        lat0 = lat.mean()
    lat_rad = np.deg2rad(lat)
    lon_rad = np.deg2rad(lon)
    lat0_rad = np.deg2rad(lat0)
    x = R * lon_rad * np.cos(lat0_rad)
    y = R * lat_rad
    return x, y


def xy_to_latlon(x, y, lat0=None):
    R = 6371000.0
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    lat = np.rad2deg(y / R)
    if lat0 is None:
        lat0 = lat.mean()
    lat0_rad = np.deg2rad(lat0)
    lon = np.rad2deg(x / (R * np.cos(lat0_rad)))
    return lat, lon


def estimate_positions_from_rssi_distance(df, A=-40.0, n=2.0, eps=1e-6):
    """Estima posições convertendo RSSI -> distância pelo modelo: rssi = A - 10*n*log10(d).

    Parâmetros:
    - A: RSSI at 1 meter (dBm)
    - n: path-loss exponent
    Retorna DataFrame com colunas ssid, lat, lng, spread_m, mean_rssi, mean_distance_m
    """
    if df.empty:
        return pd.DataFrame(columns=['ssid', 'lat', 'lng', 'spread_m', 'mean_rssi', 'mean_distance_m'])

    estimates = []
    lat0 = df['lat'].mean()
    for ssid in df['ssid'].unique():
        sub = df[df['ssid'] == ssid]
        if sub.empty:
            continue
        rssi = sub['rssi'].astype(float)
        # estimativa de distância (metros)
        distances = 10 ** ((A - rssi) / (10.0 * n))

        # converte coords para metros
        x, y = latlon_to_xy(sub['lat'].values, sub['lng'].values, lat0=lat0)

        # pesos inversos pela distância^2 (mais peso para pontos mais próximos ao transmissor)
        weights = 1.0 / (distances + eps) ** 2
        wsum = weights.sum()
        if wsum <= 0:
            continue
        x_est = (x * weights).sum() / wsum
        y_est = (y * weights).sum() / wsum
        lat_est, lon_est = xy_to_latlon(x_est, y_est, lat0=lat0)

        # dispersão média ponderada (em metros)
        dists_m = np.sqrt((x - x_est) ** 2 + (y - y_est) ** 2)
        spread_m = np.sqrt((weights * (dists_m ** 2)).sum() / wsum)
        mean_rssi = (rssi * weights).sum() / wsum
        mean_distance = (distances * weights).sum() / wsum

        estimates.append({'ssid': ssid, 'lat': lat_est, 'lng': lon_est, 'spread_m': spread_m, 'mean_rssi': mean_rssi, 'mean_distance_m': mean_distance})

    return pd.DataFrame(estimates)


def create_estimated_positions_map_distance(df_points, df_estimates, title, filename):
    """Plota estimativas derivadas de conversão RSSI->distância."""
    if df_estimates.empty:
        print(f"⚠️ Nada estimado para gerar o mapa: {title}")
        return

    ssids = df_estimates['ssid'].values
    num = len(ssids)
    cmap = plt.cm.tab20 if num <= 20 else plt.cm.hsv
    colors = [cmap(i) for i in range(num)]
    color_map = {ssid: colors[i] for i, ssid in enumerate(ssids)}

    plt.figure(figsize=(10, 8))
    # pontos de medição
    if not df_points.empty:
        plt.scatter(df_points['lng'], df_points['lat'], c='lightgray', s=15, alpha=0.3, marker='o', label='medições')

    for _, row in df_estimates.iterrows():
        s = max(80, row['mean_distance_m'] * 5)
        plt.scatter(row['lng'], row['lat'], marker='o', s=s, c=[color_map[row['ssid']]], edgecolors='black', linewidths=0.6, label=f"{row['ssid']} (est)")
        plt.text(row['lng'], row['lat'], f" {row['ssid']}", fontsize=8, weight='bold', va='bottom')

    # overlay MACARI
    if not df_processed[df_processed['rssi_macari'] > -200].empty:
        plt.scatter(df_processed['lng'], df_processed['lat'], c='black', s=8, alpha=0.4, marker='x', label='MACARI')

    plt.title(title)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.axis('equal')
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize='small')
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Gráfico salvo: {filename}")


# =============================
# 7. GERA OS MAPAS
# =============================
print("\n📊 Gerando gráficos estáticos...")

# LoRa
create_heatmap(
    df_processed['lng'].values,
    df_processed['lat'].values,
    df_processed['rssi_lora'].values,
    "Mapa de Calor - RSSI LoRa",
    "/home/ajm/Desktop/Projetos/RFMapper32/python/Resultados/heatmap_lora_static.png"
)

# MACARI
if not df_processed[df_processed['rssi_macari'] > -200].empty:
    create_heatmap(
        df_processed['lng'].values,
        df_processed['lat'].values,
        df_processed['rssi_macari'].values,
        "Mapa de Calor - RSSI Rede MACARI",
        "/home/ajm/Desktop/Projetos/RFMapper32/python/Resultados/heatmap_macari_static.png"
    )

# Outras Redes
if not df_processed[df_processed['rssi_other_best'] > -200].empty:
    create_heatmap(
        df_processed['lng'].values,
        df_processed['lat'].values,
        df_processed['rssi_other_best'].values,
        "Mapa de Calor - Melhor RSSI (Outras Redes)",
        "/home/ajm/Desktop/Projetos/RFMapper32/python/Resultados/heatmap_other_static.png"
    )

# HDOP
if not df_processed.empty:
    create_heatmap(
        df_processed['lng'].values,
        df_processed['lat'].values,
        df_processed['hdop'].values,
        "Mapa de Calor - HDOP",
        "/home/ajm/Desktop/Projetos/RFMapper32/python/Resultados/heatmap_hdop_static.png"
    )

# Interferentes coloridos
create_interferent_map(
    df_interferents,
    "Mapa de Interferentes - SSIDs não MACARI",
    "/home/ajm/Desktop/Projetos/RFMapper32/python/Resultados/interferentes_scatter.png"
)

# Estimativa de posição por centroide ponderado e mapa resultante
df_estimates = estimate_centroid_positions(df_interferents)
if not df_estimates.empty:
    create_estimated_positions_map(
        df_interferents,
        df_estimates,
        "Estimativa de Posições dos Interferentes",
        "/home/ajm/Desktop/Projetos/RFMapper32/python/Resultados/interferentes_estimated.png"
    )

# Estimativa usando modelo PLE (RSSI -> distância)
df_estimates_dist = estimate_positions_from_rssi_distance(df_interferents, A=-40.0, n=2.0)
if not df_estimates_dist.empty:
    create_estimated_positions_map_distance(
        df_interferents,
        df_estimates_dist,
        "Estimativa (RSSI->Dist) dos Interferentes (A=-40,n=2)",
        "/home/ajm/Desktop/Projetos/RFMapper32/python/Resultados/interferentes_estimated_distance.png"
    )

print("\n🎉 Todos os mapas foram gerados com sucesso!")
print("📁 Arquivos gerados:")
print("   - heatmap_lora_static.png")
print("   - heatmap_macari_static.png")
print("   - heatmap_other_static.png")
print("   - heatmap_hdop_static.png")
print("   - interferentes_scatter.png")
print("   - interferentes_estimated.png")
