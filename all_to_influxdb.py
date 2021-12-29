# -*- coding: utf-8 -*-
#!/usr/bin/env python3

"""Send data using the InfluxDB client."""

import time
import colorsys
import os
import sys
import socket
import configparser
import logging

import ST7735

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

from bme280 import BME280
from pms5003 import PMS5003, ReadTimeoutError
from enviroplus import gas

from subprocess import PIPE, Popen

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from fonts.ttf import RobotoMedium as UserFont

from influxdb import InfluxDBClient

# Get the temperature of the CPU for compensation
def get_cpu_temperature():
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        return int(f.read()) / 1000.0

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

logging.info("Started monitoring process..")

# Load the configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# BME280 temperature/pressure/humidity sensor
bme280 = BME280()

# PMS5003 particle matter sensor
pms5003 = PMS5003()

# Create ST7735 LCD display class
st7735 = ST7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)

# Initialize display.
st7735.begin()

# Initialize display
WIDTH = st7735.width
HEIGHT = st7735.height

# Set up canvas and font
img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)
top_pos = 25

# Set up InfluxDB
influx = InfluxDBClient(host=config['influxdb']['host'],
                        username=config['influxdb']['username'],
                        password=config['influxdb']['password'],
                        database=config['influxdb']['database'])

# Create the influxDB data object to store data
influx_data = [
        {
            "measurement": config['influxdb']['measurement'],
            "tags": {
                "host": "enviroplus"
            },
            "fields": { }
        }
    ]

# Setup the screen and show "monitoring"
font_size = 25
font = ImageFont.truetype(UserFont, font_size)
text_colour = (255, 255, 255)
back_colour = (0, 170, 170)

message = "Monitoring!"
size_x, size_y = draw.textsize(message, font)

# Calculate text position
x = (WIDTH - size_x) / 2
y = (HEIGHT / 2) - (size_y / 2)

# Draw background rectangle and write text.
draw.rectangle((0, 0, 160, 80), back_colour)
draw.text((x, y), message, font=font, fill=text_colour)
st7735.display(img)

# The main loop
try:
    iterations = 0
    while True:
        try:
            # Initialize a data point - reading from all sensors
            reading = {}

            # Get data from the proximity sensor
            proximity = ltr559.get_proximity()

            # Compensated Temperature
            cpu_temp = get_cpu_temperature()

            # Fill the readings dictionary
            reading['ltr559.proximity'] = proximity

            # If something is close to the proximity sensor, return just 1.0
            if proximity < 10:
                reading['ltr559.lux'] = ltr559.get_lux()
            else:
                reading['ltr559.lux'] = 1.0

            # After a warm up period, report the temperature from the sensor
            if iterations >= 6:
                reading['bme280.temperature'] = bme280.get_temperature() - 2.2
            reading['bme280.pressure'] = bme280.get_pressure()
            reading['bme280.humidity'] = bme280.get_humidity()

            # Get gas sensor readings
            gas_data = gas.read_all()
            reading['mics6814.oxidising'] = gas_data.oxidising
            reading['mics6814.reducing'] = gas_data.reducing
            reading['mics6814.nh3'] = gas_data.nh3

            # Get particle matter sensor readings
            particle_data = pms5003.read()
            reading['pms5003.pm1'] = particle_data.pm_ug_per_m3(1.0)
            reading['pms5003.pm25'] = particle_data.pm_ug_per_m3(2.5)
            reading['pms5003.pm10'] = particle_data.pm_ug_per_m3(10.0)

            reading['pms5003.03um'] = particle_data.pm_per_1l_air(0.3)
            reading['pms5003.05um'] = particle_data.pm_per_1l_air(0.5)
            reading['pms5003.10um'] = particle_data.pm_per_1l_air(1.0)
            reading['pms5003.25um'] = particle_data.pm_per_1l_air(2.5)
            reading['pms5003.50um'] = particle_data.pm_per_1l_air(5)
            reading['pms5003.100um'] = particle_data.pm_per_1l_air(10)

            if iterations >= 3:
                influx_data[0]["fields"] = reading
                logging.debug("Write points: {0}".format(influx_data))
                influx.write_points(influx_data)
            else:
                logging.warning("Skip iteration: " + str(iterations))

            time.sleep(10)
            iterations += 1
        except Exception as error:
            logging.error(f"Measurement error: {error}")

# Exit cleanly
except KeyboardInterrupt:
    logging.info("Received CTRL+C interrupt, exiting!")
    sys.exit(0)