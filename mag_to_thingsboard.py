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
TB_GATEWAY_HOST = TB_GW_HOST  # ThingsBoard server
TB_GATEWAY_PORT = 1883
GATEWAY_ACCESS_TOKEN = GW_ACCESS_TOKEN

# ISM303DAC register addresses (from ism303dac_reg.h)
WHO_AM_I_M = 0x4F
CFG_REG_A_M = 0x60
STATUS_REG_M = 0x67
OUTX_L_REG_M = 0x68

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

# Conversion function (approximating ism303dac_from_lsb_to_mG)
def lsb_to_mG(lsb):
    return lsb * 1.5  # Sensitivity ~1.5 mG/LSB per ISM303DAC datasheet

# Main loop
logger.info("Starting main loop")
while True:
    try:
        # Check data ready status
        logger.debug("Reading STATUS_REG_M")
        status = bus.read_byte_data(MAG_ADDRESS, STATUS_REG_M)
        logger.debug(f"STATUS_M: 0x{status:02x}")
        if not (status & 0x08):  # ZYXDA bit
            logger.debug("Data not ready")
            time.sleep(0.1)
            continue

        # Read magnetometer data
        logger.debug("Reading magnetometer data")
        data = bus.read_i2c_block_data(MAG_ADDRESS, OUTX_L_REG_M, 6)
        logger.debug(f"Raw data: {data}")
        x = (data[1] << 8) | data[0]
        y = (data[3] << 8) | data[2]
        z = (data[5] << 8) | data[4]
        if x > 32767: x -= 65536  # Convert to signed 16-bit
        if y > 32767: y -= 65536
        if z > 32767: z -= 65536

        # Convert to milliGauss
        mag_x = lsb_to_mG(x)
        mag_y = lsb_to_mG(y)
        mag_z = lsb_to_mG(z)

        # Prepare telemetry
        telemetry = {
            "deviceName": "ISM303DAC Magnetometer",
            "deviceType": "default",
            "magneticX": mag_x,
            "magneticY": mag_y,
            "magneticZ": mag_z
        }
        logger.info(f"Magnetic Field - X: {mag_x:.2f} mG, Y: {mag_y:.2f} mG, Z: {mag_z:.2f} mG")

        # Publish to ThingsBoard
        logger.debug("Publishing telemetry")
        client.publish(
            "v1/gateway/telemetry",
            json.dumps({"ISM303DAC Magnetometer": [telemetry]}),
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