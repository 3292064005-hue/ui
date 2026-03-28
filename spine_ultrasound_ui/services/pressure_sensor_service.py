import threading
import time
from loguru import logger

class ExternalPressureSensorService:
    """
    Abstract interface for the external 1D/6D Force Sensor mounted between
    the ER3 Flange and the Ultrasound Probe.
    Since the hardware protocol is TBD (Modbus/EtherCAT/UDP/USB),
    this service exposes a mock 1kHz threaded polling loop to feed
    the shared memory pool (and ultimately the C++ Admittance Controller).
    """
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self._thread = None
        self.latest_z_force_N = 0.0
        
        # self.serial_conn = Serial(self.port, self.baudrate) # TBD when hardware confirmed

    def start_polling(self):
        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(f"[Pressure Sensor] Began polling 1kHz force data on {self.port}")

    def _poll_loop(self):
        """ Extremely tight loop strictly for RS485/USB data flushing """
        while self.running:
            # TBD Hardware Block
            # data_bytes = self.serial_conn.read(8) 
            # self.latest_z_force_N = unpack(">d", data_bytes)
            
            # Mocking realistic breathing/sensor noise
            self.latest_z_force_N = 9.8 + (time.time() % 0.4) 
            
            # memory_pool.push_pressure_data(self.latest_z_force_N)

            # Sleep slightly less than 1ms to prevent starvation, or let the serial buffer block naturally.
            time.sleep(0.0005)

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("[Pressure Sensor] Polling halted.")
