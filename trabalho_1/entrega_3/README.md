# Sistema de Controle Distribuído de Cruzamentos de Trânsito

## Visão Geral

Sistema distribuído de controle e monitoramento de cruzamentos de sinais de trânsito com integração MODBUS RS485 para câmeras LPR e detecção de emergências.

### Componentes

- **Servidor Central**: Monitora cruzamentos, registra multas por infrações de velocidade, gerencia emergências e modo noturno
- **Servidores Distribuídos (2x)**: Controlam semáforos, detectam infrações de velocidade, respeitam modo noturno e de emergência

## Instalação

### Dependências

```bash
pip install -r requirements.txt
```

### Configuração

Editar `config/intersection1.json` e `config/intersection2.json` conforme necessário:

```json
{
  "central_host": "127.0.0.1",
  "central_port": 5000,
  "intersection_id": 1
}
```

## Uso

Abrir 3 terminais:

### Terminal 1 - Servidor Central

```bash
cd entrega_3
python -m central.main
```

O servidor central irá:
- Escutar na porta 5000 por conexões dos cruzamentos
- Fazer polling periódico do estado de emergência via MODBUS
- Registrar multas quando infrações de velocidade forem detectadas
- Exibir dashboard de monitoramento com status dos cruzamentos

### Terminal 2 - Servidor Distribuído 1

```bash
cd entrega_3
python -m distributed.main config/intersection1.json
```

### Terminal 3 - Servidor Distribuído 2

```bash
cd entrega_3
python -m distributed.main config/intersection2.json
```

## Funcionalidades Implementadas

### Servidor Central

- ✅ Conexão TCP/IP com múltiplos cruzamentos
- ✅ Leitura periódica de estado de emergência (MODBUS 0x20)
- ✅ Acionamento de câmeras LPR via MODBUS (0x11-0x14)
- ✅ Registro persistente de multas (arquivo `multas.json`)
- ✅ Comando de modo noturno (amarelo intermitente)
- ✅ Comando de modo de emergência (abrir via)
- ✅ Dashboard de monitoramento em tempo real
- ✅ Cálculo de fluxo de tráfego por sensor
- ✅ Histórico de infrações por cruzamento

### Servidores Distribuídos

- ✅ Máquina de estados para controle de semáforos
- ✅ Modo noturno (alternância entre amarelo e vermelho a cada 1s)
- ✅ Modo de emergência (abre via indicada)
- ✅ Simulação de sensores de velocidade
- ✅ Detecção e reporte de infrações de velocidade (> 60 km/h)
- ✅ Contagem de veículos por sensor
- ✅ Heartbeat periódico
- ✅ Reconexão automática ao servidor central

## Protocolo de Comunicação

### TCP/IP (Central ↔ Distribuído)

Mensagens em JSON terminadas por `\n`:

```json
{"type": "heartbeat", "intersection_id": 1, "timestamp": "..."}
{"type": "vehicle_count", "intersection_id": 1, "sensor_id": 1, "count": 42, "timestamp": "..."}
{"type": "speed_violation", "intersection_id": 1, "sensor_id": 1, "speed": 75.5, "timestamp": "..."}
```

### Comandos do Central para Distribuído

```json
{"type": "night_mode", "enabled": true}
{"type": "emergency", "active": true, "road": 1, "signal_group": 1}
```

### MODBUS RS485

- **Emergências**: Dispositivo 0x20, Função 0x03 (leitura), 11 registradores
- **Câmeras LPR**: Dispositivos 0x11-0x14, Funções 0x03 (leitura) e 0x10 (escrita)

## Arquitetura de Arquivos

```
entrega_3/
├── central/
│   ├── main.py                    # Ponto de entrada
│   ├── constants.py               # Constantes do sistema
│   ├── violations_logger.py       # Logging de multas
│   ├── network/
│   │   └── tcp_server.py         # Servidor TCP
│   ├── state/
│   │   ├── state_manager.py      # Gerenciador de estado
│   │   └── intersection_state.py # Estado por cruzamento
│   └── modbus/
│       ├── crc16.py              # CRC16
│       ├── uart_interface.py     # Interface UART
│       ├── emergency_reader.py   # Leitor de emergências
│       └── lpr_camera.py         # Controle de câmeras LPR
├── distributed/
│   ├── main.py                    # Ponto de entrada
│   ├── network/
│   │   └── tcp_client.py         # Cliente TCP
│   └── traffic/
│       ├── traffic_state_machine.py
│       ├── traffic_controller.py
│       └── traffic_states.py
├── common/
│   ├── __init__.py
│   └── messages.py               # Definição de mensagens
├── config/
│   ├── intersection1.json        # Config cruzamento 1
│   └── intersection2.json        # Config cruzamento 2
├── requirements.txt
└── README.md
```

## Logging de Multas

As multas são registradas em `multas.json` com os seguintes campos:

```json
{
  "timestamp": "2026-06-06T...",
  "intersection_id": 1,
  "sensor_id": 1,
  "speed_kmh": 75.5,
  "camera_modbus": "0x11",
  "plate": "ABC1234",
  "confidence": 95,
  "fine_value": 293.47
}
```

## Modos de Operação

### Normal

A máquina de estados segue a sequência padrão:
- Via Principal Verde (15s)
- Via Principal Amarelo (3s)
- Vermelho Total (2s)
- Via Cruzamento Verde (5s)
- Via Cruzamento Amarelo (3s)
- Vermelho Total (2s)

### Modo Noturno

Quando ativado via MODBUS, todos os semáforos alternam entre:
- Amarelo (código 0) - 1s
- Vermelho/Apagado (código 4) - 1s

### Modo de Emergência

Quando detectado via MODBUS:
- Identifica qual via/cruzamento está afetado
- Abre verde para a via de emergência (signal_group)
- Fecha vermelho para as outras vias
- Mantém até o término da emergência

## Diagnóstico

### Central não conecta aos distribuídos?

1. Verificar se os distribuídos estão rodando
2. Verificar firewall na porta 5000
3. Verificar configuração de host/porta nos arquivos `config/intersection*.json`

### Multas não estão sendo registradas?

1. Verificar se a câmera LPR está corretamente conectada à porta UART
2. Verificar porta serial em `central/constants.py` (padrão: `/dev/serial0`)
3. Verificar permissões de acesso à porta serial

### Modo noturno não funciona?

1. Verificar conexão MODBUS à ESP32
2. Verificar se o registrador `night_mode` está sendo enviado corretamente
3. Verificar logs do servidor central

## Tecnologias

- **Linguagem**: Python 3.7+
- **Protocolo**: TCP/IP (para comunicação distribuída), MODBUS RTU over RS485
- **Serialização**: JSON
- **Threading**: Multithreading nativo do Python
- **Serial**: pyserial

## Observações de Implementação

- O sistema está preparado para simular sensores de velocidade na falta de hardware GPIO real
- Reconexão automática está implementada para resiliência
- O servidor central detecta desconexões de cruzamentos por timeout de heartbeat
- Log persistente garante histórico de multas mesmo após reinicialização
