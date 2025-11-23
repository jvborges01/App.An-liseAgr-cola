import tkinter as tk
from tkinter import filedialog, messagebox
import os
import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.ops import unary_union
import matplotlib.pyplot as plt

# --- Constantes de cálculo ---
PARCELA_ID = 1
COEF_A = 360.6
COEF_B = 1.1941
BANDA_RED_IDX = 3
BANDA_GREEN_IDX = 2

# --- Funções geoespaciais ---
def carregar_e_calcular_ndvi(tiff_path, shp_path):
    if not os.path.exists(tiff_path) or not os.path.exists(shp_path):
        messagebox.showerror("Erro", "Arquivos TIFF ou SHP não encontrados!")
        return None, None

    with rasterio.open(tiff_path) as dataset:
        crs = dataset.crs
        nodata = dataset.nodata if dataset.nodata is not None else 0

        # Carrega shapefile e reprojeta
        shapes = gpd.read_file(shp_path).to_crs(crs)
        geometria = [unary_union(shapes.geometry)]

        # Recorta bandas Red e Green
        recorte, _ = mask(dataset, geometria, crop=True, nodata=nodata, indexes=[BANDA_RED_IDX, BANDA_GREEN_IDX])
        red_raw = recorte[0].astype(float)
        green_raw = recorte[1].astype(float)
        red_raw[red_raw == nodata] = np.nan
        green_raw[green_raw == nodata] = np.nan

        # Calcula NIR estimado
        nir_estimado = (COEF_A - green_raw) / COEF_B

        # Calcula NDVI
        with np.errstate(divide='ignore', invalid='ignore'):
            ndvi = (nir_estimado - red_raw) / (nir_estimado + red_raw)
            ndvi[np.isnan(red_raw) | np.isnan(green_raw)] = np.nan

        return red_raw, ndvi

# --- Função de MVLF ---
def calcular_mvlf(ndvi_p25):
    coef_angular = 13147.5532
    intercepto = -557.5606
    mvlf = max(0, coef_angular * ndvi_p25 + intercepto)
    return mvlf

# --- Função de Processamento e Plot ---
def processar_e_plotar(tiff_path, shp_path):
    red_raw, ndvi = carregar_e_calcular_ndvi(tiff_path, shp_path)
    if ndvi is None:
        return

    ndvi_valido = ndvi[~np.isnan(ndvi)]
    if ndvi_valido.size == 0:
        messagebox.showwarning("Aviso", "NDVI inválido!")
        return

    ndvi_p25 = np.percentile(ndvi_valido, 25)
    mvlf_estimada = calcular_mvlf(ndvi_p25)

    # --- Criação do gráfico ---
    ndvi_simulado = np.linspace(0, 1, 50)
    mvlf_simulado = 13147.5532 * ndvi_simulado - 557.5606

    plt.figure(figsize=(8,6))
    plt.plot(ndvi_simulado, mvlf_simulado, 'r-', label="Regressão MVLF")
    plt.scatter(ndvi_p25, mvlf_estimada, color='blue', s=80, label=f"Ponto Parcela {PARCELA_ID}")
    plt.xlabel("NDVI-P25")
    plt.ylabel("MVLF (kg/ha)")
    plt.title("Estimativa de MVLF vs NDVI")
    plt.grid(True)
    plt.legend()
    plt.show()

    messagebox.showinfo("Resultados",
                        f"NDVI-P25: {ndvi_p25:.4f}\nMVLF estimada: {mvlf_estimada:.2f} kg/ha")

# --- GUI ---
def selecionar_arquivo(tipo):
    if tipo == "TIFF":
        return filedialog.askopenfilename(
            title="Selecione o TIFF",
            filetypes=[("Arquivos TIFF", ("*.tif", "*.tiff"))]
        )
    elif tipo == "SHP":
        return filedialog.askopenfilename(
            title="Selecione o SHP",
            filetypes=[("Shapefiles", "*.shp")]
        )
def main():
    root = tk.Tk()
    root.title("Estimativa de MVLF")

    v_tiff = tk.StringVar()
    v_shp = tk.StringVar()

    tk.Label(root, text="Arquivo TIFF:").pack()
    tk.Entry(root, textvariable=v_tiff, width=50, state='readonly').pack()
    tk.Button(root, text="Selecionar TIFF", command=lambda: v_tiff.set(selecionar_arquivo("TIFF"))).pack(pady=5)

    tk.Label(root, text="Arquivo SHP:").pack()
    tk.Entry(root, textvariable=v_shp, width=50, state='readonly').pack()
    tk.Button(root, text="Selecionar SHP", command=lambda: v_shp.set(selecionar_arquivo("SHP"))).pack(pady=5)

    tk.Button(root, text="Processar & Plotar", 
              command=lambda: processar_e_plotar(v_tiff.get(), v_shp.get()),
              bg="green", fg="white", font=("Helvetica", 12)).pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()
