#!/usr/bin/env python3
# main.py
import os
import re
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar, Separator, Checkbutton, Button, Label, Style, Frame, Entry
import geopandas as gpd
import rasterio
import rasterio.mask
from rasterio.transform import array_bounds
from rasterio.enums import Resampling
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import mapping
from shapely.ops import unary_union
from skimage import exposure
from skimage.transform import resize
import pandas as pd
import traceback
from datetime import datetime
from PIL import Image, ImageTk 
import io
from pathlib import Path # Biblioteca para lidar com caminhos de forma robusta

# =========================
# ARQUIVO DE CONFIGURAÇÃO
# =========================
CONFIG_FILE = "settings.json"

# =========================
# CONFIGURAÇÕES DE PROCESSAMENTO
# =========================
COEF_A = 360.6
COEF_B = 1.1941
BANDAS_BLUE_IDX = 1
BANDAS_GREEN_IDX = 2
BANDAS_RED_IDX = 3
BANDAS_LEITURA = [BANDAS_BLUE_IDX, BANDAS_GREEN_IDX, BANDAS_RED_IDX]

# =========================
# FUNÇÕES UTILS
# =========================
def extract_parcela_number(filename):
    m = re.search(r"Parcela\s*(\d+)\.shp", filename, re.IGNORECASE)
    return int(m.group(1)) if m else None

def normalize_visual(band, lower_perc=2, upper_perc=98, apply_clahe=True, clahe_clip=0.02):
    band_float = band.astype(np.float32)
    valid = band_float[~np.isnan(band_float)]
    if valid.size < 10: return np.zeros_like(band_float, dtype=np.uint8)

    vmin = np.percentile(valid, lower_perc)
    vmax = np.percentile(valid, upper_perc)
    if vmax <= vmin: vmax = vmin + 1e-9

    band_norm = (np.clip(band_float, vmin, vmax) - vmin) / (vmax - vmin + 1e-9)
    band_norm = np.clip(band_norm, 0.0, 1.0)
    band_norm[np.isnan(band_norm)] = 0.0

    if apply_clahe:
        try:
            band_norm = exposure.equalize_adapthist(band_norm, clip_limit=clahe_clip)
        except Exception: pass

    band_norm[np.isnan(band_norm)] = 0.0
    return (band_norm * 255).astype(np.uint8)

def get_recorte_data(dataset, geometry_list):
    try:
        recorte, out_transform = rasterio.mask.mask(
            dataset, geometry_list, crop=True, filled=True, nodata=0, indexes=BANDAS_LEITURA
        )
    except ValueError as e:
        if "Input shapes do not overlap raster" in str(e): return None, None, None, None
        raise

    out_bounds = array_bounds(recorte.shape[1], recorte.shape[2], out_transform)
    extent = (out_bounds[0], out_bounds[2], out_bounds[1], out_bounds[3])

    B = recorte[0].astype(np.float32); B[B == 0] = np.nan
    G = recorte[1].astype(np.float32); G[G == 0] = np.nan
    R = recorte[2].astype(np.float32); R[R == 0] = np.nan

    return R, G, B, extent

