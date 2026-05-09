from threading import Thread, Event

from modelos.modelo1 import run as run_model1
from modelos.modelo2 import run as run_model2

from gpio_controller import cleanup

# evento global de parada
stop_event = Event()

try:

    # threads
    t1 = Thread(target=run_model1, args=(stop_event,))
    t2 = Thread(target=run_model2, args=(stop_event,))

    t1.start()
    t2.start()

    # espera threads
    t1.join()
    t2.join()

except KeyboardInterrupt:

    print("\nEncerrando sistema...")

    # avisa threads para parar
    stop_event.set()

    # espera terminar
    t1.join()
    t2.join()

finally:

    cleanup()