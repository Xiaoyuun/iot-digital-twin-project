#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#include <string.h>
#include "ism303dac_reg.h"

#define I2C_DEVICE "/dev/i2c-1" // I²C bus on Raspberry Pi
#define ACCEL_I2C_ADDR 0x1D     // ISM303DAC accelerometer I²C address
#define MAG_I2C_ADDR 0x1E       // ISM303DAC magnetometer I²C address

// I²C handle structure
typedef struct {
    int fd; // File descriptor for I²C device
    uint8_t addr; // I²C address
} i2c_handle_t;

// Platform write function
int32_t platform_write(void *handle, uint8_t reg, const uint8_t *bufp, uint16_t len) {
    i2c_handle_t *h = (i2c_handle_t *)handle;
    uint8_t *buffer = malloc(len + 1);
    if (!buffer) return -1;

    buffer[0] = reg; // Register address
    memcpy(&buffer[1], bufp, len); // Data

    // Set I²C slave address
    if (ioctl(h->fd, I2C_SLAVE, h->addr) < 0) {
        free(buffer);
        return -1;
    }

    // Write data
    if (write(h->fd, buffer, len + 1) != len + 1) {
        free(buffer);
        return -1;
    }

    free(buffer);
    return 0; // Success
}

// Platform read function
int32_t platform_read(void *handle, uint8_t reg, uint8_t *bufp, uint16_t len) {
    i2c_handle_t *h = (i2c_handle_t *)handle;

    // Set I²C slave address
    if (ioctl(h->fd, I2C_SLAVE, h->addr) < 0) {
        return -1;
    }

    // Write register address
    if (write(h->fd, &reg, 1) != 1) {
        return -1;
    }

    // Read data
    if (read(h->fd, bufp, len) != len) {
        return -1;
    }

    return 0; // Success
}

// Platform delay function
void platform_delay(uint32_t millisec) {
    usleep(millisec * 1000); // Convert ms to us
}

int main() {
    // Initialize I²C device
    int fd = open(I2C_DEVICE, O_RDWR);
    if (fd < 0) {
        perror("Failed to open I²C device");
        return 1;
    }

    // Initialize accelerometer handle
    i2c_handle_t accel_handle = { .fd = fd, .addr = ACCEL_I2C_ADDR };
    ism303dac_ctx_t accel_ctx;
    accel_ctx.write_reg = platform_write;
    accel_ctx.read_reg = platform_read;
    accel_ctx.mdelay = platform_delay;
    accel_ctx.handle = &accel_handle;

    // Initialize magnetometer handle
    i2c_handle_t mag_handle = { .fd = fd, .addr = MAG_I2C_ADDR };
    ism303dac_ctx_t mag_ctx;
    mag_ctx.write_reg = platform_write;
    mag_ctx.read_reg = platform_read;
    mag_ctx.mdelay = platform_delay;
    mag_ctx.handle = &mag_handle;

    // Check device ID for accelerometer
    uint8_t whoami;
    ism303dac_xl_device_id_get(&accel_ctx, &whoami);
    if (whoami != ISM303DAC_ID_XL) {
        printf("Accelerometer not detected (WHOAMI: 0x%02X, expected 0x%02X)\n", whoami, ISM303DAC_ID_XL);
        close(fd);
        return 1;
    }
    printf("Accelerometer detected (WHOAMI: 0x%02X)\n", whoami);

    // Check device ID for magnetometer
    ism303dac_mag_device_id_get(&mag_ctx, &whoami);
    if (whoami != ISM303DAC_ID_MAG) {
        printf("Magnetometer not detected (WHOAMI: 0x%02X, expected 0x%02X)\n", whoami, ISM303DAC_ID_MAG);
        close(fd);
        return 1;
    }
    printf("Magnetometer detected (WHOAMI: 0x%02X)\n", whoami);

    // Configure accelerometer
    ism303dac_xl_power_mode_set(&accel_ctx, ISM303DAC_XL_HIGH_PERFORMANCE); // High performance mode
    ism303dac_xl_data_rate_set(&accel_ctx, ISM303DAC_XL_ODR_100Hz);        // 100 Hz output data rate

    // Configure magnetometer
    ism303dac_mag_power_mode_set(&mag_ctx, ISM303DAC_CONTINUOUS_MODE); // Continuous mode
    ism303dac_mag_data_rate_set(&mag_ctx, ISM303DAC_ODR_100Hz);        // 100 Hz output data rate

    // Main loop to read and print data
    while (1) {
        // Check if accelerometer data is available
        ism303dac_xl_status_reg_t status;
        ism303dac_xl_status_get(&accel_ctx, &status);
        if (status.drdy_xl) {
            int16_t accel_data[3];
            ism303dac_acceleration_raw_get(&accel_ctx, accel_data);
            float accel_mg[3];
            for (int i = 0; i < 3; i++) {
                accel_mg[i] = ism303dac_from_fs_2g_to_mg(accel_data[i]);
            }
            printf("Accel [mg]: X=%.2f, Y=%.2f, Z=%.2f\n", accel_mg[0], accel_mg[1], accel_mg[2]);
        }

        // Check if magnetometer data is available
        ism303dac_mag_status_reg_t mag_status;
        ism303dac_mag_status_get(&mag_ctx, &mag_status);
        if (mag_status.drdy) {
            int16_t mag_data[3];
            ism303dac_magnetic_raw_get(&mag_ctx, mag_data);
            float mag_mgauss[3];
            for (int i = 0; i < 3; i++) {
                mag_mgauss[i] = ism303dac_from_lsb_to_mgauss(mag_data[i]);
            }
            printf("Mag [mGauss]: X=%.2f, Y=%.2f, Z=%.2f\n", mag_mgauss[0], mag_mgauss[1], mag_mgauss[2]);
        }

        platform_delay(100); // Delay 100ms (~10Hz update rate)
    }

    close(fd);
    return 0;
}
