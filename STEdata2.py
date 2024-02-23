import time
import datetime
import struct
import os
import serial
import pynmea2

gps_port = '/dev/ttyUSB0'
gps_baudrate = 4800

#this will create the file
log_file_dir = "/home/Lance/CAPSTONE"
current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
file_name = f"DF_Vessel_{current_time}.txt"
log_file_path = os.path.join(log_file_dir, file_name)

#These are the modes
STANDBY = "Standby"
ACTIVE = "Active"
PASSIVE = "Passive"

current_mode = STANDBY

# Define the header
header = "#Time_Logged\t#Tx_Start\t#Tone\t#Lat\t#Long\t#Power\n"

# Create the file, write the header
with open(log_file_path, "w") as file:
    file.write(header)

def log_data(tx_start, tone, lat, long, power):
        #format for logging
        time_logged = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S.%f")[:-3]
        #append the file
        with open(log_file_path, "a") as file:
                fdata = f"{time_logged}\t{tx_start}\t{tone}\t{lat}\t{long}\t{power}\n"
                file.write(fdata)

#I really hate gps data ngl
def get_gps_data():
        #THIS IS HARDER THAN I THOUGHT
    with serial.Serial(gps_port, baudrate=gps_baudrate, timeout=1) as ser:
        #MAKE SURE THE GPS DATA IS NEW, youtube said to
        for _ in range(10):
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if line.startswith('$GPGGA'):
                try:
                    msg = pynmea2.parse(line)
                    return {'lat': msg.latitude, 'lon': msg.longitude}
                except pynmea2.ParseError:
                    pass
    return {'lat': None, 'lon': None}

def main():
        gps_data = get_gps_data()
        tone = 2
        tx_start = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_data(tx_start, tone, gps_data['lat'], gps_data['lon'], 0)

if __name__ == "__main__":
        main()
