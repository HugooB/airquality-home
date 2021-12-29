# Airquality Home Measurement System
Stuff to make the enviro+ air quality sensor and RPI working

## Requirements
- A computer to set up and configure your Raspberry Pi
- Micro USB Power supply for your Raspberry Pi 
- Micro SD Card (I have used a 32GB Sandisk Ultra ) to hold the operating system of your Raspberry Pi and the data you collect
- A way to read/write to your SD card from your computer
- Raspberry Pi 4
- Pimoroni Enviro+ sensor
- PMS5003 Matter sensor with cable 

## Install the hardware

## Install the Raspbian software

## Install Enviro+ libraries
https://learn.pimoroni.com/article/getting-started-with-enviro-plus

## Install influxDB

## Install Grafana

## Make sure that this script runs after powering up
1. Edit your crontab file with `sudo crontab -e`
2. Add the following line to the file:

```bash
@reboot python3 /home/pi/all_to_influxdb.py > /home/pi/measurement_logs.txt
```

3. Save and exit by typing `CTRL+X` and `Y`. 
4. Reboot your RPI to test it