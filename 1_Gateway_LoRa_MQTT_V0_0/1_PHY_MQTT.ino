/*
// =====================================================================
//  1_PHY.ino  –  Camada Física do Gateway LoRa MQTT
//  Versão MQTT: comunicação via broker.hivemq.com:1883
//  - DL: assina "mot_lora_SEU_NOME/gateway/downlink"  ← recebe do Python
//  - UL: publica em "mot_lora_SEU_NOME/gateway/uplink" → envia ao Python
//  As funções de rádio LoRa (Phy_radio_send_DL / Phy_radio_receive_UL)
//  permanecem idênticas à versão Framework Basic.
//
//  Última Modificação: Branquinho / Felipe / Luís Felipe / Anderson - 21/06/2026
//
// =====================================================================
*/

// ========================= PACOTE DOWN LINK ==========================
// Recebe pacote DL do broker MQTT (publicado pelo Python)
void Phy_mqtt_receive_DL() {

  // Verifica se há novas mensagens no broker MQTT
  // Flag setada na função Callback MQTT
  if (mqtt_dl_disponivel) {          
    mqtt_dl_disponivel = false;

    // Copia payload recebido para PacoteDL
    for (int i = 0; i < Tamanho_pacote; i++) {
      PacoteDL[i] = mqtt_dl_payload[i];
    }
    ID_gateway = PacoteDL[10];       // Identifica o gateway

    Serial.println("[PHY] Pacote DL recebido via MQTT.");

    // Chama camada física para transmitir pelo rádio RFM95
    Phy_radio_send_DL();
  }
}

// ==================== ENVIA PACOTE DL PELO RÁDIO RFM95 ==============
// (sem alterações em relação a versão USB)
void Phy_radio_send_DL() {

  // Pisca LED Vermelho - Indica Transmissão para o Nó Sensor
  digitalWrite(LED_VERMELHO_PIN, HIGH);

  LoRa.beginPacket();
  for (int i = 0; i < Tamanho_pacote; i++) {
    LoRa.write(PacoteDL[i]);
  }
  LoRa.endPacket();

  delay(50);
  digitalWrite(LED_VERMELHO_PIN, LOW);

}

// ==================== RECEBE PACOTE UL DO RÁ DIO RFM95 ==============
// (sem alterações em relação à versão serial)
void Phy_radio_receive_UL() {

  uint8_t packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    if (packetSize >= Tamanho_pacote) {

      // Pisca LED Verde - Indica Recepção do Gateway
      digitalWrite(LED_VERDE_PIN, HIGH);

      for (int i = 0; i < Tamanho_pacote; i++) {
        PacoteUL[i] = LoRa.read();
      }

      RSSI_dBm_UL = LoRa.packetRssi();
      SNR_UL      = LoRa.packetSnr();

      delay(50);
      digitalWrite(LED_VERDE_PIN, LOW);

      // Chama função de envio do Pacote UL via MQTT
      Phy_mqtt_send_UL();
    }
  }
}

//  ==================== PUBLICA PACOTE UL NO BROKER MQTT ==============
//  Substitui Phy_serial_send_UL(): envia o pacote UL via MQTT
void Phy_mqtt_send_UL() {

  // Mapeia RSSI_UL para 1 byte (mesma lógica da versão serial)
  if (RSSI_dBm_UL > -10.5) {
    RSSI_UL = 127;
  } else if (RSSI_dBm_UL <= -10.5 && RSSI_dBm_UL >= -74) {
    RSSI_UL = (int)((RSSI_dBm_UL + 74) * 2);
  } else {
    RSSI_UL = (int)(((RSSI_dBm_UL + 74) * 2) + 256);
  }

  // Armazena informações de gerência no pacote UL
  PacoteUL[2] = RSSI_UL;

  SNR_UL = ((SNR_UL + 30) * 4); // Offset de 30 para o valor da SNR que tem uma casa decimal e ao multiplicar por 4 fica inteiro
  SNR_UL_inteiro = int(SNR_UL);
  PacoteUL[3] = byte(SNR_UL_inteiro);

  // Publica no tópico UL o PacoteUL
  if (mqttClient.connected()) {
    mqttClient.publish(TOPIC_UL, PacoteUL, Tamanho_pacote);
    Serial.println("[PHY] Pacote UL publicado via MQTT.");
  } else {
    Serial.println("[PHY] MQTT desconectado – pacote UL descartado.");
  }

}


//  =====================================================================
//  Funções auxiliares de conexão
//  =====================================================================

//  =====================================================================
//  Callback MQTT (recepção de novas mensagens)
//  =====================================================================
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  if (strcmp(topic, TOPIC_DL) == 0) {
    if (length >= Tamanho_pacote) {
      for (int i = 0; i < Tamanho_pacote; i++) {
        mqtt_dl_payload[i] = payload[i];
      }
      mqtt_dl_disponivel = true;   // sinaliza para o loop principal
    }
  }
}

//  =====================================================================
//  Conexão com Broker MQTT
//  =====================================================================
void conectar_mqtt() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Conectando ao broker...");
    if (mqttClient.connect(CLIENT_ID.c_str())) {
      Serial.println(" conectado!");
      mqttClient.subscribe(TOPIC_DL);
      Serial.print("[MQTT] Inscrito em: ");
      Serial.println(TOPIC_DL);
    } else {
      Serial.print(" falhou (rc=");
      Serial.print(mqttClient.state());
      Serial.println("). Tentando em 3s...");
      delay(3000);
    }
  }
}
