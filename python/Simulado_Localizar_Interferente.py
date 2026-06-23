import numpy as np
import pandas as pd
from scipy.optimize import least_squares
import matplotlib.pyplot as plt

# =========================
# 1) Fonte real conhecida
# =========================

x0_real = 45
y0_real = -80

A_real = -40
n_real = 2.7

# =========================
# 2) Pontos dentro da chácara
# =========================

np.random.seed(42)

# Exemplo: chácara retangular
x_min, x_max = -150, 150
y_min, y_max = 0, 200

num_pontos = 80

x = np.random.uniform(x_min, x_max, num_pontos)
y = np.random.uniform(y_min, y_max, num_pontos)

# =========================
# 3) Modelo RSSI
# =========================

def rssi_model(x, y, x0, y0, A, n):
    d = np.sqrt((x - x0)**2 + (y - y0)**2)
    d = np.maximum(d, 1.0)
    return A - 10 * n * np.log10(d)

# RSSI ideal
rssi_ideal = rssi_model(x, y, x0_real, y0_real, A_real, n_real)

# Ruído realista
ruido = np.random.normal(0, 0.3 , num_pontos)
rssi_medido = rssi_ideal + ruido

dados = pd.DataFrame({
    "x": x,
    "y": y,
    "rssi": rssi_medido
})

# =========================
# 4) Estimar fonte
# =========================

def erro(params, x, y, rssi_medido):
    x0, y0, A, n = params
    rssi_estimado = rssi_model(x, y, x0, y0, A, n)
    return rssi_estimado - rssi_medido

chute_inicial = [
    0,      # x0
    -50,    # y0
    -40,    # A
    2.5     # n
]

limites = (
    [-500, -500, -100, 1.0],
    [ 500,  500,  -10, 6.0]
)

resultado = least_squares(
    erro,
    chute_inicial,
    bounds=limites,
    args=(x, y, rssi_medido)
)

x0_est, y0_est, A_est, n_est = resultado.x

print("Fonte real:")
print(f"x0 = {x0_real:.2f}, y0 = {y0_real:.2f}")
print(f"A  = {A_real:.2f}, n  = {n_real:.2f}")

print("\nFonte estimada:")
print(f"x0 = {x0_est:.2f}, y0 = {y0_est:.2f}")
print(f"A  = {A_est:.2f}, n  = {n_est:.2f}")

erro_pos = np.sqrt((x0_est - x0_real)**2 + (y0_est - y0_real)**2)
print(f"\nErro de posição: {erro_pos:.2f} m")

# =========================
# 5) Plot
# =========================

plt.figure(figsize=(8, 6))

plt.scatter(x, y, c=rssi_medido, label="Pontos medidos")
plt.colorbar(label="RSSI medido (dBm)")

plt.scatter(x0_real, y0_real, marker="*", s=50, label="Fonte real")
plt.scatter(x0_est, y0_est, marker="X", s=40, label="Fonte estimada")

plt.axhline(y_min, linestyle="--")
plt.axhline(y_max, linestyle="--")
plt.axvline(x_min, linestyle="--")
plt.axvline(x_max, linestyle="--")

plt.xlabel("x (m)")
plt.ylabel("y (m)")
plt.title("Estimativa da fonte por RSSI")
plt.legend()
plt.grid(True)
plt.axis("equal")
plt.savefig("/home/ajm/Desktop/Projetos/RFMapper32/python/Resultados/Teste_de_algoritmo_estimativa_fonte.png", dpi=300, bbox_inches="tight")
print("Figura salva em Teste_de_algoritmo_estimativa_fonte.png")