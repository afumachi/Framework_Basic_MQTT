# CURSO FEE247 Turma 3
# EXP_MQTT com MAC centralizada
# Versão MQTT - Comunicação via broker público HiveMQ (broker.hivemq.com:1883)
# 
# ======================================================================
#
# Última versão: PKLoRa MQTT - 21-06-2026
# Branquinho / Luís Felipe / Anderson
# 
# ======================================================================

# ===== Bibliotecas =====
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import time
from time import localtime, strftime
import os
import threading

# ===== Configurações MQTT =====
BROKER        = "broker.hivemq.com"
PORTA_MQTT    = 1883

# MODIFIQUE O TOPIC_DL E TOPIC_UL de acordo com SEU_NOME
TOPIC_DL      = "mot_lora_SEU_NOME/gateway/downlink"   # N2_N3 publica → Gateway PKLoRa assina
TOPIC_UL      = "mot_lora_SEU_NOME/gateway/uplink"     # Gateway PKLoRa assina  → N2_N3 assina

# ===== Variáveis globais =====
Tamanho_pacote = 20

# Evento para sinalizar chegada de Pacote UL
Pacote_UL_status = threading.Event()
Pacote_UL_payload = bytearray(Tamanho_pacote)

# ===== Callback MQTT =====
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[PKLoRa MQTT] Conectado ao broker HiveMQ com sucesso.")
        client.subscribe(TOPIC_UL)
        print(f"[PKLoRa MQTT] Inscrito no tópico: {TOPIC_UL}")
    else:
        print(f"[PKLoRa MQTT] Falha na conexão. Código: {reason_code}")

def on_message(client, userdata, msg):
    """Callback disparado ao receber pacote UL vindo do Gateway."""
    global Pacote_UL_payload
    payload = msg.payload
    if len(payload) >= Tamanho_pacote:
        Pacote_UL_payload = bytearray(payload[:Tamanho_pacote])
        Pacote_UL_status.set()   # Sinaliza que chegou um pacote válido

def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"[PKLoRa MQTT] Desconectado inesperadamente (rc={reason_code}). Tentando se reconectar...")

# ===== Inicialização do cliente MQTT =====
client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect

print("[PKLoRa MQTT] N2_N3 Conectando ao broker.hivemq.com via porta 1883")
client.connect(BROKER, PORTA_MQTT, keepalive=60)
client.loop_start()   # Thread de fundo para receber mensagens

# Aguarda conexão ser estabelecida com o Broker MQTT
time.sleep(2)

# ===== Arquivos de saída =====
Grava_log = 0

arquivo_gerencia = "medidas_rssi.txt"
arquivo_cliente = "medidas_luminosidade.txt"

# ===== Parâmetros de rede / camadas =====
ID_sensor      = 1
ID_gateway     = 0
Tempo_entre_pacotes = 2   # segundos (colocado no byte 4 do DL) de espera pelo pacote UL após envio do DL

