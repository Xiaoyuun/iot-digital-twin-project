import smbus
import time

I2C_BUS = 1
ACC_ADDRESS = 0x1d  # Accelerometer address with SDO low (adjust to 0x1f if SDO high)

try:
    bus = smbus.SMBus(I2C_BUS)

    # Initialize accelerometer (10Hz, 2g range)
    bus.write_byte_data(ACC_ADDRESS, 0x10, 0x60)  # CTRL1_XL: 10Hz, 2g
    bus.write_byte_data(ACC_ADDRESS, 0x11, 0x00)  # CTRL2_XL
    bus.write_byte_data(ACC_ADDRESS, 0x12, 0x04)  # CTRL3_XL: Continuous update
    time.sleep(0.2)

    while True:
        try:
            # Read raw 6 bytes from accelerometer
            raw_data = bus.read_i2c_block_data(ACC_ADDRESS, 0x28, 6)
            # Convert to hex and print as a single line
            hex_data = " ".join(f"0x{byte:02x}" for byte in raw_data)
            print(hex_data)
            time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

except Exception as e:
    print(f"Setup error: {e}")

bus.close()
