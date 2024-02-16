# few things, I created a file called CAPSTONE in the first non root user folder, 
# which is home, to do this use the command 'mkdir CAPSTONE' in your terminal on the pi

# theoretical and needs testing in order to determine if this works
# have not implemnted the hardcase mode yet, this assumes you are changing mode over mission planner

# we may or may not do a file that starts on boot, may have user input what they want to do (hard case or drone flight), need different scripts for both
######################################################################
# MUST DO ON THE PI, IF NOT FOLLOWED IT WILL NOT WORK, DO IN THIS ORDER, do the commands in the '', do not include the ''
# 'chmod 777 STEdata.py'
# 'crontab -e' then at the end of the file add the following '@reboot python3 /home/Lance/STEdata.py' and hit enter then cmd-s cmd-x to save and close the file
# the script will now run anytime the pi reboots
######################################################################

import smbus
import time
import datetime
import struct

# setup I2C and assuming /dev/i2c-1
bus = smbus.SMBus(1)  
 # replace with actual i2c address idk what it is for the drone, i2cdetect can see it when connected to pi and command is run on pi
device_address = 0xXX 

# define log file path, look at notes above, 'Lance' is the name of my Pi, your name is blank@raspberrypi in the terminal, put blank where Lance is
log_file_dir = "/home/Lance/CAPSTONE"
# this creates the file that will store the 
log_file_name = "VSTE_Log_{date}.txt".format(date=datetime.datetime.now().strftime("%Y-%m-%d"))
log_file_path = os.path.join(log_file_dir, log_file_name)

# operational modes
STANDBY = "Standby"
ACTIVE_TRANSMIT = "Active Transmit"
PASSIVE_TRANSMIT = "Passive Transmit"
# initial mode
current_mode = STANDBY  

# this makes sure the log file exists, will be run recursively from the main
def ensure_log_file_exists():
    # if it doesnt exist it will create the file and add the header on top of it
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w") as file:
            file.write("#Time_Logged\t#Tx_Start\t#Tone\t#Lat\t#Long\t#Power\n")


# this will actually log the data into the file
def log_transmission_data(data):
    # this will open the file in append mode so it will be able to add to it
    with open(log_file_path, "a") as file:
        # this will add the data in the same format as GD has it with the time, data including the start, tone, lat etc
        time_logged = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S.%f")[:-3]
        formatted_data = f"{time_logged}\t{data['tx_start']}\t{data['tone']}\t{data['lat']}\t{data['long']}\t{data['power']}\n"
        file.write(formatted_data)

######################################################################################################################
# the next section is done with research and some assumptions of how it will work, may need to change at a later date
#######################################################################################################################

# yeah this is the part im struggling with, have some assumptions here, assuming 4 bytes for unix timestamp, 8 bytes for both latitude and longitude, 2 bytes for tone
# and 4 bytes for power level (do we need that?)
def read_i2c_data(address):

    # need some help here
    try:
        # read a block of 26 bytes from the device
        data = bus.read_i2c_block_data(address, 0, 26)

        # data should be in this order but it is able to be reordered if not
        timestamp, lat, long, tone, power = struct.unpack('>IddHf', bytes(data))

        # this will allow us to read the timestamp (i do not want to admit how long this took me to figure out)
        timestamp = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # format the latitude and longitude so they are able to be read in floating point because they are most likely going to be in degrees
        # may need to adjust this at a later data after we see how the gps formats the lat and long
        lat = "{:.6f}N".format(lat) if lat >= 0 else "{:.6f}S".format(abs(lat))
        long = "{:.6f}E".format(long) if long >= 0 else "{:.6f}W".format(abs(long))

        # convert tone to kHz (it should be in kHz but this requires a test to see, I do not know radios at all)
        tone_khz = tone / 1000.0

        # this is the format that the read i2c should return 
        return {
            "tx_start": timestamp,
            "tone": "{} kHz".format(tone_khz),
            "lat": lat,
            "long": long,
            "power": str(power)
        }
    # this means I messed up, figure out error handling at a later date
    except Exception as e:
        print(f"Error reading I2C data: {e}")
        return None

# this is the main function that can be recursively called
def main():
    global current_mode

    # create the log if it doesn't already exist
    ensure_log_file_exists()

    while True:
        if current_mode == STANDBY:
            # need to implement the mode switches, should be easy, was more worried about the harder parts such as i2c
            pass
        #if it is in active or passive mode, do the data collection, need to implement when more than 30ft of distance is traved and more than 1s of intervals
        elif current_mode in [ACTIVE_TRANSMIT, PASSIVE_TRANSMIT]:
            data = read_i2c_data(device_address)
            log_transmission_data(data)
                
        
        # implement the logic switches here, will do soon
                

        # this needs to change with the mdoe, will implement more later
        # temporary break, ignore until later
        time.sleep(1)  
        False

# functionality not fully implemented, do not run this fully yet
#if __name__ == "__main__":
#    main()