# ===== Loop principal: repete pedindo número de medidas =====
print("\n========== Gateway PKLoRa - Comunicação MQTT ==========")
try:
    while True:

        # ----- Entrada do usuário -----
        num_medidas = input("\nEntre com o número de medidas (0 para sair): ").strip()
        if num_medidas == "0":
            print("Encerrando...")
            break
        try:
            medidas = int(num_medidas)
        except ValueError:
            print("Valor inválido. Entre novamente.")
            continue

        # ----- Limpa arquivos temporários a cada teste -----
        for arq in [arquivo_gerencia, arquivo_cliente]:
            if os.path.exists(arq):
                os.remove(arq)

        # ----- Grava arquivos temporários a cada teste -----        
        if Grava_log == 1:
            arquivo_log = strftime("B_Medidas_%Y_%m_%d_%H-%M-%S.txt")
            Log_dados = open(arquivo_log, 'w')
            print(f"Arquivo de log: {arquivo_log}")
            print('Time stamp;Contador;RSSI_DL;RSSI_UL;SNR_DL;SNR_UL;Luminosidade;LED', file=Log_dados)

        Contador_Pacote_DL  = 0
        perda_pacote        = 0
        Comando_LED_amarelo = 0

        # ----- Montagem e envio dos pacotes -----
        for j in range(1, medidas + 1):

            # -------- Camada de Aplicação DL: lê comando LED --------
            try:
                with open("cmd_led_amarelo.txt", "r") as f:
                    linha = f.readline().strip()
                    Comando_LED_amarelo = 1 if linha == "1" else 0
            except Exception:
                Comando_LED_amarelo = 0

            # -------- Monta pacote DL de 20 bytes --------
            Pacote_DL = bytearray(Tamanho_pacote)

            # Camada MAC
            Pacote_DL[4]  = Tempo_entre_pacotes

            # Camada de Rede
            Pacote_DL[8]  = ID_sensor
            Pacote_DL[9]  = ID_gateway
            
            # Camada de Transporte
            Contador_Pacote_DL = (Contador_Pacote_DL + 1) % 256
            Pacote_DL[12] = Contador_Pacote_DL

            # Camada de Aplicação
            Pacote_DL[16] = Comando_LED_amarelo

            # -------- Publica pacote DL no broker MQTT --------
            Pacote_UL_status.clear()
            result = client.publish(TOPIC_DL, bytes(Pacote_DL))
            result.wait_for_publish()
            print(f"Pacote [DL] {j:03d} publicado no broker | LED AMARELO = {Comando_LED_amarelo}")

            # Aguarda antes do próximo ciclo de pacotes DL-UL
            time.sleep(Tempo_entre_pacotes)
            
            # -------- Aguarda novo pacote UL (timeout = Tempo_entre_pacotes) --------
            Pacote_UL_novo = Pacote_UL_status.wait(timeout=Tempo_entre_pacotes)

            if Pacote_UL_novo:
                Pacote_UL = Pacote_UL_payload

                # -------- Decodifica RSSI DL (byte 0) --------
                rssi_dl_bruto = Pacote_UL[0]
                RSSI_DL = ((rssi_dl_bruto - 256) / 2.0) - 74 if rssi_dl_bruto > 128 else (rssi_dl_bruto / 2.0) - 74

                # -------- Decodifica SNR DL (byte 1) --------
                SNR_DL = ((Pacote_UL[1] / 4) - 30)

                # -------- Decodifica RSSI UL (byte 2) --------
                rssi_ul_bruto = Pacote_UL[2]
                RSSI_UL = ((rssi_ul_bruto - 256) / 2.0) - 74 if rssi_ul_bruto > 128 else (rssi_ul_bruto / 2.0) - 74

                # -------- Decodifica SNR UL (byte 3) --------
                SNR_UL = ((Pacote_UL[3] / 4) - 30)

                # -------- Camada de Aplicação: Luminosidade (bytes 18-19) --------
                luminosidade = Pacote_UL[18] * 256 + Pacote_UL[19]

                print(f"Pacote [UL] {j:03d} | RSSI_DL={RSSI_DL:.1f} dBm | RSSI_UL={RSSI_UL:.1f} dBm | SNR_DL={SNR_DL:.1f} dB | SNR_UL={SNR_UL:.1f} dB | Lum={luminosidade} | LED={Comando_LED_amarelo}")

                # Salva dados em arquivo
                with open(arquivo_gerencia, 'a+') as f:
                    print(RSSI_DL, RSSI_UL, file=f)
                with open(arquivo_cliente, 'a+') as f:
                    print(luminosidade, file=f)

                if Grava_log == 1:
                    print(f"{time.asctime()};{j};{RSSI_DL};{RSSI_UL};{SNR_DL};{SNR_UL};{luminosidade};{Comando_LED_amarelo}", file=Log_dados)
            else:
                perda_pacote = perda_pacote + 1
                print(f"Pacote [UL] {j:03d} | TIMEOUT - Pacote UL não recebido")
                with open(arquivo_gerencia, 'a+') as f:
                    print(f"{j};;{perda_pacote}", file=f)

                if Grava_log == 1:
                    print(f"{time.asctime()};{j};;", file=Log_dados)


        # ===== Resumo do Teste =====
        PSR = (1.00 - (perda_pacote / medidas)) * 100
        print(f"\nTeste concluído: {medidas} Pacotes DL enviados | {perda_pacote} Pacotes Perdidos | PSR {PSR} %")

        if Grava_log == 1:
            Log_dados.close()

# Interrompe a aplicação N2_N3 e a conexão com MQTT
except KeyboardInterrupt:
    print("\n[Ctrl + C] Interrompido pelo usuário.")
finally:
    client.loop_stop()
    client.disconnect()
    print("[PKLoRa MQTT] Desconectado do broker.")
