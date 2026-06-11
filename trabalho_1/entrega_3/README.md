# Sistema de Controle Distribuído de Cruzamentos de Trânsito

## Visão Geral

Sistema distribuído de controle e monitoramento de cruzamentos de sinais de trânsito com integração MODBUS RS485 para câmeras LPR e detecção de emergências.

### Componentes

- **Servidor Central**: Monitora cruzamentos, registra multas por infrações de velocidade, gerencia emergências e modo noturno
- **Servidores Distribuídos (2x)**: Controlam semáforos via GPIO, leem sensores de velocidade, respondem a botões de pedestre e respeitam modo noturno, emergência e controle manual

## Instalação

### Dependências

```bash
pip install -r requirements.txt
```

> `RPi.GPIO` é necessário apenas em Raspberry Pi. O sistema detecta automaticamente o hardware e entra em modo mock caso não esteja em uma RPi.

### Configuração

Editar `config/intersection1.json` e `config/intersection2.json` conforme necessário:

```json
{
  "intersection_id": 1,
  "central_host": "127.0.0.1",
  "central_port": 5000
}
```

## Uso

### Launcher (recomendado)

```bash
cd entrega_3
python launcher.py
```

O launcher abre uma interface de terminal interativa que gerencia todos os processos em um único painel.

#### Controles do Launcher

**Navegação entre abas**

| Tecla | Ação |
|-------|------|
| `C` | Ver log da Central |
| `V` | Ver log do Distribuído 1 |
| `B` | Ver log do Distribuído 2 |
| `N` | Ver multas registradas (`multas.json`) |
| Roda do mouse | Scroll no log da aba ativa |

**Controle de processos**

| Tecla | Ação |
|-------|------|
| `1` | Iniciar Central |
| `2` | Iniciar Distribuído 1 |
| `3` | Iniciar Distribuído 2 |
| `A` | Iniciar todos os processos |
| `Q` | Parar Central |
| `W` | Parar Distribuído 1 |
| `E` | Parar Distribuído 2 |
| `S` | Parar todos os processos |
| `0` | Encerrar todos os processos e sair |

**Controle manual de semáforos** (acessado via `F`)

| Tecla | Ação |
|-------|------|
| `F` | Entrar no modo de controle manual |
| `1` | CRZ-1: via principal verde |
| `2` | CRZ-1: via cruzamento verde |
| `3` | CRZ-1: vermelho total |
| `4` | CRZ-1: retornar ao ciclo normal |
| `5` | CRZ-2: via principal verde |
| `6` | CRZ-2: via cruzamento verde |
| `7` | CRZ-2: vermelho total |
| `8` | CRZ-2: retornar ao ciclo normal |
| `Y` | Alternar amarelo intermitente (modo noturno) |
| `Esc` | Cancelar controle manual |

### Execução manual (alternativa)

Abrir 3 terminais separados:

```bash
# Terminal 1 — Servidor Central
cd entrega_3
python -m central.main

# Terminal 2 — Distribuído 1
cd entrega_3
python -m distributed.main config/intersection1.json

# Terminal 3 — Distribuído 2
cd entrega_3
python -m distributed.main config/intersection2.json
```

Para forçar modo mock (sem GPIO real):

```bash
python -m distributed.main config/intersection1.json --mock
```

## Funcionalidades Implementadas

### Servidor Central

- ✅ Conexão TCP/IP com múltiplos cruzamentos
- ✅ Leitura periódica de estado de emergência (MODBUS 0x20)
- ✅ Acionamento de câmeras LPR via MODBUS (0x11–0x14)
- ✅ Registro persistente de multas (`multas.json`)
- ✅ Controle de modo noturno (via MODBUS ou launcher)
- ✅ Comando de modo de emergência (abrir via)
- ✅ Controle manual de estados por cruzamento (via launcher)
- ✅ Dashboard de monitoramento no log (atualiza a cada 5s)
- ✅ Cálculo de fluxo de tráfego por sensor
- ✅ Reenvio de estado salvo para cruzamentos que reconectam

### Servidores Distribuídos

- ✅ Máquina de estados para controle de semáforos
- ✅ Controle GPIO de semáforos (com fallback automático para mock)
- ✅ Auto-detecção de Raspberry Pi (modo mock em outros ambientes)
- ✅ Leitura de sensores de velocidade via GPIO
- ✅ Botões de pedestre (via principal e via cruzamento)
- ✅ Modo noturno (amarelo/vermelho a cada 1s)
- ✅ Modo de emergência (abre via indicada)
- ✅ Controle manual de estado via launcher
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

### Comandos da Central para os Distribuídos

```json
{"type": "night_mode", "enabled": true}
{"type": "emergency", "active": true, "road": 1, "signal_group": 1}
{"type": "manual_override", "state_code": 1}
{"type": "manual_override", "state_code": null}
```

> `state_code: null` cancela o controle manual e retoma o ciclo normal.

### MODBUS RS485

