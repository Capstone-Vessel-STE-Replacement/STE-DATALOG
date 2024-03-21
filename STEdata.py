import time
import math
import datetime
import struct
import os
import serial
import pynmea2
import threading
import shutil
import smbus2
from geopy.distance import geodesic

import radio

# storage_location = '/media/Lance/789A-55B910'
storage_location = '/media/gdkita/Removable Disk/CSE424/logs'

###################################################################################

##########################
#### CONFIGURABLE DUTY CYCLES
active_wait_time = 1
passive_wait_time = 1
passive_distance_travelled = 30
##############################


current_thread = None 
stop_event = threading.Event()

#####################################################
# for gps time instead of built in time
# Everything with gps is here
def get_gps_time():
    with serial.Serial(gps_port, baudrate=gps_baudrate, timeout=1) as ser:
        for _ in range(40):  # Read multiple lines to find a valid time sentence
            line = ser.readline().decode('ascii', errors='ignore').strip()
            try:
                if line.startswith('$GPRMC'):
                    msg = pynmea2.parse(line)
                    if msg.status == 'A':  # Status 'A' indicates valid data
                        gps_time = msg.timestamp.strftime('%H:%M:%S')
                        gps_date = msg.datestamp.strftime('%Y-%m-%d')
                        return f'{gps_date}_{gps_time}'
            except pynmea2.ParseError:
                continue
    return False


def passive_gps_time():
    with serial.Serial(gps_port, baudrate=gps_baudrate, timeout=1) as ser:
        for _ in range(40):  # Read multiple lines to find a valid time sentence
            line = ser.readline().decode('ascii', errors='ignore').strip()
            try:
                if line.startswith('$GPRMC'):
                    msg = pynmea2.parse(line)
                    if msg.status == 'A':  # Status 'A' indicates valid data
                        # Parse the time from the GPS data
                        gps_hours = msg.timestamp.hour
                        gps_minutes = msg.timestamp.minute
                        gps_seconds = msg.timestamp.second
                        # Convert to total seconds since midnight
                        total_seconds = (gps_hours * 3600) + (gps_minutes * 60) + gps_seconds
                        return float(total_seconds)
            except pynmea2.ParseError:
                continue
    return None

def get_gps_data():
	pdop = None  # Initialize PDOP
	gps_data = {'lat': None, 'lon': None, 'pdop': None}
	with serial.Serial(gps_port, baudrate=gps_baudrate, timeout=1) as ser:
		for _ in range(40):  # Increase range to ensure we read both GPGGA and GPGSA
			line = ser.readline().decode('ascii', errors='ignore').strip()
			try:
				if line.startswith('$GPGGA'):
					msg = pynmea2.parse(line)
					gps_data['lat'] = msg.latitude
					gps_data['lon'] = msg.longitude
				elif line.startswith('$GPGSA'):
					msg = pynmea2.parse(line)
					pdop = msg.pdop
			except pynmea2.ParseError:
				pass

			# Check if we have both GPS and PDOP data, then break early
			if gps_data['lat'] and gps_data['lon'] and pdop:
				gps_data['pdop'] = pdop
				break
	return gps_data


####################################################################################
gps_port = '/dev/ttyUSB0'
gps_baudrate = 4800
tone_hold = 1000 # hz tone created on for transmissions
mode_lock = threading.Lock()

# this will create the file
log_file_dir = "/home/gdkita/Documents"
# log_file_dir = "/home/Lance/CAPSTONE" # XXX
#current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
current_time = get_gps_time()

file_name = f"DF_Vessel_{current_time.replace(':', '-')}.txt"
log_file_path = os.path.join(log_file_dir, file_name)

# These are the modes
STANDBY = "Standby"
ACTIVE = "Active"
PASSIVE = "Passive"

current_mode = STANDBY

mode_lock = threading.Lock()

def change_mode(new_mode):
    global current_mode, current_thread
    with mode_lock:
        # Check if the mode is actually changing to prevent unnecessary thread restarts
        if current_mode == new_mode:
            return
        current_mode = new_mode
        print(f"Mode changed to {current_mode}")
    
    if current_thread is not None:
        # Assuming your mode operation functions check `current_mode` and exit if it has changed
        current_thread.join()  # Wait for the current thread to finish its execution
    
    # Start a new thread based on the new mode
    if current_mode == ACTIVE:
        current_thread = threading.Thread(target=active_mode)
        current_thread.start()
    elif current_mode == PASSIVE:
        current_thread = threading.Thread(target=passive_mode)
        current_thread.start()
    elif current_mode == STANDBY:
        current_thread = threading.Thread(target=standby_mode)
        current_thread.start()

# Define the header
header = "#Time_Logged\t#Tx_Start\t#Tone\t#Lat\t#Long\t#Power\t#Accuracy\t#Mode\n"

# Create the file, write the header
with open(log_file_path, "w") as file:
    file.write(header)

