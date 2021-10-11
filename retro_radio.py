#!/usr/bin/env python

"""
Following files are essential parts that need to stay in this directory:
- this file
- rotary_encoder.py (reads the rotary encoder)
- playlist.csv (the list of radio stations and audio files)
    the following columns are required:
    col 0: lower boundary of rotary encoder position to play that station
    col 1: upper boundary of rotary encoder position to play that station
    col 2: radio station stream url
    optional columns:
    col 3: station description (optional)
    col 4: hompage url of radio station (optional)
- position.py (persistence of rotary encoder position between pi startups)
- a noise-file (mp3). This is played if there is no assigned radio station to a given position
"""

import pigpio            # Import Pi GPIO Library (for rotary encoder)
import rotary_encoder    # Import the rotary encoder library from rotary_encoder.py file
import RPi.GPIO as GPIO  # Import the other Raspberry Pi GPIO library (for button)
import vlc               # Import VLC for Python Library (for playing audio)
import csv              # csv file support
from position import start_position  # Import the last encoder position saved to position.py file
import time              # Import the time library


# Variables files and paths
ABSOLUTE_PATH = "/home/pi/rustafari_radio_noserver/"      # Absolute file path of this directory
POSITION_PY_FILE = ABSOLUTE_PATH + "position.py"           # Local position Python file to read on start-up
PLAYLIST_CSV_FILE = ABSOLUTE_PATH + "playlist.csv"         # Local csv file with playlist
NOISE_FILE = ABSOLUTE_PATH + "rauschen.mp3"                 # Local noise file

# gpio pins:
SD_BUTTON = 15   # BCM pin for shutdown button (BCM 15 = GPIO 10)
CLK_PIN = 18     # BCM pin for CLK signal on rotary encoder (BCM 18 = GPIO 12)
DT_PIN = 17      # BCM pin for DT signal on rotary encoder (BCM 17 = GPIO 11)

# Setup of button
GPIO.setmode(GPIO.BCM)

# Device specific values: Lowest and highest position of the radio pointer.
MIN_POS = 0      # minimum value of rotary encoder
MAX_POS = 1020   # maximum value of rotary encoder.


def read_csv():
    stations = []
    with open(PLAYLIST_CSV_FILE, newline='') as csvfile:
        playlist = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in playlist:
            # convert position values to integers:
            try:
                row[0] = int(row[0])
                row[1] = int(row[1])
            except:
                print(f'Error in csv file line {row}: boundary values must be integers')
                exit()
            stations.append(row)
        # check consistency of csv file:
        csv_sanity_check(stations)
        # append noise file as last entry:
        stations.append([-1, -1, NOISE_FILE])
    return stations


def csv_sanity_check(stations):
    for i in range(0, len(stations) - 1):
        # check if lower boundary and upper boundary are correct:
        if stations[i][0] > stations[i][1]:
            print(f'Error in csv file line {i}: check boundaries')
            exit()
        # check that boundary ranges are non-overlapping
        if stations[i][1] >= stations[i + 1][0]:
            print(f'Error in csv file line {i} / {i + 1}: check boundaries')
            exit()


def populate_postostation(sl):
    # making a list assigning rotary enocder positions to radio stations:
    # list[position of rotary-encoder] = line in station_list
    pos2station = [-1 for _ in range(MIN_POS, MAX_POS + 1)]
    l = len(sl)
    # go through stations, excluding last line (noise file)
    for line_nr in range(l - 1):
        low = sl[line_nr][0]
        upp = sl[line_nr][1]
        for p in range(low, upp + 1):
            pos2station[p] = line_nr
    return pos2station


def play(url):
    player.stop()
    media = instance.media_new(url)
    player.set_media(media)
    player.play()


def callback_rotary_encoder(way):
    # This is called if there is a change in the position of the rotary encoder.
    # It will trigger the playback of a new radio station

    # makes sure pos does not go beyond min/max position
    global pos
    if (pos >= MAX_POS and way == 1) or (pos <= MIN_POS and way == -1):
        way = 0
    # check if new radio station needs to be selected
    if posToStation[pos] != posToStation[pos + way]:
        pos += way
        play(station_list[posToStation[pos]][2])
    else:
        pos += way
    # write position to file in case of shutdown or crash
    write_position_files()


def callback_button(pin):
    # this is called when the button is pressed. It toggles play/pause.
    if player.is_playing() == 1:
        player.stop()
    else:
        player.play()


def write_position_files():
    with open(POSITION_PY_FILE, "w") as position_py_file:
        # write the position to the Python file
        position_py_file.write('#!/usr/bin/env python\n\n'+'start_position = ' + str(pos))


def cleanup():
    decoder.cancel()
    GPIO.cleanup()
    pi.stop()

# Setup of rotary encoder
pi = pigpio.pi()

# Starting position of rotary encoder
pos = start_position

# get station information from csv file and generate variables
# populate station_list from excel file
station_list = read_csv()

# populate posToStation from station_list
posToStation = populate_postostation(station_list)

# Rotary encoder setup 
decoder = rotary_encoder.decoder(pi, DT_PIN, CLK_PIN, callback_rotary_encoder)

# Button setup
GPIO.setwarnings(False)
GPIO.setup(SD_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(SD_BUTTON, GPIO.RISING, callback=callback_button, bouncetime=300)

# initiate VLC for Python
instance = vlc.Instance('--input-repeat=-1', '--fullscreen')
player = instance.media_player_new()

# play station according to saved position
play(station_list[posToStation[pos]][2])

# wait for callbacks from the button and rotary encoder forever:
while True:
    time.sleep(100)
