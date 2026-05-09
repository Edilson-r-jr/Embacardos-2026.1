import time

def log(message):

    current_time = time.strftime("%H:%M:%S")

    print(f"[{current_time}] {message}")