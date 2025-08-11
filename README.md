# ThingsBoard Raspberry Pi Gateway Backup

## Overview

This repository backs up the `gateway-pi` folder from a Raspberry Pi running ThingsBoard Gateway. It supports a lab setup with fewer than 10 sensors, including the ISM303DAC accelerometer/magnetometer, sending data to a local ThingsBoard instance via MQTT. Use this to replicate the setup.

## System Details

- **OS**: Raspberry Pi OS (64-bit)
- **ThingsBoard Version**: v3.6.2 CE (adjust to your version)
- **Sensors**: SHT45 Trinkey, ISM303DAC
- **Hardware**: Raspberry Pi 4, 4GB RAM

## Repository Contents

- `gateway-pi/`: Main folder with sensor scripts and configurations
  - `ISM303DAC-PID/`: Sensor driver or scripts for ISM303DAC from STMicroelectronics (https://github.com/STMicroelectronics/ism303dac-pid)
  - `tests`: script to test ISM303DAC magnetometer and accelerometer, some may not work anymore
  - `ism303dac_to_tb.py`: Python script to send ISM303DAC sensor data to Thingsboard
  - `mag_to_thingsboard.py`: Old python script to send ISM303DAC magnetometer sensor data to Thingsboard
  - `sht45_to_thingsboard.py`: Python script to send SHT45 Trinkey sensor data (temperature and humidity) to Thingsboard

## Contact

See [ThingsBoard CE docs](https://thingsboard.io/docs/) or community forums for support.
