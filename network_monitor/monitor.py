import psutil
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

class NetworkMonitor:
    def __init__(self):
        self.start_io = psutil.net_io_counters()
        
    def check_traffic(self):
        """
        Prints the amount of network traffic sent/received since the monitor started.
        This is a proof-of-concept for the sovereignty claim.
        """
        current_io = psutil.net_io_counters()
        
        bytes_sent = current_io.bytes_sent - self.start_io.bytes_sent
        bytes_recv = current_io.bytes_recv - self.start_io.bytes_recv
        
        # Since we use localhost for Ollama, there will be loopback traffic.
        # A true test requires isolating physical network interfaces or tracking loopback separately.
        # This basic monitor tracks total traffic as a proxy.
        
        logging.info(f"Network Monitor: Sent: {bytes_sent / 1024:.2f} KB | Received: {bytes_recv / 1024:.2f} KB")
        return bytes_sent, bytes_recv

if __name__ == "__main__":
    logging.info("Starting Vajra Network Monitor (Sovereignty Proof)...")
    monitor = NetworkMonitor()
    try:
        while True:
            monitor.check_traffic()
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Network Monitor stopped.")