- **Emergências**: Dispositivo `0x20`, Função `0x03` (leitura), 11 registradores
- **Câmeras LPR**: Dispositivos `0x11`–`0x14`, Funções `0x03` (leitura) e `0x10` (escrita)

## Arquitetura de Arquivos

```
entrega_3/
├── central/
│   ├── main.py                    # Ponto de entrada
│   ├── constants.py               # Constantes do sistema
│   ├── violations_logger.py       # Logging de multas
│   ├── network/
│   │   └── tcp_server.py          # Servidor TCP
│   ├── state/
│   │   ├── state_manager.py       # Gerenciador de estado
│   │   └── intersection_state.py  # Estado por cruzamento
│   └── modbus/
│       ├── bus_manager.py         # Gerenciador do barramento MODBUS
│       ├── crc16.py               # CRC16
│       ├── uart_interface.py      # Interface UART
│       ├── emergency_reader.py    # Leitor de emergências
│       └── lpr_camera.py          # Controle de câmeras LPR
├── distributed/
│   ├── main.py                    # Ponto de entrada
│   ├── constants.py               # Constantes do distribuído
│   ├── network/
│   │   └── tcp_client.py          # Cliente TCP
│   ├── traffic/
│   │   ├── traffic_state_machine.py
│   │   ├── traffic_controller.py
│   │   └── traffic_states.py
│   └── gpio/
│       ├── gpio_interface.py      # Abstração GPIO (real/mock)
│       ├── traffic_light_controller.py  # Controle dos semáforos
│       └── sensor_reader.py       # Sensores de velocidade e botões
├── common/
│   ├── __init__.py
│   └── messages.py                # Definição de mensagens
├── config/
│   ├── intersection1.json         # Config cruzamento 1
│   └── intersection2.json         # Config cruzamento 2
├── launcher.py
├── requirements.txt
└── README.md
```

## Logging de Multas

As multas são registradas em `multas.json` com os seguintes campos:

```json
{
  "timestamp": "2026-06-06T12:00:00.000000",
  "intersection_id": 1,
  "sensor_id": 1,
  "speed_kmh": 75.5,
  "camera_modbus": "0x11",
  "plate": "ABC1234",
  "confidence": 0.95,
  "fine_value": 293.47
}
```

## Modos de Operação

### Normal

A máquina de estados segue a sequência padrão. As fases verdes têm duração variável: encerram no tempo máximo ou antecipadamente se um botão de pedestre for pressionado após o tempo mínimo.

| Fase | Mín | Máx |
|------|-----|-----|
| Via Principal Verde | 15s | 30s |
| Via Principal Amarelo | 3s | 3s |
| Vermelho Total | 2s | 2s |
| Via Cruzamento Verde | 5s | 10s |
| Via Cruzamento Amarelo | 3s | 3s |
| Vermelho Total | 2s | 2s |

### Modo Noturno

Quando ativado (via MODBUS ou tecla `Y` no launcher), todos os semáforos alternam entre:

- Amarelo — 1s
- Vermelho/Apagado — 1s

### Modo de Emergência

Quando detectado via MODBUS:

- Identifica qual via/cruzamento está afetado
- Abre verde para a via de emergência (`signal_group`)
- Fecha vermelho para as outras vias
- Mantém até o término da emergência

### Controle Manual

Acessado pela tecla `F` no launcher. Permite forçar um estado fixo em qualquer cruzamento, independente do ciclo ou dos modos noturno/emergência. Tecla `4`/`8` retoma o ciclo normal.

## Diagnóstico

### Central não conecta aos distribuídos?

1. Verificar se os distribuídos estão rodando
2. Verificar firewall na porta 5000
3. Verificar `central_host` e `central_port` nos arquivos `config/intersection*.json`

### GPIO não inicializa no distribuído?

O sistema entra em modo mock automaticamente se não detectar uma Raspberry Pi. Para forçar mock explicitamente: `python -m distributed.main config/intersection1.json --mock`

### Multas não estão sendo registradas?

1. Verificar se a câmera LPR está corretamente conectada à porta UART
2. Verificar porta serial em `central/constants.py` (padrão: `/dev/serial0`)
3. Verificar permissões de acesso à porta serial (`sudo usermod -a -G dialout $USER`)

### Modo noturno não funciona?

1. Verificar conexão MODBUS à ESP32
2. Verificar se o registrador `night_mode` está sendo enviado corretamente
3. Verificar logs do servidor central
4. Alternativa: ativar manualmente via tecla `Y` no modo de controle do launcher

## Tecnologias

- **Linguagem**: Python 3.7+
- **Protocolo**: TCP/IP (comunicação distribuída), MODBUS RTU over RS485
- **Serialização**: JSON
- **Threading**: Multithreading nativo do Python
- **Serial**: pyserial
- **GPIO**: RPi.GPIO (apenas em Raspberry Pi; mock automático nos demais)
- **Interface do launcher**: rich