def log_data(tx_start, tone, lat, long, power, pdop):
	#did this as a check to make sure two threads cant access this data at the same time
	with mode_lock:
		if current_mode == "Active":
			# format for logging
			# time_logged = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S.%f")[:-3]
			# append the file
			time_logged = get_gps_time()
			with open(log_file_path, "a") as file:
				fdata = f"{time_logged}\t{tx_start}\t{tone}\t{lat}\t{long}\t{power}\t{pdop}\t{current_mode}\n"
				file.write(fdata)
		elif current_mode == "Passive":
			# format for logging
			# time_logged = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S.%f")[:-3]
			# append the file
			time_logged = get_gps_time()
			with open(log_file_path, "a") as file:
				fdata = f"{time_logged}\t{tx_start}\t{tone}\t{lat}\t{long}\t{power}\t{pdop}\t{current_mode}\n"
				file.write(fdata)


def calculate_distance(lock1, lock2):
	# have to use meters, it is a built in function, convert to feet
	distance_in_meters = geodesic(lock1, lock2).meters
	return distance_in_meters * 3.28084

def radio_overhead():
	radio.play_tone(tone=tone_hold, milliseconds=1000, blocking=True)

previous_location = None
# previous_transmit_time = time.time()
previous_transmit_time = passive_gps_time()
def passive_mode():
	global current_mode
	while current_mode == PASSIVE:
		global previous_location, previous_transmit_time
		minimum_distance = passive_distance_travelled  # Minimum distance in feet before transmitting
		minimum_time = passive_wait_time  # Minimum time in seconds before transmitting

		current_location = get_gps_data()
		# current_time = time.time()
		current_time = passive_gps_time()

		if previous_location and current_location['lat'] and current_location['lon']:
			distance = calculate_distance((previous_location['lat'],previous_location['lon']), (current_location['lat'], current_location['lon']))
			time_elapsed = current_time - previous_transmit_time

			if distance >= minimum_distance and time_elapsed >= minimum_time:
				# Conditions met, log data
				radio_overhead()
				# tx_start = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
				tx_start = get_gps_time()
				pdop = current_location['pdop'] if current_location['pdop'] else "N/A"
				log_data(tx_start, str(tone_hold), current_location['lat'], current_location['lon'], "0", pdop) # TODO make the power represent something or remove it
				previous_transmit_time = current_time
				destination_path = storage_location
				try:
					shutil.copy(log_file_path, destination_path)
				except Exception as e:
					print(f"{e}")

		previous_location = current_location
		time.sleep(0.1)  # Sleep for a bit before checking again		
	
def active_mode():
	global current_mode
	while current_mode == ACTIVE:
		current_location = get_gps_data()
		# tx_start = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
		tx_start = get_gps_time()
		radio_overhead()
		pdop = current_location['pdop'] if current_location['pdop'] else "N/A"
		log_data(tx_start, str(tone_hold), current_location['lat'], current_location['lon'],"0", pdop) # TODO make the power value represent something or remove it
		
		#############
		#PUT REMOVABLE DRIVE NAME HERE
		destination_path = storage_location
		try:
			shutil.copy(log_file_path, destination_path)
		except Exception as e:
			print(f"{e}")

		time.sleep(active_wait_time)
		time.sleep(0.1)

def standby_mode():
	global is_ready, current_mode
	while current_mode == STANDBY and not stop_event.is_set():

		# Checks for the standby mode requirements
		gps_in_accuracy = is_gps_accurate()
		gps_time = is_gps_time()
		removable_storage = storage_ready()
		rf_ready = rf_transmitter()
		controller_ready = system_controller()
		downlink_ready = downlink_status()

		is_ready = all([gps_in_accuracy, gps_time, removable_storage, rf_ready, controller_ready, downlink_ready])

		# testing purposes, lets you know what is wrong
		if is_ready:
			print("System ready")
		else:
			print("Checking conditions, SYSTEM NOT READY")
			if not gps_in_accuracy:
				print("GPS ACCURACY OUT OF RANGE")
			if not gps_time:
				print("GPS time NOT AQUIRED")
			if not removable_storage:
				print("Thumbdrive not found")
			if not rf_ready:
				print("Plug in the radio")
			if not controller_ready:
				print("System controller has a problem")
			if not downlink_ready:
				print("Mission planner error")

		time.sleep(5)

##################################
#STANDBY MODE CHECKS
def is_gps_accurate():
	current_location = get_gps_data()
	pdop = current_location['pdop'] if current_location['pdop'] else "N/A"
	if pdop != "N/A":
		pdop_value = float(pdop)
		if pdop_value < 3.0:
			print("PDOP is below 3.0")
			return True
		else:
			print("PDOP IS ABOVE 3.0")
			return False
	else:
		print("PDOP IS N/A")
		return False

def is_gps_time():
	return bool(get_gps_time())

def storage_ready():
	return os.path.ismount(storage_location) and os.access(storage_location, os.W_OK)

def rf_transmitter():
	# dont know what to put here atm
	return True

def system_controller():
	# fix later
	return True

def downlink_status():
	# fix later
	return True
##################################
	

if __name__ == "__main__":
    from HCUI import HCUIApp
    HCUIApp().run() # run the Kivy application
