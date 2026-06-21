# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
#======= Nível 6 ============
# Comando do LED amarelo
import tkinter as tk
import os
# Define o caminho do arquivo no MESMO diretório do script
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_arquivo = os.path.join(diretorio_atual, "cmd_led_amarelo.txt")
# Função para salvar o valor
def salvar_valor(valor):
    with open(caminho_arquivo, "w") as f:
        f.write(str(valor))
    print(f"Valor {valor} salvo em: {caminho_arquivo}")
# Criando a janela
janela = tk.Tk()
janela.title("Controle LED Amarelo")
janela.geometry("300x150")
# Variável da opção
opcao = tk.IntVar(value=0)
# Interface
tk.Label(janela, text="Selecione 0 ou 1:", font=("Arial", 12)).pack(pady=10)
tk.Radiobutton(janela, text="0", variable=opcao, value=0).pack()
tk.Radiobutton(janela, text="1", variable=opcao, value=1).pack()
tk.Button(janela, text="Salvar",
          command=lambda: salvar_valor(opcao.get())).pack(pady=10)
# Executa
janela.mainloop()
