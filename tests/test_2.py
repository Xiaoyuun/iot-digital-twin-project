import smbus
import time

I2C_BUS = 1
MAG_ADDRESS = 0x1e  # Magnetometer address with SDO low
ACC_ADDRESS = 0x1d  # Accelerometer address with SDO low

try:
    bus = smbus.SMBus(I2C_BUS)

    # Initialize magnetometer (10Hz, continuous mode)
    bus.write_byte_data(MAG_ADDRESS, 0x20, 0x90)  # CTRL1_M: 10Hz, ultra-high performance
    bus.write_byte_data(MAG_ADDRESS, 0x21, 0x00)  # CTRL2_M
    bus.write_byte_data(MAG_ADDRESS, 0x22, 0x00)  # CTRL3_M
    time.sleep(0.2)

    # Initialize accelerometer (10Hz, 2g range)
    bus.write_byte_data(ACC_ADDRESS, 0x10, 0x60)  # CTRL1_XL: 10Hz, 2g
    bus.write_byte_data(ACC_ADDRESS, 0x11, 0x00)  # CTRL2_XL
    bus.write_byte_data(ACC_ADDRESS, 0x12, 0x04)  # CTRL3_XL: Continuous update
    time.sleep(0.2)

    while True:
        try:
            # Read magnetometer raw data
            mag_data = bus.read_i2c_block_data(MAG_ADDRESS, 0x28, 6)
            mag_x = (mag_data[1] << 8) | mag_data[0]  # Low byte first
            mag_y = (mag_data[3] << 8) | mag_data[2]
            mag_z = (mag_data[5] << 8) | mag_data[4]
            if mag_x > 32767: mag_x -= 65536
            if mag_y > 32767: mag_y -= 65536
            if mag_z > 32767: mag_z -= 65536

            # Read accelerometer raw data
            acc_data = bus.read_i2c_block_data(ACC_ADDRESS, 0x28, 6)
            acc_x = (acc_data[1] << 8) | acc_data[0]
            acc_y = (acc_data[3] << 8) | acc_data[2]
            acc_z = (acc_data[5] << 8) | acc_data[4]
            if acc_x > 32767: acc_x -= 65536
            if acc_y > 32767: acc_y -= 65536
            if acc_z > 32767: acc_z -= 65536

            # Print raw data
            print(f"Mag Raw - X: {mag_x}, Y: {mag_y}, Z: {mag_z}")
            print(f"Acc Raw - X: {acc_x}, Y: {acc_y}, Z: {acc_z}")
            time.sleep(1)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

except Exception as e:
    print(f"Setup error: {e}")

bus.close()
