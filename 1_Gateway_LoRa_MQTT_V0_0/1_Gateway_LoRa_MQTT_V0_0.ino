/*
//  MoT LoRa MQTT | WissTek IoT
//  Versão MQTT: Comunicação Python↔Gateway via broker.hivemq.com
//  - Mantém toda a camada de rádio LoRa (RFM95)
//  - Substitui USB/Serial por Wi-Fi + MQTT
//
//  Versão MQTT: comunicação via broker.hivemq.com:1883
//  - DL: assina "mot_lora_SEU_NOME/gateway/downlink"  ← recebe do Python
//  - UL: publica em "mot_lora_SEU_NOME/gateway/uplink" → envia ao Python
//  As funções de rádio LoRa (Phy_radio_send_DL / Phy_radio_receive_UL)
//  permanecem idênticas à versão Framework Basic.
//
//  Última Modificação: Branquinho / Felipe / Luís Felipe / Anderson - 21/06/2026
//
*/

//  =====================================================================
//  1 - Bibliotecas
//  =====================================================================
//  Bibliotecas LoRa Framework Basic
#include <SPI.h>
#include <LoRa.h>

//  Bibliotecas adicionais para conexão Wi-Fi + MQTT
#include <WiFi.h>
#include <WiFiMulti.h>
#include <PubSubClient.h>

//   =====================================================================
//   2 - Configurações Wi-Fi
//   =====================================================================
//  Instancia o objeto WiFiMulti
WiFiMulti wifiMulti;

//  =====================================================================
//  3 - Configurações MQTT
//  =====================================================================
const char* MQTT_BROKER   = "broker.hivemq.com";
const int   MQTT_PORT     = 1883;

// ***** MODIFIQUE O TOPIC_DL E TOPIC_UL de acordo com NOME do usuário ****
const char* TOPIC_DL      = "mot_lora_SEU_NOME/gateway/downlink";  // Python → ESP32
const char* TOPIC_UL      = "mot_lora_SEU_NOME/gateway/uplink";    // ESP32  → Python
String CLIENT_ID ;                                                 // ID único no broker

//  =====================================================================
//  4 - Pinagem RFM95 (Kit PKLORa)
//  =====================================================================
#define SCK_PIN    5
#define MISO_PIN  19
#define MOSI_PIN  27
#define NSS_PIN   18
#define RST_PIN   14
#define DIO0_PIN  26

//  =====================================================================
//  5 - Parâmetros LoRa
//  =====================================================================
#define FREQUENCY_IN_HZ       915E6
#define txPower               17
#define spreadingFactor       7
#define signalBandwidth       500E3
#define codingRateDenominator 5

//  =====================================================================
//  6 - Pinos de LED
//  =====================================================================
#define LED_VERMELHO_PIN 15
#define LED_VERDE_PIN     4

//  =====================================================================
//  7 - Variáveis do Gateway
//  =====================================================================
#define Tamanho_pacote 20

byte  PacoteDL[Tamanho_pacote];
byte  PacoteUL[Tamanho_pacote];
int   ID_gateway;

int   RSSI_dBm_UL;
int   RSSI_UL;
float SNR_UL;
int   SNR_UL_inteiro;

//  =====================================================================
//  8 - Objetos Wi-Fi e MQTT
//  =====================================================================
WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

//  Buffer e flag para o pacote DL recebido via MQTT
volatile bool mqtt_dl_disponivel = false;      // Flag de sinalização de Pacote DL disponível no Broker MQTT
byte          mqtt_dl_payload[Tamanho_pacote]; // Define o tamanho do Payload para os pacotes de DL


//  =====================================================================
//  11 - Setup - Executa durante a inicialização da Aplicação no ESP32
//  =====================================================================
void setup() {
  Serial.begin(115200);
  // Aguarda para estabilização da Serial
  delay(20);

  // Declaração dos pinos de LED
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  pinMode(LED_VERDE_PIN,    OUTPUT);
  
  // Inicia os Leds Apagados
  digitalWrite(LED_VERMELHO_PIN, LOW);
  digitalWrite(LED_VERDE_PIN,    LOW);

  // Inicia Wi-Fi
  // Cadastre quantas redes Wi-Fi necessárias (para Fallback) (SSID, Senha)
  wifiMulti.addAP("SSID_1", "Senha_2");
  wifiMulti.addAP("SSID_2", "Senha_2");
  wifiMulti.addAP("SSID_3", "Senha_3");
  wifiMulti.addAP("SSID_4", "Senha_4");

  // O wifiMulti.run() tenta conectar a uma das redes cadastradas
  // Ele retorna WL_CONNECTED quando consegue se conectar com sucesso
  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi conectado com sucesso!");
  Serial.print("Conectado na rede: ");
  Serial.println(WiFi.SSID());
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());

  // Inicia Conexão com Broker MQTT
  CLIENT_ID = "esp32_gateway+lora_" + String(WiFi.macAddress());
  CLIENT_ID.replace(":", "");

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqtt_callback);
  mqttClient.setBufferSize(256);   // garante buffer para 20 bytes + overhead
  conectar_mqtt();

  // Inicia módulo LoRa RFM95
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("[LoRa] Erro ao iniciar módulo!");
    while (true) { delay(1000); }
  }

  // Configura parâmetros de rádio LoRa
  LoRa.setTxPower(txPower);
  LoRa.setSpreadingFactor(spreadingFactor);
  LoRa.setSignalBandwidth(signalBandwidth);
  LoRa.setCodingRate4(codingRateDenominator);

  // Indica inicialização do Gateway LoRa MQTT
  Serial.println("[LoRa] Gateway MQTT inicializado com sucesso!");
  Serial.println("[INFO] Aguardando pacotes DL via MQTT...");

  // Pisca verde 1x → tudo OK
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERDE_PIN, LOW);
}

//  =====================================================================
//  12 - Loop principal
//  =====================================================================
void loop() {

  // Mantém conexões ativas
  // No loop, você pode monitorar a conexão.
  // Se a rede cair, o wifiMulti.run() tenta se reconectar automaticamente à melhor rede disponível.
  if (wifiMulti.run() != WL_CONNECTED) {
    Serial.println("Conexão perdida! Tentando reconectar...");
    delay(1000);
  }

  // Reconexão ao Broker MQTT caso conexão perdida
  if (!mqttClient.connected()) {
    conectar_mqtt();
  }
  mqttClient.loop();   // processa mensagens MQTT pendentes

  // Verifica se chegou pacote DL via MQTT e o envia pelo rádio LoRa
  Phy_mqtt_receive_DL();

  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker
  Phy_radio_receive_UL();
}
