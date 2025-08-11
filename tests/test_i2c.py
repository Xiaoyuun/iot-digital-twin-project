import smbus
import time

bus = smbus.SMBus(1)

# Addresses to test
addresses = [0x1d, 0x1e]
device_found = False

# Delay to allow sensor stabilization
time.sleep(0.1)

for addr in addresses:
    try:
        # Attempt a simple read
        bus.read_byte(addr)
        print(f"Device found and responsive at 0x{addr:02x}")
        device_found = True
    except:
        print(f"No response at 0x{addr:02x}")

if not device_found:
    print("No devices responded at expected addresses.")

# Initialize and read WHO_AM_I (0x0F) for accelerometer
try:
    # Wake up sensor (CTRL1_XL register 0x10, set to 0x60 for 1.66kHz)
    bus.write_byte_data(0x1d, 0x10, 0x60)
    time.sleep(0.1)  # Wait for sensor to stabilize
    who_am_i = bus.read_byte_data(0x1d, 0x0f)
    print(f"Accelerometer WHO_AM_I: 0x{who_am_i:02x} (expected 0x44)")
except Exception as e:
    print(f"Failed to read accelerometer WHO_AM_I: {e}")

bus.close()