# =========================
# PLOTAGEM
# =========================
def gerar_plot_complexo(R_par, G_par, B_par, NIR_par, NDVI_par,
                        RGB_contexto, extent_contexto,
                        shp_contexto_gdf, shp_parcela_gdf, save_path=None):
    
    # Mude a grade para 3 linhas e 6 colunas
    fig = plt.figure(figsize=(20, 12)) 

    # --- LINHA 0: Contexto e Zoom (Preenche a linha) ---
    # Contexto: 4 colunas (à esquerda)
    ax0 = plt.subplot2grid((3, 6), (0, 0), colspan=4) 
    # Zoom: 2 colunas (à direita)
    ax1 = plt.subplot2grid((3, 6), (0, 4), colspan=2)            
    
    # --- LINHA 1: R, G, B (Centralizado, 2 colunas por plot) ---
    # Começa na coluna 0, cada um com colspan=2
    ax2 = plt.subplot2grid((3, 6), (1, 0), colspan=2) # Banda Vermelha
    ax3 = plt.subplot2grid((3, 6), (1, 2), colspan=2) # Banda Verde
    ax4 = plt.subplot2grid((3, 6), (1, 4), colspan=2) # Banda Azul

    # --- LINHA 2: NIR, NDVI (Centralizado, 3 colunas por plot) ---
    # Começa na coluna 0, cada um com colspan=3
    ax5 = plt.subplot2grid((3, 6), (2, 0), colspan=3) # NIR
    ax6 = plt.subplot2grid((3, 6), (2, 3), colspan=3) # NDVI         

    ax0.set_title("1. Mapa de Contexto (Área Total)")
    
    if RGB_contexto is not None and extent_contexto is not None:
        ax0.imshow(RGB_contexto, extent=extent_contexto)
        
        # 1. Plotar a Área Total (Amarelo)
        try: 
            shp_contexto_gdf.boundary.plot(ax=ax0, color='yellow', linewidth=2, label="Área Total")
        except Exception: 
            # Se houver erro no plot, a exceção será silenciada, mas a imagem segue.
            pass
            
        # 2. Plotar a Parcela de Interesse (Vermelho)
        try: 
            shp_parcela_gdf.boundary.plot(ax=ax0, color='red', linewidth=3, label="Parcela")
        except Exception: 
            pass
            
        # CHAVE: Adicionar a legenda para que os rótulos (label) sejam exibidos
        ax0.legend(loc='lower left', fontsize=8, facecolor='white', framealpha=0.8) # Legend call added/verified
        
        ax0.ticklabel_format(style='plain', useOffset=False)
        
    else:
        ax0.text(0.5, 0.5, "Contexto indisponível", ha='center')

    try:
        rgb_par_fil = np.dstack((normalize_visual(R_par), normalize_visual(G_par), normalize_visual(B_par)))
        ax1.imshow(rgb_par_fil)
    except Exception:
        ax1.text(0.5, 0.5, "Erro no zoom RGB", ha='center')
    ax1.axis('off')

    plots = [
        (R_par, "Banda Vermelha", "Reds", ax2),
        (G_par, "Banda Verde", "Greens", ax3),
        (B_par, "Banda Azul", "Blues", ax4),
        (NIR_par, "Banda NIR Estimada", "gray", ax5),
        (NDVI_par, "NDVI Estimado", "RdYlGn", ax6)
    ]

    for data_raw, title, cmap_name, ax in plots:
        if "NDVI" in title:
            im = ax.imshow(data_raw, cmap=cmap_name, vmin=-0.2, vmax=1.0)
            plt.colorbar(im, ax=ax, shrink=0.8)
        else:
            norm_data = normalize_visual(data_raw, lower_perc=2, upper_perc=98, apply_clahe=True)
            im = ax.imshow(norm_data, cmap=cmap_name, vmin=0, vmax=255) # Adicionado vmin/vmax para o plot

            label_text = "Refletância Normalizada (0-255)"
            if "NIR" in title:
                label_text = "Refletância Estimada (0-255)"
            
            # --- CORREÇÃO APLICADA AQUI: FORÇA OS TICKS DA BARRA DE CORES ---
            # Define os ticks em intervalos de 50, garantindo que 0 e 255 sejam exibidos.
            ticks_range = [0, 50, 100, 150, 200, 255] 
            
            plt.colorbar(im, ax=ax, shrink=0.8, ticks=ticks_range) 
            # -----------------------------------------------------------------
            
        ax.set_title(title)
        ax.axis('off')

    try:
        # Apenas limpando os subplots antigos na grade (3, 4) se existirem
        fig.delaxes(plt.subplot2grid((3, 4), (2, 2))) 
        fig.delaxes(plt.subplot2grid((3, 4), (2, 3))) 
    except Exception: pass
    
    # Adicionando rótulo principal (Suptitle)
    plt.suptitle(f"Análise: {os.path.basename(shp_parcela_gdf.filepath_or_buffer)} | Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fontsize=16)

    # 1. Usa tight_layout para ajustar o espaçamento interno e o suptitle.
    plt.tight_layout(rect=[0, 0, 1, 0.95]) 
    
    # 2. SOBRESCREVE OS VALORES DE CENTRALIZAÇÃO (EXECUÇÃO FINAL)
    # left = 0.09 e right = 0.838 (Ajuste fino para a direita)
    fig.subplots_adjust(left=0.09, right=0.838, wspace=0.15, hspace=0.25) 
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
    else:
        plt.show()

def preparar_contexto(raster_obj, caminho_shp_contexto):
    try:
        gdf_ctx = gpd.read_file(caminho_shp_contexto).to_crs(raster_obj.crs)
        geom_ctx = [unary_union(gdf_ctx.geometry)]
        Rc, Gc, Bc, extent_ctx = get_recorte_data(raster_obj, geom_ctx)
        if Rc is None: return None, None, None
        rgb_ctx_norm = np.dstack((normalize_visual(Rc), normalize_visual(Gc), normalize_visual(Bc)))
        h, w, _ = rgb_ctx_norm.shape
        max_size = 600
        scale_factor = max_size / max(h, w) if max(h,w) > 0 else 1
        if scale_factor < 1:
            rgb_resized = resize(rgb_ctx_norm, (int(h*scale_factor), int(w*scale_factor)), anti_aliasing=True, preserve_range=True).astype(np.uint8)
        else:
            rgb_resized = rgb_ctx_norm
        return rgb_resized, extent_ctx, gdf_ctx
    except Exception as e:
        print("Erro preparar_contexto:", e)
        return None, None, None

def processar_logica_geral(raster_path, shp_parcela_path, shp_contexto_path, save_path=None, show_plot=True):
    try:
        raster = rasterio.open(raster_path)
    except Exception as e:
        raise FileNotFoundError(f"Não foi possível abrir o TIFF: {e}")

    with raster:
        if raster.crs is None: raise ValueError("O TIFF não tem CRS definido.")
        rgb_ctx, extent_ctx, gdf_ctx = preparar_contexto(raster, shp_contexto_path)
        gdf_par = gpd.read_file(shp_parcela_path).to_crs(raster.crs)
        geom_par = [mapping(unary_union(gdf_par.geometry))]
        Rp, Gp, Bp, _ = get_recorte_data(raster, geom_par)
        if Rp is None: raise ValueError("A parcela está fora da área do raster selecionado.")
        with np.errstate(divide='ignore', invalid='ignore'):
            NIR_est = (COEF_A - Gp) / COEF_B
            NDVI = (NIR_est - Rp) / (NIR_est + Rp + 1e-9)
        NIR_est[np.isnan(Gp)] = np.nan
        NDVI[~np.isfinite(NDVI)] = np.nan
        gdf_par.filepath_or_buffer = shp_parcela_path 
        gerar_plot_complexo(Rp, Gp, Bp, NIR_est, NDVI, rgb_ctx, extent_ctx, gdf_ctx, gdf_par, save_path=save_path)

# =========================
# GUI 
# =========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Análise Agrícola - Mode 3")
        self.geometry("560x480") 
        self.resizable(False, False)
        self.configure(bg='#0a0a0a') 
        
        self.FONT_FAMILY = "Inter"

        # --- Carregar Configurações ---
        self.settings = self.load_settings()
        
        if self.settings.get("fullscreen", False):
            self.attributes('-fullscreen', True)

        default_dir = self.settings.get("default_dir", os.path.expanduser("~"))
        self.last_dir = {
            "folder": self.settings.get("last_dir_folder", default_dir),
            "shp_par": self.settings.get("last_dir_shp_par", default_dir),
            "shp_ctx": self.settings.get("last_dir_shp_ctx", default_dir),
            "rast": self.settings.get("last_dir_rast", default_dir)
        }
        
        # --- Estilo ttk (Dark Theme) ---
        s = Style()
        s.theme_use('clam') 

        BG_COLOR = '#0a0a0a'
        FG_COLOR = 'white'
        BUTTON_BG = '#191919'
        BUTTON_BORDER = '#3b3b3b'

        s.configure('TFrame', background=BG_COLOR)
        s.configure('TLabel', background=BG_COLOR, foreground=FG_COLOR, font=(self.FONT_FAMILY, 10))
        s.configure('Header.TLabel', font=(self.FONT_FAMILY, 18, 'bold'), foreground='white', background=BG_COLOR)
        
        s.configure('TButton', 
                    background=BUTTON_BG, 
                    foreground=FG_COLOR, 
                    font=(self.FONT_FAMILY, 10, 'bold'), 
                    borderwidth=1, 
                    relief='raised', 
                    bordercolor=BUTTON_BORDER, 
                    lightcolor=BUTTON_BORDER, 
                    darkcolor=BUTTON_BORDER,
                    padding=[10, 5] 
                   ) 
        s.map('TButton', background=[('active', '#3b3b3b')], foreground=[('active', 'white')])

        s.configure('Accent.TButton', 
                    background='#007acc', 
                    foreground='white',
                    bordercolor='#005a99',
                    lightcolor='#005a99', 
                    darkcolor='#005a99'
                   )
        s.map('Accent.TButton', background=[('active', '#0099e6')])
        
        s.configure('TSeparator', background='#3b3b3b') 
        s.configure('TProgressbar', background='#007acc', troughcolor='#3b3b3b')
        s.configure('TCheckbutton', background=BG_COLOR, foreground=FG_COLOR, font=(self.FONT_FAMILY, 10))
        s.map('TCheckbutton', background=[('active', BG_COLOR)])

        s.configure('Preview.TLabel', background='#191919', foreground='#3b3b3b', padding=[10, 20])

        container = Frame(self, style='TFrame')
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (StartPage, ManualPage, AutomaticPage, SettingsPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("StartPage")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()

    def load_settings(self):
        default_settings = {
            "fullscreen": False,
            "remember_last_dir": True,
            "default_dir": os.path.expanduser("~")
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return default_settings
        return default_settings

    def save_settings(self):
        if self.settings.get("remember_last_dir", True):
            self.settings["last_dir_folder"] = self.last_dir["folder"]
            self.settings["last_dir_shp_par"] = self.last_dir["shp_par"]
            self.settings["last_dir_shp_ctx"] = self.last_dir["shp_ctx"]
            self.settings["last_dir_rast"] = self.last_dir["rast"]
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")

    def update_last_dir(self, key, path):
        if os.path.isdir(path):
            self.last_dir[key] = path
        else:
            self.last_dir[key] = os.path.dirname(path)

class StartPage(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style='TFrame')
        self.controller = controller
        
        Label(self, text="Processador de NDVI & NIR", style='Header.TLabel').pack(pady=20)
        
        Button(self, text="Modo Manual (Visualizar)", style='Accent.TButton', 
               width=28, command=lambda: controller.show_frame("ManualPage")).pack(pady=8, ipady=10)
        Button(self, text="Modo Automático (Lote)", style='Accent.TButton', 
               width=28, command=lambda: controller.show_frame("AutomaticPage")).pack(pady=8, ipady=10)
        
        Button(self, text="Configurações", width=28, 
               command=lambda: controller.show_frame("SettingsPage")).pack(pady=8, ipady=5)
        
        Separator(self, orient='horizontal').pack(fill='x', padx=60, pady=15)
        Button(self, text="Sair", width=20, command=self.quit).pack(pady=5, ipady=5)

class SettingsPage(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style='TFrame')
        self.controller = controller
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        
        row = 0
        Label(self, text="Configurações", font=(controller.FONT_FAMILY, 16, "bold"), foreground='white').grid(row=row, column=1, pady=20)
        row += 1

        self.var_fullscreen = tk.BooleanVar(value=controller.settings.get("fullscreen", False))
        self.var_remember = tk.BooleanVar(value=controller.settings.get("remember_last_dir", True))
        self.var_default_dir = tk.StringVar(value=controller.settings.get("default_dir", os.path.expanduser("~")))

        cb_full = Checkbutton(self, text="Modo Tela Cheia", variable=self.var_fullscreen, 
                              style='TCheckbutton', command=self.toggle_fullscreen)
        cb_full.grid(row=row, column=1, sticky='w', pady=10)
        row += 1

        cb_rem = Checkbutton(self, text="Salvar o último diretório após processar", variable=self.var_remember, 
                             style='TCheckbutton', command=self.save_changes)
        cb_rem.grid(row=row, column=1, sticky='w', pady=10)
        row += 1

        Separator(self, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', padx=40, pady=15)
        row += 1

        Label(self, text="Diretório Padrão (Início):").grid(row=row, column=1, sticky='w', pady=(5,0))
        row += 1
        
        def choose_default_dir():
            path = filedialog.askdirectory()
            if path:
                self.var_default_dir.set(path)
                self.save_changes()
                # CORREÇÃO: Atualiza instantaneamente o dicionário do controlador
                self.controller.settings["default_dir"] = path
                if not self.var_remember.get():
                    # Se não for para lembrar, força todos os diretórios atuais para o novo padrão
                    for key in controller.last_dir:
                        controller.last_dir[key] = path

        Button(self, text="Selecionar Pasta Padrão", width=25, command=choose_default_dir).grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        Label(self, textvariable=self.var_default_dir, foreground='#6aa84f', wraplength=400).grid(row=row, column=1, sticky='w', pady=(0, 10))
        row += 1

        Separator(self, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', padx=40, pady=20)
        row += 1
        Button(self, text="< Voltar", width=20, command=lambda: controller.show_frame("StartPage")).grid(row=row, column=1, pady=10)

    def toggle_fullscreen(self):
        state = self.var_fullscreen.get()
        self.controller.attributes('-fullscreen', state)
        self.save_changes()

    def save_changes(self):
        self.controller.settings["fullscreen"] = self.var_fullscreen.get()
        self.controller.settings["remember_last_dir"] = self.var_remember.get()
        self.controller.settings["default_dir"] = self.var_default_dir.get()
        self.controller.save_settings()

class ManualPage(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style='TFrame')
        self.controller = controller
        
        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_columnconfigure(2, weight=1) 
        
        self.current_row = 0
        self.img_tk = None 

        Button(self, text="<", width=2, command=lambda: controller.show_frame("StartPage")).grid(
            row=self.current_row, column=0, sticky='w', padx=(20, 0), pady=15, ipady=1
        )
        self.current_row += 1

        self.preview_label = Label(self, text="Pré-visualização TIFF", anchor='center', style='Preview.TLabel')
        self.preview_label.grid(row=self.current_row, column=1, pady=30)
        self.current_row += 1 
        

        self.v_shp_par = tk.StringVar()
        self.v_shp_ctx = tk.StringVar()
        self.v_rast = tk.StringVar()
        VAR_COLOR = '#6aa84f'

        self.build_input_group("Shapefile da Parcela (alvo - *.shp):", "Selecionar Parcela", self.v_shp_par, "shp_par", [("Shapefile", "*.shp")], VAR_COLOR)
        self.build_input_group("Shapefile de Contexto (Área Geral - *.shp):", "Selecionar Contexto", self.v_shp_ctx, "shp_ctx", [("Shapefile", "*.shp")], VAR_COLOR)
        self.build_input_group("Imagem TIFF (Mosaico/Ortofoto - *.tif/*.tiff):", "Selecionar TIFF", self.v_rast, "rast", [("Tiff", "*.tif *.tiff")], VAR_COLOR)
        
        Button(self, text="Processar", style='Accent.TButton', 
               command=self.run_manual, width=20).grid(row=self.current_row, column=1, pady=15, ipady=8)
        self.current_row += 1
        

    def update_tif_preview(self):
        shp_par_path = self.v_shp_par.get()
        shp_ctx_path = self.v_shp_ctx.get()
        rast_path = self.v_rast.get()

        if not shp_ctx_path or not rast_path:
            self.preview_label.config(image='', text="Selecione TIFF e Contexto", style='Preview.TLabel')
            self.img_tk = None
            return

        self.preview_label.config(image='', text="Carregando...", style='Preview.TLabel', foreground='#007acc')
        self.update_idletasks()

        try:
            with rasterio.open(rast_path) as src:
                if src.count < 3: raise ValueError("Raster precisa de 3 bandas (RGB).")
                
                gdf_ctx = gpd.read_file(shp_ctx_path).to_crs(src.crs)
                geom_ctx = [mapping(unary_union(gdf_ctx.geometry))]
                
                if shp_par_path and os.path.exists(shp_par_path):
                    gdf_par = gpd.read_file(shp_par_path).to_crs(src.crs)
                else:
                    gdf_par = None
                    
                recorte, out_transform = rasterio.mask.mask(
                    src, geom_ctx, crop=True, filled=True, nodata=0, indexes=BANDAS_LEITURA
                )
                
                R = recorte[2].astype(np.float32); R[R == 0] = np.nan
                G = recorte[1].astype(np.float32); G[G == 0] = np.nan
                B = recorte[0].astype(np.float32); B[B == 0] = np.nan
                rgb_ctx_norm = np.dstack((normalize_visual(R), normalize_visual(G), normalize_visual(B)))

                out_bounds = array_bounds(recorte.shape[1], recorte.shape[2], out_transform)
                extent = (out_bounds[0], out_bounds[2], out_bounds[1], out_bounds[3])

                fig, ax = plt.subplots(figsize=(4, 4)) 
                ax.imshow(rgb_ctx_norm, extent=extent, vmin=0, vmax=255) 
                ax.axis('off')

                if gdf_par is not None:
                    gdf_par.boundary.plot(ax=ax, color='red', linewidth=3)
                    
                ax.set_xlim(extent[0], extent[1])
                ax.set_ylim(extent[2], extent[3])
                
                plt.tight_layout(pad=0)
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
                plt.close(fig)
                
                buf.seek(0)
                img = Image.open(buf)
                img.thumbnail((200, 200))
                tk_img = ImageTk.PhotoImage(img)
                
                self.img_tk = tk_img 
                self.preview_label.config(image=self.img_tk, text="", style='TLabel')
                
        except Exception as e:
            msg = f"Erro: {str(e)}"
            self.preview_label.config(image='', text=msg, style='Preview.TLabel', foreground='red')
            self.img_tk = None

    def build_input_group(self, label_text, button_text, var_control, dir_key, filetypes, var_color):
        row = self.current_row 
        Label(self, text=label_text).grid(row=row, column=0, columnspan=3, pady=(5,0)) 
        row += 1

        def open_dialog(target_var=var_control, key=dir_key):
            if self.controller.settings.get("remember_last_dir", True):
                initial_dir = self.controller.last_dir.get(key, self.controller.settings.get("default_dir"))
            else:
                initial_dir = self.controller.settings.get("default_dir", os.path.expanduser("~"))

            if key == 'folder':
                path = filedialog.askdirectory(initialdir=initial_dir)
            else:
                path = filedialog.askopenfilename(initialdir=initial_dir, filetypes=filetypes)
            
            if path:
                # --- COMPARAÇÃO ROBUSTA USANDO PATHLIB ---
                try:
                    path_obj = Path(path).resolve()
                    current_val = target_var.get()
                    current_obj = Path(current_val).resolve() if current_val else Path(".")
                    
                    # Se o usuário selecionou exatamente o mesmo arquivo que já está no campo
                    if path_obj == current_obj and current_val != "":
                        messagebox.showinfo("Arquivo Repetido", f"O arquivo já está selecionado:\n\n{path_obj.name}")
                        return # Interrompe aqui
                except Exception:
                    # Fallback se der erro na resolução do caminho
                    pass

                # Se passou, atualiza
                target_var.set(path)
                
                if self.controller.settings.get("remember_last_dir", True):
                    self.controller.update_last_dir(key, path)
                
                if hasattr(self, 'update_tif_preview') and key in ['rast', 'shp_ctx', 'shp_par']:
                    self.update_tif_preview()

        Button(self, text=button_text, command=open_dialog, width=15).grid(row=row, column=1, pady=2)
        row += 1
        Label(self, textvariable=var_control, foreground=var_color, wraplength=520, justify="center").grid(row=row, column=1, padx=20)
        row += 1
        self.current_row = row 

    def run_manual(self):
        shp_par = self.v_shp_par.get()
        shp_ctx = self.v_shp_ctx.get()
        rast = self.v_rast.get()
        if not all([shp_par, shp_ctx, rast]):
            messagebox.showwarning("Aviso", "Preencha os 3 campos antes de processar.")
            return
        try:
            self.controller.update_idletasks() 
            processar_logica_geral(rast, shp_par, shp_ctx, save_path=None, show_plot=True)
            
            # SALVAR O DIRETÓRIO APENAS APÓS O SUCESSO (Salvar o arquivo escolhido como último)
            if self.controller.settings.get("remember_last_dir", True):
                # Atualiza explicitamente o last_dir com os arquivos usados
                self.controller.update_last_dir("shp_par", shp_par)
                self.controller.update_last_dir("shp_ctx", shp_ctx)
                self.controller.update_last_dir("rast", rast)
                self.controller.save_settings()

        except Exception as e:
            print("--- ERRO MANUAL ---")
            print(traceback.format_exc())
            messagebox.showerror("Erro", f"Falha no processamento manual:\n{e}")

class AutomaticPage(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style='TFrame')
        self.controller = controller

        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_columnconfigure(2, weight=1) 
        self.current_row = 0
        
        self.v_folder = tk.StringVar()
        self.v_shp_ctx = tk.StringVar()
        self.v_rast = tk.StringVar()
        
        Label(self, text="Modo Automático (Lote)", font=(controller.FONT_FAMILY, 14, "bold"), foreground='white').grid(row=self.current_row, column=1, pady=15)
        self.current_row += 1
        
        VAR_COLOR = '#6aa84f'

        self.build_input_group("Pasta com Parcelas (*.shp):", "Selecionar Pasta", self.v_folder, "folder", [], VAR_COLOR) 
        self.build_input_group("Shapefile de Contexto (Área Geral - *.shp):", "Selecionar Contexto", self.v_shp_ctx, "shp_ctx", [("Shapefile", "*.shp")], VAR_COLOR)
        self.build_input_group("Imagem TIFF (Mosaico/Ortofoto - *.tif/*.tiff):", "Selecionar TIFF", self.v_rast, "rast", [("Tiff", "*.tif *.tiff")], VAR_COLOR)
        
        cb = Checkbutton(self, text="Salvar relatório CSV consolidado (por parcela)", variable=tk.IntVar(value=0), style='TCheckbutton')
        cb.grid(row=self.current_row, column=1, pady=(12,0), sticky='w')
        self.v_savecsv = tk.IntVar(value=0) 
        self.current_row += 1

        Label(self, text="Progresso:").grid(row=self.current_row, column=1, pady=(10,0))
        self.v_prog = tk.IntVar()
        self.current_row += 1
        
        Progressbar(self, variable=self.v_prog, length=480, style='TProgressbar').grid(row=self.current_row, column=1, pady=6)
        self.current_row += 1

        Button(self, text="INICIAR LOTE (SALVAR PNGs)", style='Accent.TButton', 
               command=self.run_automatico, width=35).grid(row=self.current_row, column=1, pady=10, ipady=8)
        self.current_row += 1
        
        Button(self, text="< Voltar", width=20, command=lambda: controller.show_frame("StartPage")).grid(row=self.current_row, column=1, pady=5, ipady=3)

    # Reutiliza a lógica robusta de build_input_group
    def build_input_group(self, label_text, button_text, var_control, dir_key, filetypes, var_color):
        row = self.current_row 
        Label(self, text=label_text).grid(row=row, column=0, columnspan=3, pady=(5,0)) 
        row += 1

        def open_dialog(target_var=var_control, key=dir_key):
            if self.controller.settings.get("remember_last_dir", True):
                initial_dir = self.controller.last_dir.get(key, self.controller.settings.get("default_dir"))
            else:
                initial_dir = self.controller.settings.get("default_dir", os.path.expanduser("~"))

            if key == 'folder':
                path = filedialog.askdirectory(initialdir=initial_dir)
            else:
                path = filedialog.askopenfilename(initialdir=initial_dir, filetypes=filetypes)
            
            if path:
                try:
                    path_obj = Path(path).resolve()
                    current_val = target_var.get()
                    current_obj = Path(current_val).resolve() if current_val else Path(".")
                    
                    if path_obj == current_obj and current_val != "":
                        messagebox.showinfo("Arquivo Repetido", f"O arquivo já está selecionado:\n\n{path_obj.name}")
                        return 
                except Exception: pass

                target_var.set(path)
                if self.controller.settings.get("remember_last_dir", True):
                    self.controller.update_last_dir(key, path)

        Button(self, text=button_text, command=open_dialog, width=28).grid(row=row, column=1, pady=2)
        row += 1
        Label(self, textvariable=var_control, foreground=var_color, wraplength=520, justify="center").grid(row=row, column=1, padx=20)
        row += 1
        self.current_row = row 

    def run_automatico(self):
        folder = self.v_folder.get()
        shp_ctx = self.v_shp_ctx.get()
        raster = self.v_rast.get()
        save_csv_flag = bool(self.v_savecsv.get())

        if not all([folder, shp_ctx, raster]):
            messagebox.showwarning("Aviso", "Preencha todos os campos antes de iniciar o lote.")
            return

        try:
            arquivos = sorted([f for f in os.listdir(folder) if f.lower().endswith(".shp")],
                              key=lambda x: (extract_parcela_number(x) if extract_parcela_number(x) is not None else 9999, x))
            total = len(arquivos)
            if total == 0:
                messagebox.showwarning("Aviso", "Nenhum arquivo .shp encontrado na pasta selecionada.")
                return

            csv_rows = []
            self.v_prog.set(0)
            
            for i, shp in enumerate(arquivos):
                full_shp = os.path.join(folder, shp)
                out_png = os.path.join(folder, f"Resultado_{os.path.splitext(shp)[0]}.png")

                try:
                    processar_logica_geral(raster, full_shp, shp_ctx, save_path=out_png, show_plot=False)
                except Exception as e:
                    print(f"Erro processando {shp}: {e}")
                
                if save_csv_flag:
                    try:
                        with rasterio.open(raster) as ds:
                            gdf_par = gpd.read_file(full_shp).to_crs(ds.crs)
                            geom = [mapping(unary_union(gdf_par.geometry))]
                            rec, _ = rasterio.mask.mask(ds, geom, crop=True, filled=True, nodata=0, indexes=BANDAS_LEITURA)
                            rec = rec.astype(np.float32)
                            R = rec[2]; G = rec[1]; B = rec[0]
                            R[R==0] = np.nan; G[G==0] = np.nan; B[B==0] = np.nan
                            
                            with np.errstate(divide='ignore', invalid='ignore'):
                                NIR_est = (COEF_A - G) / COEF_B
                                NDVI = (NIR_est - R) / (NIR_est + R + 1e-9)
                            
                            def stats(arr):
                                valid = arr[~np.isnan(arr)]
                                if valid.size == 0: return [np.nan]*7
                                return [float(np.nanmean(valid)), float(np.nanmedian(valid)), float(np.nanstd(valid)),
                                        float(np.nanmin(valid)), float(np.nanmax(valid)),
                                        float(np.nanpercentile(valid,25)), float(np.nanpercentile(valid,75))]
                                        
                            r_stats = stats(R); g_stats = stats(G); b_stats = stats(B); ndvi_stats = stats(NDVI)
                            row = {"Parcela": os.path.splitext(shp)[0]}
                            row.update({f"R_{k}": v for k,v in zip(["mean","median","std","min","max","p25","p75"], r_stats)})
                            row.update({f"G_{k}": v for k,v in zip(["mean","median","std","min","max","p25","p75"], g_stats)})
                            row.update({f"B_{k}": v for k,v in zip(["mean","median","std","min","max","p25","p75"], b_stats)})
                            row.update({f"NDVI_{k}": v for k,v in zip(["mean","median","std","min","max","p25","p75"], ndvi_stats)})
                            csv_rows.append(row)
                    except Exception as e:
                        print(f"Erro stats {shp}: {e}")

                self.v_prog.set(int((i+1)/total * 100))
                self.update_idletasks()

            if save_csv_flag and csv_rows:
                try:
                    df = pd.DataFrame(csv_rows)
                    csv_out = os.path.join(folder, "relatorio_consolidado_parcelas.csv")
                    df.to_csv(csv_out, index=False, float_format="%.6f")
                    messagebox.showinfo("Concluído", f"Lote finalizado. CSV salvo em:\n{csv_out}")
                except Exception as e:
                    messagebox.showwarning("Aviso", f"Lote finalizado. Falha ao salvar CSV: {e}")
            else:
                messagebox.showinfo("Concluído", f"Lote finalizado. {total} parcelas processadas.")
            
            # SALVA SETTINGS APÓS SUCESSO
            self.controller.save_settings()

        except Exception as e:
            print("--- ERRO AUTOMÁTICO ---")
            print(traceback.format_exc())
            messagebox.showerror("Erro Fatal", f"Erro durante processamento em lote:\n{e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()