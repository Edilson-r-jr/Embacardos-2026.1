# Execução do Projeto

## Pré-requisitos

* Python 3 instalado
* Biblioteca `RPi.GPIO`
* Raspberry Pi configurada

---

# Instalação

## Instalar pip

```bash
sudo apt install python3-pip
```

---

## Instalar dependências

Na raiz do projeto:

```bash
pip install -r requirements.txt
```

---

# requirements.txt

```text
RPi.GPIO
```

---

# Estrutura do Projeto

```text
entrega_1/
│
├── README.md
├── requirements.txt
│
└── src/
    ├── constants.py
    ├── gpio_controller.py
    ├── main.py
    │
    ├── modelos/
    │   ├── modelo1.py
    │   └── modelo2.py
    │
    └── utils/
        └── logger.py
```

---

# Execução

Entre na pasta `src`:

```bash
cd src
```

Execute o programa:

```bash
python3 main.py
```

Em alguns sistemas pode ser necessário executar como superusuário:

```bash
sudo python3 main.py
```

---

# Encerramento

Para encerrar o sistema:

```text
CTRL + C
```

O programa realiza limpeza automática dos GPIOs utilizando `GPIO.cleanup()`.
