# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
#======= Nível 5 ============
#Calcula a média da luminosidade
import time
import os
arquivo_entrada = "medidas_luminosidade.txt"
arquivo_saida = "media_luminosidade.txt"
# Aguarda o arquivo ser criado
while not os.path.exists(arquivo_entrada):
    print("Aguardando criação do arquivo medidas_luminosidade.txt...")
    time.sleep(1)
print("Arquivo encontrado.")
while True:
    try:
        luminosidades = []
        with open(arquivo_entrada, "r") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        luminosidades.append(float(linha))
                    except ValueError:
                        pass
        if luminosidades:
            soma = 0.0
            with open(arquivo_saida, "w") as f_media:
                for i, valor in enumerate(luminosidades):
                    soma += valor
                    media = soma / (i + 1)
                    # grava somente a média na linha
                    f_media.write(f"{media:.2f}\n")
            print(
                f"Luminosidade = {luminosidades[-1]:.2f} | "
                f"Amostras = {len(luminosidades)} | "
                f"Média = {media:.2f}"
            )
    except Exception as erro:
        print(f"Erro: {erro}")

    time.sleep(1)
