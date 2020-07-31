#!/usr/bin/python3
#
#

import sys
import time
import signal
import pigpio
import schedule
import configparser
import RPi.GPIO as GPIO
from pathlib import Path
from influxdb import InfluxDBClient

homedir = str(Path.home())

CONFIGFILE = '/etc/presence.conf'

config = configparser.ConfigParser()

if not Path(CONFIGFILE).is_file():
    config['GPIOPIR'] = {
        'SENSOR_A_PIN': 7,
        'SENSOR_B_PIN': 8,
    }
    config['INFLUXDBCONF'] = {
        'IFDB_IP': 'InfluxDP IP',
        'IFDB_PORT': 'InfluxDP port',
        'IFDB_USER': 'InfluxDP user',
        'IFDB_PW': 'InfluxDB password',
        'IFDB_DB': 'InfluxDP database'
    }
    config['DAEMON'] = {
        'CLEARONSTART': 'False',
        'BOUNCETIME': '1',
        'LOGFILE': '/var/log/presence.log',
        'VERBOSE': 'True'
    }
    with open(CONFIGFILE, 'w') as f:
        config.write(f)
else:
    config.read(CONFIGFILE)

IFDB_IP = config['INFLUXDBCONF']['IFDB_IP']
IFDB_PORT = int(config['INFLUXDBCONF']['IFDB_PORT'])
IFDB_USER = config['INFLUXDBCONF']['IFDB_USER']
IFDB_PW = config['INFLUXDBCONF']['IFDB_PW']
IFDB_DB = config['INFLUXDBCONF']['IFDB_DB']

SENSOR_A_PIN = int(config['GPIOPIR']['SENSOR_A_PIN'])
SENSOR_B_PIN = int(config['GPIOPIR']['SENSOR_B_PIN'])

CLEARONSTART = config['DAEMON']['CLEARONSTART'].lower()
BOUNCETIME = float(config['DAEMON']['BOUNCETIME'].lower())
LOGFILE = config['DAEMON']['LOGFILE']
VERBOSE = config['DAEMON']['VERBOSE'].lower()

if LOGFILE:
    LOG = open(LOGFILE, 'a+')

# Initiate the InfluxDB client ------------------------------------------------
ifdbc = InfluxDBClient(host=IFDB_IP,
                       port=IFDB_PORT,
                       username=IFDB_USER,
                       password=IFDB_PW,
                       database=IFDB_DB)



MEASUREMENT = []
CUMULATIVE = 0
TS_A = 0
TS_B = 0
SLEEP_A = 0
SLEEP_B = 0
WAITFOREVAL = time.time()

now = time.time()

SENSORS = {SENSOR_A_PIN: [True, now, 0], SENSOR_B_PIN: [True, now, 0]}

def getcurrentpresence():
    # Get the latest number of people in the room (in case of e.g. restart)
    query='select "Presence" from "People" where ("MotionSensor"=\'Eingang\') order by time desc limit 1'
    ITEM = None

    try:
        q = ifdbc.query(query)
        # Get the last item of the iterator...
        ITEMS = q.get_points()
        for ITEM in ITEMS:
            pass
        PRESENCE = int(ITEM['Presence'])
    except Exception:
        myprint(f'Error')
        PRESENCE = 0
    return PRESENCE

def myprint(message):
    if VERBOSE == "true":
        print(message)
    if LOGFILE:
        LOG.write(f'{message}\n')
        LOG.flush()

def terminateProcess(signalNumber, frame):
    myprint(f'Terminating the process because we received signal {signalNumber}')
    pi.stop()
    if LOGFILE:
        LOG.close()
    sys.exit()

def timestamp():
   now = time.time()
   tsleep = now + BOUNCETIME
   localtime = time.localtime(now)
   milliseconds = '%03d' % int((now - int(now)) * 1000)
   ts = int(time.strftime('%Y%m%d%H%M%S', localtime) + milliseconds)
   return ts, now

def updateifdb(count):
    PRESENCE = getcurrentpresence()
    
    if count > 0:
        PRESENCE += 1
        myprint(f"In room: {PRESENCE}")
        MEASUREMENT = [
            {
                'measurement': 'People',
                'tags': {
                    'MotionSensor': "Eingang",
                },
                'fields': {
                    'Presence': int(PRESENCE),
                    'Cumulative': 1
                },
            }
        ]
        ifdbc.write_points(MEASUREMENT)
    
    if count < 0 and PRESENCE > 0:
        PRESENCE -= 1
        myprint(f"In room: {PRESENCE}")
        MEASUREMENT = [
            {
                'measurement': 'People',
                'tags': {
                    'MotionSensor': "Eingang",
                },
                'fields': {
                    'Presence': int(PRESENCE),
                },
            }
        ]
        ifdbc.write_points(MEASUREMENT)

