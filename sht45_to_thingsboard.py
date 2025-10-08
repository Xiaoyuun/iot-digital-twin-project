import time
import serial
import paho.mqtt.client as mqtt
import json
from config import GW_ACCESS_TOKEN, SHRINKEY_DEVICE_TOKEN

# Configuration
SERIAL_PORT = "/dev/ttyACM0"  # Check with 'ls /dev/tty*'
BAUD_RATE = 115200            # Default for SHT45 Trinkey
TB_GATEWAY_HOST = "localhost"
TB_GATEWAY_PORT = 1883
GATEWAY_ACCESS_TOKEN = GW_ACCESS_TOKEN
SHT45_DEVICE_TOKEN = SHRINKEY_DEVICE_TOKEN  # From ThingsBoard device credentials
# Initialize serial connection
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    ser.flush()
except serial.SerialException as e:
    print(f"Serial error: {e}")
    exit(1)

# Initialize MQTT client
client = mqtt.Client()
client.username_pw_set(GATEWAY_ACCESS_TOKEN)
try:
    client.connect(TB_GATEWAY_HOST, TB_GATEWAY_PORT, 60)
    # Send device connect message
    connect_message = {
        "device": "SHT45 Trinkey Sensor"
    }
    client.publish("v1/gateway/connect", json.dumps(connect_message))
except Exception as e:
    print(f"MQTT connection error: {e}")
    exit(1)

# Main loop
while True:
    try:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            if line:
                # Parse CSV: <serial_number>,<temperature>,<humidity>,<touch_value>
                parts = line.split(',')
                if len(parts) >= 3:
                    temperature = float(parts[1])
                    humidity = float(parts[2])
                    telemetry = {
                        "deviceName": "SHT45 Trinkey Sensor",
                        "deviceType": "default",
                        "temperature": temperature,
                        "humidity": humidity
                    }
                    print(f"Temperature: {temperature:.2f} C, Humidity: {humidity:.2f} %")
                    client.publish(
                        "v1/gateway/telemetry", 
                        json.dumps(telemetry)
                    )
        time.sleep(1)  # Adjust based on Trinkey output rate
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)

# Cleanup (unreachable due to infinite loop, but included for completeness)
ser.close()
client.disconnect()