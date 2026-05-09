from modelos.modelo2 import run
from gpio_controller import cleanup

try:

    run()

except KeyboardInterrupt:

    print("\nEncerrando sistema...")

finally:

    cleanup()