def reset_peoplecount():
    MEASUREMENT = [
        {
            'measurement': 'People',
            'tags': {
                'MotionSensor': "Eingang",
            },
            'fields': {
                'Presence': 0,
            },
        }
    ]
    ifdbc.write_points(MEASUREMENT)

def evaluate(PIN):
    GlobList = globals()
    PINA = GlobList['SENSOR_A_PIN']
    PINB = GlobList['SENSOR_B_PIN']
    TSA = GlobList['SENSORS'][PINA][2]
    TSB = GlobList['SENSORS'][PINB][2]
    SLA = GlobList['SENSORS'][PINA][1]
    SLB = GlobList['SENSORS'][PINB][1]

    if TSA < TSB and TSA != 0 and TSB != 0:
        DELTA = SLB - SLA
        if DELTA <= BOUNCETIME:
            myprint(f"Timestamp: A({SENSOR_A_PIN}) {TSA} < {TSB} B({SENSOR_B_PIN}) | delta = {DELTA}")
            updateifdb(1)
        else:
            myprint(f"Timedelta A({SENSOR_A_PIN}) < B({SENSOR_B_PIN}) larger than {BOUNCETIME}: {DELTA}")
        GlobList['SENSORS'][PINA][2] = 0
        GlobList['SENSORS'][PINB][2] = 0


    if TSA > TSB and TSA != 0 and TSB != 0:
        DELTA = SLA - SLB
        if DELTA <= BOUNCETIME:
            myprint(f"Timestamp: A({SENSOR_A_PIN}) {TSA} > {TSB} B({SENSOR_B_PIN}) | delta = {DELTA}")
            updateifdb(-1)
        else:
            myprint(f"Timedelta A({SENSOR_A_PIN}) > B({SENSOR_B_PIN}) larger than {BOUNCETIME}: {DELTA}")
        GlobList['SENSORS'][PINA][2] = 0
        GlobList['SENSORS'][PINB][2] = 0    

def motion(SENSOR_PIN, level, tick):
    GlobList = globals()
    TS, NOW = timestamp()
    if GlobList['SENSORS'][SENSOR_PIN][0] or GlobList['SENSORS'][SENSOR_PIN][1] < NOW:
        myprint(f'Motion on {SENSOR_PIN}')
        GlobList['SENSORS'][SENSOR_PIN] = [False, NOW + BOUNCETIME, TS]
        evaluate(SENSOR_PIN)

def alignment_check(a, b):
    myprint(f'Laser_A_status: {a} | Laser_B_status {b}')
    MEASUREMENT = [
        {
            'measurement': 'People',
            'tags': {
                'MotionSensor': "Eingang",
            },
            'fields': {
                'Laser_A_status': int(a),
                'Laser_B_status': int(b)
            },
        }
    ]
    ifdbc.write_points(MEASUREMENT)

if __name__ == '__main__':
    pi = pigpio.pi()
    myprint(f'Pi hardware revision: {pi.get_hardware_revision()}')
    pi.set_mode(SENSOR_A_PIN, pigpio.INPUT)
    pi.set_mode(SENSOR_B_PIN, pigpio.INPUT)

    signal.signal(signal.SIGINT, terminateProcess)
    signal.signal(signal.SIGTERM, terminateProcess)

    schedule.every().day.at("00:00").do(reset_peoplecount)

    if CLEARONSTART == "true":
        myprint("Seting presence to 0")
        reset_peoplecount()

    PRESENCE = getcurrentpresence()
    
    myprint(f'People in room at start: {PRESENCE}')

    cba = pi.callback(SENSOR_A_PIN, pigpio.RISING_EDGE, motion)
    cbb = pi.callback(SENSOR_B_PIN, pigpio.RISING_EDGE, motion)

    while True:
        status_a = pi.read(SENSOR_A_PIN)
        status_b = pi.read(SENSOR_B_PIN)
        alignment_check(status_a, status_b)
        schedule.run_pending()
        time.sleep(60)
