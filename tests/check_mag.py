import smbus
import time

I2C_BUS = 1
MAG_ADDRESS = 0x1e

try:
    bus = smbus.SMBus(I2C_BUS)
    # Initialize magnetometer
    bus.write_byte_data(MAG_ADDRESS, 0x20, 0x90)  # CTRL1_M: 10Hz, ultra-high performance mode
    bus.write_byte_data(MAG_ADDRESS, 0x21, 0x00)  # CTRL2_M: Default
    bus.write_byte_data(MAG_ADDRESS, 0x22, 0x00)  # CTRL3_M: Continuous mode
    time.sleep(0.2)  # Increased delay for sensor to stabilize

    # Read magnetometer data
    data = bus.read_i2c_block_data(MAG_ADDRESS, 0x28, 6)
    x = (data[0] << 8) | data[1]
    y = (data[2] << 8) | data[3]
    z = (data[4] << 8) | data[5]
    if x > 32767: x -= 65536  # Convert to signed 16-bit
    if y > 32767: y -= 65536
    if z > 32767: z -= 65536
    print(f"Magnetic Field - X: {x} uT, Y: {y} uT, Z: {z} uT")

except Exception as e:
    print(f"Error: {e}")

bus.close()
