import subprocess
import sys

LOG_FILES = {
    "central": "logs/central.log",
    "dist1": "logs/dist1.log",
    "dist2": "logs/dist2.log",
}

processes = {}
log_handles = {}


def start_central():
    if "central" in processes:
        print("[LAUNCHER] Central já está rodando.")
        return

    print("[LAUNCHER] Iniciando CENTRAL em background...")

    log_handles["central"] = open(LOG_FILES["central"], "w")

    processes["central"] = subprocess.Popen(
        [sys.executable, "-u", "-m", "central.main"],
        stdout=log_handles["central"],
        stderr=subprocess.STDOUT
    )


def start_dist1():
    if "dist1" in processes:
        print("[LAUNCHER] Distribuído 1 já está rodando.")
        return
    
    print("[LAUNCHER] Iniciando DISTRIBUÍDO 1 em background...")

    log_handles["dist1"] = open(LOG_FILES["dist1"], "w")

    processes["dist1"] = subprocess.Popen(
        [sys.executable, "-u", "-m", "distributed.main", "config/intersection1.json"],
        stdout=log_handles["dist1"],
        stderr=subprocess.STDOUT
    )


def start_dist2():
    if "dist2" in processes:
        print("[LAUNCHER] Distribuído 2 já está rodando.")
        return

    print("[LAUNCHER] Iniciando DISTRIBUÍDO 2 em background...")

    log_handles["dist2"] = open(LOG_FILES["dist2"], "w")

    processes["dist2"] = subprocess.Popen(
        [sys.executable, "-u", "-m", "distributed.main", "config/intersection2.json"],
        stdout=log_handles["dist2"],
        stderr=subprocess.STDOUT
    )


def stop_central():
    if "central" in processes:
        print("[LAUNCHER] Parando CENTRAL...")

        processes["central"].terminate()
        processes.pop("central")

        log_handles["central"].close()
        log_handles.pop("central")

    else:
        print("[LAUNCHER] Central não está rodando.")


def stop_dist1():
    if "dist1" in processes:
        print("[LAUNCHER] Parando DISTRIBUÍDO 1...")

        processes["dist1"].terminate()
        processes.pop("dist1")

        log_handles["dist1"].close()
        log_handles.pop("dist1")

    else:
        print("[LAUNCHER] Distribuído 1 não está rodando.")


def stop_dist2():
    if "dist2" in processes:
        print("[LAUNCHER] Parando DISTRIBUÍDO 2...")
        processes["dist2"].terminate()
        processes.pop("dist2")
        
        log_handles["dist2"].close()
        log_handles.pop("dist2")
    else:
        print("[LAUNCHER] Distribuído 2 não está rodando.")


def stop_all():
    print("[LAUNCHER] Encerrando processos...")

    for name, proc in processes.items():
        print(f" - Parando {name}")
        proc.terminate()

    processes.clear()

def show_logs(name):
    try:
        with open(LOG_FILES[name], "r") as f:
            lines = f.readlines()[-30:]  # últimas 30 linhas

        print("\n" + "=" * 50)
        print(f"LOGS - {name}")
        print("=" * 50)

        for line in lines:
            print(line.strip())

    except FileNotFoundError:
        print("[LAUNCHER] Nenhum log encontrado ainda.")


def menu():
    while True:
        print("\n" + "=" * 45)
        print("        SISTEMA DE TRÁFEGO - LAUNCHER")
        print("=" * 45)
        print("1 - Iniciar Central")
        print("2 - Iniciar Distribuído 1")
        print("3 - Iniciar Distribuído 2")
        print("4 - Iniciar tudo")
        print("5 - Ver processos ativos")
        print("6 - Encerrar Central")
        print("7 - Encerrar Distribuído 1")
        print("8 - Encerrar Distribuído 2")
        print("9 - Ver logs Central")
        print("10 - Ver logs Distribuído 1")
        print("11 - Ver logs Distribuído 2")
        print("12 - Encerrar tudo")
        print("0 - Sair")
        print("=" * 45)

        choice = input("Escolha: ")

        if choice == "1":
            start_central()

        elif choice == "2":
            start_dist1()

        elif choice == "3":
            start_dist2()

        elif choice == "4":
            start_central()
            start_dist1()
            start_dist2()

        elif choice == "5":
            print("\n[ATIVOS]")
            for k in processes:
                print(f" - {k}")

        elif choice == "6":
            stop_central()

        elif choice == "7":
            stop_dist1()

        elif choice == "8":
            stop_dist2()

        elif choice == "9":
            show_logs("central")

        elif choice == "10":
            show_logs("dist1")

        elif choice == "11":
            show_logs("dist2")

        elif choice == "12":
            stop_all()

        elif choice == "0":
            stop_all()
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        stop_all()
        print("\n[LAUNCHER] Finalizado.")