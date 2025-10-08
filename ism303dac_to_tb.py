import time
import smbus
import paho.mqtt.client as mqtt
import json
import logging
import sys
from config import TB_GW_HOST, GW_ACCESS_TOKEN

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mag_to_thingsboard.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
I2C_BUS = 1                  # Raspberry Pi I2C bus
MAG_ADDRESS = 0x1E           # Magnetometer I2C address (7-bit)
ACC_ADDRESS = 0X1D           # Accelerometer I2C address (7-bit)
TB_GATEWAY_HOST = TB_GW_HOST  # ThingsBoard server
TB_GATEWAY_PORT = 1883
GATEWAY_ACCESS_TOKEN = GW_ACCESS_TOKEN

# ISM303DAC register addresses (from ism303dac_reg.h)
WHO_AM_I_M = 0x4F
CFG_REG_A_M = 0x60
STATUS_REG_M = 0x67
OUTX_L_REG_M = 0x68
# Accelerometer registers
WHO_AM_I_A = 0x0F
CTRL1_XL = 0x10
STATUS_REG_A = 0x1B
OUTX_L_XL = 0x28

# Initialize I2C bus
logger.info("Initializing I2C bus")
try:
    bus = smbus.SMBus(I2C_BUS)
except Exception as e:
    logger.error(f"I2C initialization error: {e}")
    exit(1)

# Check WHO_AM_I register to verify magnetometer
logger.info("Reading WHO_AM_I register")
try:
    who_am_i = bus.read_byte_data(MAG_ADDRESS, WHO_AM_I_M)
    logger.info(f"WHO_AM_I: 0x{who_am_i:02x}")
    if who_am_i != 0x40:  # ISM303DAC magnetometer expected value
        logger.error("Incorrect WHO_AM_I value, expected 0x40")
        exit(1)
    who_am_i_a = bus.read_byte_data(ACC_ADDRESS, WHO_AM_I_A)
    logger.info(f"Accelerometer WHO_AM_I: 0x{who_am_i_a:02x}")
    if who_am_i_a != 0x43:  # ISM303DAC accelerometer expected value
        logger.error("Incorrect Accelerometer WHO_AM_I value, expected 0x43")
        exit(1)
except Exception as e:
    logger.error(f"WHO_AM_I read error: {e}")
    exit(1)

# Initialize MQTT client
logger.info("Initializing MQTT client")
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker")
        # Send device connect message
        connect_message = {"device": "ISM303DAC Magnetometer"}
        client.publish("v1/gateway/connect", json.dumps(connect_message), qos=1)
        logger.info("Published device connect message")
    else:
        logger.error(f"MQTT connection failed with code {rc}")

def on_publish(client, userdata, mid):
    logger.debug(f"Message {mid} published")

client.on_connect = on_connect
client.on_publish = on_publish
client.username_pw_set(GATEWAY_ACCESS_TOKEN)
try:
    client.connect(TB_GATEWAY_HOST, TB_GATEWAY_PORT, 60)
    client.loop_start()  # Start background loop for MQTT
except Exception as e:
    logger.error(f"MQTT connection error: {e}")
    exit(1)

# Initialize magnetometer (100Hz, continuous mode, high-resolution)
logger.info("Initializing magnetometer")
try:
    bus.write_byte_data(MAG_ADDRESS, CFG_REG_A_M, 0x0C)  # ODR=100Hz (11), MD=continuous (00)
    time.sleep(0.1)  # Allow initialization
    cfg_reg_a = bus.read_byte_data(MAG_ADDRESS, CFG_REG_A_M)
    logger.info(f"CFG_REG_A_M: 0x{cfg_reg_a:02x}")
    if cfg_reg_a != 0x0C:
        logger.warning("CFG_REG_A_M not set correctly")
except Exception as e:
    logger.error(f"Magnetometer initialization error: {e}")
    exit(1)

# Initialize accelerometer (100Hz, ±2g, high-resolution)
logger.info("Initializing accelerometer")
try:
    bus.write_byte_data(ACC_ADDRESS, CTRL1_XL, 0x38)  # ODR=100Hz (0011), FS=±2g (00), BW=400Hz
    time.sleep(0.1)
    ctrl1_xl = bus.read_byte_data(ACC_ADDRESS, CTRL1_XL)
    logger.info(f"Accelerometer CTRL1_XL: 0x{ctrl1_xl:02x}")
    if ctrl1_xl != 0x38:
        logger.warning("Accelerometer CTRL1_XL not set correctly")
