# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
#======= Nível 6 ============
# Gráficos da Luminosidade e da Média
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.style as style
style.use("ggplot")
MAX_PONTOS = 60
def atualizar_grafico(ax1, ax2, canvas, raiz):
    valores_lum = []
    valores_media = []
    rssi_down = []
    rssi_up = []
    # ===================== LUMINOSIDADE =====================
    try:
        with open("medidas_luminosidade.txt", 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        valores_lum.append(float(linha))
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    # ===================== MÉDIA DA LUMINOSIDADE =====================
    try:
        with open("media_luminosidade.txt", 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        valores_media.append(float(linha))
                    except ValueError:
                        pass
    except FileNotFoundError:
        valores_media = valores_lum.copy()
    # Se existir apenas uma média gravada,
    # repete-a para acompanhar a quantidade de pontos
    if len(valores_media) == 1 and len(valores_lum) > 1:
        valores_media = [valores_media[0]] * len(valores_lum)
    # Ajusta tamanhos diferentes
    if len(valores_media) < len(valores_lum):
        if len(valores_media) > 0:
            ultimo = valores_media[-1]
            while len(valores_media) < len(valores_lum):
                valores_media.append(ultimo)
        else:
            valores_media = valores_lum.copy()
    # ===================== RSSI =====================
    try:
        with open("medidas_rssi.txt", 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        partes = linha.split()

                        if len(partes) < 2:
                            continue
                        down = float(partes[0].replace(",", "."))
                        up = float(partes[1].replace(",", "."))
                        rssi_down.append(down)
                        rssi_up.append(up)
                    except (ValueError, IndexError):
                        pass
    except FileNotFoundError:
        pass
    # ===================== JANELA DESLIZANTE =====================
    valores_lum = valores_lum[-MAX_PONTOS:]
    valores_media = valores_media[-MAX_PONTOS:]
    rssi_down = rssi_down[-MAX_PONTOS:]
    rssi_up = rssi_up[-MAX_PONTOS:]
    # ===================== GRÁFICO 1 =====================
    ax1.clear()
    if valores_lum:
        ax1.plot(
            valores_lum,
            label="Luminosidade",
            linewidth=2,
            marker='o',
            markersize=4
        )
        ax1.plot(
            valores_media,
            label="Média",
            linewidth=3
        )
        ax1.legend(loc='upper right')
        todos = valores_lum + valores_media
        val_min = min(todos)
        val_max = max(todos)
        margem = (val_max - val_min) * 0.10

        if margem == 0:
            margem = 100

        ax1.set_ylim(max(0, val_min - margem),min(4095, val_max + margem)        )
    ax1.set_title("Luminosidade e Média")
    ax1.set_ylabel("Intensidade (0-4095)")
    ax1.set_xlabel(f"Últimas {MAX_PONTOS} medidas")
    # ===================== GRÁFICO 2 =====================
    ax2.clear()
    if rssi_down:
        ax2.plot(
            rssi_down,
            label="RSSI Downlink (dBm)",
            linewidth=2,
            marker='o',
            markersize=4
        )
    if rssi_up:
        ax2.plot(
            rssi_up,
            label="RSSI Uplink (dBm)",
            linewidth=2,
            marker='s',
            markersize=4
        )
    if rssi_down or rssi_up:
        ax2.legend(loc='upper right')
        todos_rssi = rssi_down + rssi_up
        val_min = min(todos_rssi)
        val_max = max(todos_rssi)
        margem = (val_max - val_min) * 0.10
        if margem == 0:
            margem = 5
        ax2.set_ylim(max(-130, val_min - margem),min(0, val_max + margem))
    ax2.set_title("RSSI LoRa (Downlink / Uplink)")
    ax2.set_ylabel("RSSI (dBm)")
    ax2.set_xlabel(f"Últimas {MAX_PONTOS} medidas")
    # ===================== ATUALIZA =====================
    canvas.figure.subplots_adjust(hspace=0.4)
    canvas.draw()
    raiz.after(1000,atualizar_grafico,ax1,ax2,canvas,raiz)
# ===================== BOTÕES =====================
def fechar():
    if messagebox.askokcancel(
        "Sair",
        "Deseja fechar o monitor?"
    ):
        raiz.destroy()
def salvar(fig):
    arquivo = filedialog.asksaveasfilename(
        defaultextension=".png"
    )
    if arquivo:
        fig.savefig(arquivo)
# ===================== INTERFACE =====================
raiz = tk.Tk()
raiz.title("FEE247 - MONITOR LORA - LUMINOSIDADE + RSSI")
raiz.geometry("1000x700")
frame = tk.Frame(raiz)
frame.pack(fill="both", expand=True)
fig = Figure(figsize=(10, 6))
ax1 = fig.add_subplot(211)
ax2 = fig.add_subplot(212)
canvas = FigureCanvasTkAgg(fig,master=frame)
canvas.get_tk_widget().pack(fill="both",expand=True)
btn = tk.Button(raiz,text="Salvar Gráfico",command=lambda: salvar(fig))
btn.pack(pady=5)
atualizar_grafico(ax1,ax2,canvas,raiz)
raiz.protocol(
    "WM_DELETE_WINDOW",
    fechar
)

raiz.mainloop()
