from gpiozero import LED
from pydub import AudioSegment
from pydub.playback import play
import threading
import time

##################################################

tones = {
        1000: AudioSegment.from_wav("tones/audiocheck.net_sin_1000Hz_-3dBFS_3s.wav") - 30 # the -30 lowers the db by another 30 to be -33db
}

##################################################

radio_lock = threading.Lock()

def radio_busy() -> bool:
    radio_lock.locked()

ptt = LED(17, active_high=False)
ptt.off()

def play_tone(tone:int=1000, milliseconds:int=1000, blocking:bool=True) -> bool:
    file = None
    try:
        file = tones[tone]
    except KeyError as e:
        return False

    # to make a sound sample which is as long as desired, copy the full array data enough times and then a partial array data
    sample = file[:] * (milliseconds//len(file)) + file[0:milliseconds%len(file)]

    def tone_thread():
        with radio_lock:
            ptt.on()
            play(sample)
            ptt.off()

    if blocking:
        tone_thread()
    else: # nonblocking
        threading.Thread(target=tone_thread).start()

    return True

if __name__ == "__main__":
    i = 0
    while True:
        print(i)
        if 0==i%12:
            play_tone(1000, blocking=False)
        i+=1
        time.sleep(1)