except Exception as e:
    logger.error(f"Accelerometer initialization error: {e}")
    exit(1)

# Conversion function (approximating ism303dac_from_lsb_to_mG)
def lsb_to_mG(lsb):
    return lsb * 1.5  # Sensitivity ~1.5 mG/LSB per ISM303DAC datasheet

def lsb_to_mg(lsb):
    return lsb * 0.061  # Accelerometer sensitivity ~0.061 mg/LSB for ±2g range

# Main loop
logger.info("Starting main loop")
while True:
    try:
        # Check data ready status
        logger.debug("Reading magnetometer STATUS_REG_M")
        status = bus.read_byte_data(MAG_ADDRESS, STATUS_REG_M)
        logger.debug(f"STATUS_M: 0x{status:02x}")

        # Check data ready status for accelerometer
        logger.debug("Reading accelerometer STATUS_REG_A")
        status_a = bus.read_byte_data(ACC_ADDRESS, STATUS_REG_A)
        logger.debug(f"Accelerometer STATUS_A: 0x{status_a:02x}")

        if not (status & 0x08):  # ZYXDA bit
            logger.debug("Data not ready")
            time.sleep(0.1)
            continue

        # Read magnetometer data
        logger.debug("Reading magnetometer data")
        data_m = bus.read_i2c_block_data(MAG_ADDRESS, OUTX_L_REG_M, 6)
        x_m = (data_m[1] << 8) | data_m[0]
        y_m = (data_m[3] << 8) | data_m[2]
        z_m = (data_m[5] << 8) | data_m[4]
        if x_m > 32767: x_m -= 65536
        if y_m > 32767: y_m -= 65536
        if z_m > 32767: z_m -= 65536
        mag_x = lsb_to_mG(x_m)
        mag_y = lsb_to_mG(y_m)
        mag_z = lsb_to_mG(z_m)

        # Read accelerometer data
        logger.debug("Reading accelerometer data")
        data_a = bus.read_i2c_block_data(ACC_ADDRESS, OUTX_L_XL, 6)
        x_a = (data_a[1] << 8) | data_a[0]
        y_a = (data_a[3] << 8) | data_a[2]
        z_a = (data_a[5] << 8) | data_a[4]
        if x_a > 32767: x_a -= 65536
        if y_a > 32767: y_a -= 65536
        if z_a > 32767: z_a -= 65536
        acc_x = lsb_to_mg(x_a)
        acc_y = lsb_to_mg(y_a)
        acc_z = lsb_to_mg(z_a)

        # Prepare telemetry
        telemetry = {
            "deviceName": "ISM303DAC Sensor",
            "deviceType": "default",
            "magneticX": mag_x,
            "magneticY": mag_y,
            "magneticZ": mag_z,
            "accelX": acc_x,
            "accelY": acc_y,
            "accelZ": acc_z
        }
        logger.info(f"Magnetic Field - X: {mag_x:.2f} mG, Y: {mag_y:.2f} mG, Z: {mag_z:.2f} mG")
        logger.info(f"Acceleration - X: {acc_x:.2f} mg, Y: {acc_y:.2f} mg, Z: {acc_z:.2f} mg")

        # Publish to ThingsBoard
        logger.debug("Publishing telemetry")
        client.publish(
            "v1/gateway/telemetry",
            json.dumps({"ISM303DAC Sensor": [telemetry]}),
            qos=1
        )
        time.sleep(1)  # 1Hz update rate

    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        # Attempt to reconnect MQTT if disconnected
        if not client.is_connected():
            logger.info("Attempting to reconnect MQTT")
            try:
                client.reconnect()
            except Exception as reconn_e:
                logger.error(f"MQTT reconnect error: {reconn_e}")
        time.sleep(1)  # Reduced delay to avoid long pauses

# Cleanup (unreachable due to infinite loop)
bus.close()
client.loop_stop()
client.disconnect()