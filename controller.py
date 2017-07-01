import platform
import os
import uuid
import urllib.request, urllib.error, urllib.parse
import json
import traceback
import tempfile
import asyncio
import websockets
import jsonpickle

import argparse
parser = argparse.ArgumentParser(description='start robot control program')
parser.add_argument('robot_id', help='Robot ID')
parser.add_argument('--env', help="Environment for example dev or prod, prod is default", default='prod')
parser.add_argument('--type', help="serial or motor_hat or gopigo or l298n or motozero", default='motor_hat')
parser.add_argument('--serial-device', help="serial device", default='/dev/ttyACM0')
parser.add_argument('--male', dest='male', action='store_true')
parser.add_argument('--female', dest='male', action='store_false')
parser.add_argument('--voice-number', type=int, default=1)
parser.add_argument('--led', help="Type of LED for example max7219", default=None)
parser.add_argument('--ledrotate', help="Rotates the LED matrix. Example: 180", default=None)
parser.add_argument('--tts-volume', type=int, default=80)
parser.add_argument('--secret-key', default=None)
parser.add_argument('--turn-delay', type=float, default=0.4)
parser.add_argument('--straight-delay', type=float, default=0.5)
parser.add_argument('--driving-speed', type=int, default=90)
parser.add_argument('--night-speed', type=int, default=170)
parser.add_argument('--forward', default='[-1,1,-1,1]')
parser.add_argument('--left', default='[1,1,1,1]')
parser.add_argument('--festival-tts', dest='festival_tts', action='store_true')
parser.set_defaults(festival_tts=False)
parser.add_argument('--auto-wifi', dest='auto_wifi', action='store_true')
parser.set_defaults(auto_wifi=False)

commandArgs = parser.parse_args()
print(commandArgs)

# watch dog timer
#os.system("sudo modprobe bcm2835_wdt")
os.system("sudo /usr/sbin/service watchdog start")


# set volume level

# tested for 3.5mm audio jack
#if commandArgs.tts_volume > 50:
#    os.system("amixer set PCM -- -100")

# tested for USB audio device
#os.system("amixer -c 2 cset numid=3 %d%%" % commandArgs.tts_volume)

server = "univac.ngrok.io"
#server = "localhost:4000"
#server = "runmyrobot.com"
#server = "52.52.213.92"

tempDir = tempfile.gettempdir()
print(("temporary directory:", tempDir))


# motor controller specific imports
if commandArgs.type == 'none':
    pass
elif commandArgs.type == 'serial':
    import serial
elif commandArgs.type == 'motor_hat':
    pass
elif commandArgs.type == 'gopigo':
    import gopigo
elif commandArgs.type == 'l298n':
    pass
elif commandArgs.type == 'motozero':
    pass
elif commandArgs.type == 'screencap':
    pass
elif commandArgs.type == 'adafruit_pwm':
    from Adafruit_PWM_Servo_Driver import PWM
elif commandArgs.led == 'max7219':
    import spidev
else:
    print("invalid --type in command line")
    exit(0)

#serialDevice = '/dev/tty.usbmodem12341'
#serialDevice = '/dev/ttyUSB0'

serialDevice = commandArgs.serial_device



if commandArgs.type == 'motor_hat':
    try:
        from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor
        motorsEnabled = True
    except ImportError:
        print("You need to install Adafruit_MotorHAT")
        print("Please install Adafruit_MotorHAT for python and restart this script.")
        print("To install: cd /usr/local/src && sudo git clone https://github.com/adafruit/Adafruit-Motor-HAT-Python-Library.git")
        print("cd /usr/local/src/Adafruit-Motor-HAT-Python-Library && sudo python setup.py install")
        print("Running in test mode.")
        print("Ctrl-C to quit")
        motorsEnabled = False

# todo: specificity is not correct, this is specific to a bot with a claw, not all motor_hat based bots
if commandArgs.type == 'motor_hat':
    from Adafruit_PWM_Servo_Driver import PWM

import time
import atexit
import sys
import _thread
import subprocess
if (commandArgs.type == 'motor_hat') or (commandArgs.type == 'l298n') or (commandArgs.type == 'motozero'):
    import RPi.GPIO as GPIO
import datetime
from socketIO_client import SocketIO, LoggingNamespace


chargeIONumber = 17
robotID = commandArgs.robot_id

if commandArgs.type == 'motor_hat':
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(chargeIONumber, GPIO.IN)
if commandArgs.type == 'l298n':
    mode=GPIO.getmode()
    print(" mode ="+str(mode))
    GPIO.cleanup()
    #Change the GPIO Pins to your connected motors
    #visit http://bit.ly/1S5nQ4y for reference
    if robotID == "20134182": # StanleyBot
        StepPinForward=12,16
        StepPinBackward=11,15
        StepPinLeft=15,12
        StepPinRight=11,16
    elif robotID == "53326365": # StaceyBot
        StepPinForward=11,15
        StepPinBackward=12,16
        StepPinLeft=11,16
        StepPinRight=15,12
    else: # default settings
        StepPinForward=12,16
        StepPinBackward=11,15
        StepPinLeft=15,12
        StepPinRight=11,16
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(StepPinForward, GPIO.OUT)
    GPIO.setup(StepPinBackward, GPIO.OUT)
    GPIO.setup(StepPinLeft, GPIO.OUT)
    GPIO.setup(StepPinRight, GPIO.OUT)
if commandArgs.type == 'motozero':
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)

    # Motor1 is back left
    # Motor1A is reverse
    # Motor1B is forward
    Motor1A = 24
    Motor1B = 27
    Motor1Enable = 5

    # Motor2 is back right
    # Motor2A is reverse
    # Motor2B is forward
    Motor2A = 6
    Motor2B = 22
    Motor2Enable = 17

    # Motor3 is ?
    # Motor3A is reverse
    # Motor3B is forward
    Motor3A = 23
    Motor3B = 16
    Motor3Enable = 12

    # Motor4 is ?
    # Motor4A is reverse
    # Motor4B is forward
    Motor4A = 13
    Motor4B = 18
    Motor4Enable = 25

    GPIO.setup(Motor1A,GPIO.OUT)
    GPIO.setup(Motor1B,GPIO.OUT)
    GPIO.setup(Motor1Enable,GPIO.OUT)

    GPIO.setup(Motor2A,GPIO.OUT)
    GPIO.setup(Motor2B,GPIO.OUT)
    GPIO.setup(Motor2Enable,GPIO.OUT)

    GPIO.setup(Motor3A,GPIO.OUT)
    GPIO.setup(Motor3B,GPIO.OUT)
    GPIO.setup(Motor3Enable,GPIO.OUT)

    GPIO.setup(Motor4A,GPIO.OUT)
    GPIO.setup(Motor4B,GPIO.OUT)
    GPIO.setup(Motor4Enable,GPIO.OUT)

#LED controlling
if commandArgs.led == 'max7219':
    spi = spidev.SpiDev()
    spi.open(0,0)
    #VCC -> RPi Pin 2
    #GND -> RPi Pin 6
    #DIN -> RPi Pin 19
    #CLK -> RPi Pin 23
    #CS -> RPi Pin 24

    # decoding:BCD
    spi.writebytes([0x09])
    spi.writebytes([0x00])
    # Start with low brightness
    spi.writebytes([0x0a])
    spi.writebytes([0x03])
    # scanlimit; 8 LEDs
    spi.writebytes([0x0b])
    spi.writebytes([0x07])
    # Enter normal power-mode
    spi.writebytes([0x0c])
    spi.writebytes([0x01])
    # Activate display
    spi.writebytes([0x0f])
    spi.writebytes([0x00])
    columns = [0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8]
    LEDOn = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
    LEDOff = [0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0]
    LEDEmoteSmile = [0x0,0x0,0x24,0x0,0x42,0x3C,0x0,0x0]
    LEDEmoteSad = [0x0,0x0,0x24,0x0,0x0,0x3C,0x42,0x0]
    LEDEmoteTongue = [0x0,0x0,0x24,0x0,0x42,0x3C,0xC,0x0]
    LEDEmoteSuprise = [0x0,0x0,0x24,0x0,0x18,0x24,0x24,0x18]
    if commandArgs.ledrotate == '180':
        LEDEmoteSmile = LEDEmoteSmile[::-1]
        LEDEmoteSad = LEDEmoteSad[::-1]
        LEDEmoteTongue = LEDEmoteTongue[::-1]
        LEDEmoteSuprise = LEDEmoteSuprise[::-1]

def SetLED_On():
  if commandArgs.led == 'max7219':
    for i in range(len(columns)):
        spi.xfer([columns[i],LEDOn[i]])
def SetLED_Off():
  if commandArgs.led == 'max7219':
    for i in range(len(columns)):
        spi.xfer([columns[i],LEDOff[i]])
def SetLED_E_Smiley():
  if commandArgs.led == 'max7219':
    for i in range(len(columns)):
        spi.xfer([columns[i],LEDEmoteSmile[i]])
def SetLED_E_Sad():
  if commandArgs.led == 'max7219':
    for i in range(len(columns)):
        spi.xfer([columns[i],LEDEmoteSad[i]])
def SetLED_E_Tongue():
  if commandArgs.led == 'max7219':
    for i in range(len(columns)):
        spi.xfer([columns[i],LEDEmoteTongue[i]])
def SetLED_E_Suprised():
  if commandArgs.led == 'max7219':
    for i in range(len(columns)):
        spi.xfer([columns[i],LEDEmoteSuprise[i]])
def SetLED_Low():
  if commandArgs.led == 'max7219':
    # brightness MIN
    spi.writebytes([0x0a])
    spi.writebytes([0x00])
def SetLED_Med():
  if commandArgs.led == 'max7219':
    #brightness MED
    spi.writebytes([0x0a])
    spi.writebytes([0x06])
def SetLED_Full():
  if commandArgs.led == 'max7219':
    # brightness MAX
    spi.writebytes([0x0a])
    spi.writebytes([0x0F])

SetLED_Off()

steeringSpeed = 90
steeringHoldingSpeed = 90

global drivingSpeed


#drivingSpeed = 90
drivingSpeed = commandArgs.driving_speed
handlingCommand = False


# Marvin
turningSpeedActuallyUsed = 250
dayTimeDrivingSpeedActuallyUsed = 250
nightTimeDrivingSpeedActuallyUsed = commandArgs.night_speed

# Initialise the PWM device
if commandArgs.type == 'motor_hat':
    pwm = PWM(0x42)
elif commandArgs.type == 'adafruit_pwm':
    pwm = PWM(0x40)

# Note if you'd like more debug output you can instead run:
#pwm = PWM(0x40, debug=True)
servoMin = [150, 150, 130]  # Min pulse length out of 4096
servoMax = [600, 600, 270]  # Max pulse length out of 4096
armServo = [300, 300, 300]

#def setMotorsToIdle():
#    s = 65
#    for i in range(1, 2):
#        mh.getMotor(i).setSpeed(s)
#        mh.getMotor(i).run(Adafruit_MotorHAT.FORWARD)







if commandArgs.env == 'dev':
    print('DEV MODE ***************')
    print("using dev port 8122")
    port = 8122
elif commandArgs.env == 'prod':
    print('PROD MODE *************')
    print("using prod port 8022")
    port = 8022
else:
    print("invalid environment")
    sys.exit(0)


if commandArgs.type == 'serial':
    # initialize serial connection
    serialBaud = 9600
    print("baud:", serialBaud)
    #ser = serial.Serial('/dev/tty.usbmodem12341', 19200, timeout=1)  # open serial
    ser = serial.Serial(serialDevice, serialBaud, timeout=1)  # open serial

from websocket import create_connection
# ws = create_connection("ws://10.180.0.105:4000/socket/websocket")

channel = "robots:%s" % robotID
print("channel: %s" % channel)
ws = create_connection("ws://univac.ngrok.io/socket/websocket")

def ws_send(event, payload):
    print("sending")
    data = dict(topic=channel, event=event, payload=payload, ref=None)
    arez = ws.send(jsonpickle.encode(data))

data = dict(topic=channel, event="phx_join", payload={}, ref=None)

print("Sending 'Hello, World'...")
rez = ws_send("phx_join", dict(topic=channel, event="phx_join", payload={}, ref=None))
arez = ws.send(jsonpickle.encode(data))
print("Sent")
print("Receiving...")
result =  ws.recv()
print("Received '%s'" % result)
# ws.close()

print('finished using socket io to connect to', server)
print(rez)


def setServoPulse(channel, pulse):
  pulseLength = 1000000                   # 1,000,000 us per second
  pulseLength /= 60                       # 60 Hz
  print("%d us per period" % pulseLength)
  pulseLength /= 4096                     # 12 bits of resolution
  print("%d us per bit" % pulseLength)
  pulse *= 1000
  pulse /= pulseLength
  pwm.setPWM(channel, 0, pulse)


if commandArgs.type == 'motor_hat' or commandArgs.type == 'adafruit_pwm':
    pwm.setPWMFreq(60)                        # Set frequency to 60 Hz


WPA_FILE_TEMPLATE = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=GB

network={{
            ssid=\"beepx\"
            psk=\"yellow123\"
            key_mgmt=WPA-PSK
    }}

network={{
            ssid=\"{name}\"
            psk=\"{password}\"
            key_mgmt=WPA-PSK
    }}
"""


def isInternetConnected():
    try:
        urllib.request.urlopen('http://216.58.192.142', timeout=1)
        return True
    except urllib.error.URLError as err:
        return False


def configWifiLogin(secretKey):

    url = 'https://%s/get_wifi_login/%s' % (server, secretKey)
    try:
        print("GET", url)
        response = urllib.request.urlopen(url).read()
        responseJson = json.loads(response)
        print("get wifi login response:", response)
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", 'r') as originalWPAFile:
            originalWPAText = originalWPAFile.read()

        wpaText = WPA_FILE_TEMPLATE.format(name=responseJson['wifi_name'], password=responseJson['wifi_password'])


        print("original(" + originalWPAText + ")")
        print("new(" + wpaText + ")")

        if originalWPAText != wpaText:

            wpaFile = open("/etc/wpa_supplicant/wpa_supplicant.conf", 'w')

            print(wpaText)
            print()
            wpaFile.write(wpaText)
            wpaFile.close()

            say("Updated wifi settings. I will automatically reset in 10 seconds.")
            time.sleep(8)
            say("Reseting")
            time.sleep(2)
            os.system("reboot")


    except:
        print("exception while configuring setting wifi", url)
        traceback.print_exc()



def sendSerialCommand(command):


    print((ser.name))         # check which port was really used
    ser.nonblocking()

    # loop to collect input
    #s = "f"
    #print "string:", s
    print(str(command.lower()))
    ser.write(command.lower() + "\r\n")     # write a string
    #ser.write(s)
    ser.flush()

    #while ser.in_waiting > 0:
    #    print "read:", ser.read()

    #ser.close()





def incrementArmServo(channel, amount):

    armServo[channel] += amount

    print("arm servo positions:", armServo)

    if armServo[channel] > servoMax[channel]:
        armServo[channel] = servoMax[channel]
    if armServo[channel] < servoMin[channel]:
        armServo[channel] = servoMin[channel]
    pwm.setPWM(channel, 0, armServo[channel])



def times(lst, number):
    return [x*number for x in lst]



def runMotor(motorIndex, direction):
    motor = mh.getMotor(motorIndex+1)
    if direction == 1:
        motor.setSpeed(drivingSpeed)
        motor.run(Adafruit_MotorHAT.FORWARD)
    if direction == -1:
        motor.setSpeed(drivingSpeed)
        motor.run(Adafruit_MotorHAT.BACKWARD)
    if direction == 0.5:
        motor.setSpeed(128)
        motor.run(Adafruit_MotorHAT.FORWARD)
    if direction == -0.5:
        motor.setSpeed(128)
        motor.run(Adafruit_MotorHAT.BACKWARD)


forward = json.loads(commandArgs.forward)
backward = times(forward, -1)
left = json.loads(commandArgs.left)
right = times(left, -1)
straightDelay = commandArgs.straight_delay
turnDelay = commandArgs.turn_delay
#Change sleeptime to adjust driving speed
#Change rotatetimes to adjust the rotation. Will be multiplicated with sleeptime.
l298n_sleeptime=0.2
l298n_rotatetimes=5


def handle_exclusive_control(args):
        if 'status' in args and 'robot_id' in args and args['robot_id'] == robotID:

            status = args['status']

        if status == 'start':
                print("start exclusive control")
        if status == 'end':
                print("end exclusive control")



def say(message):

    tempFilePath = os.path.join(tempDir, "text_" + str(uuid.uuid4()))
    f = open(tempFilePath, "w")
    f.write(message)
    f.close()


    #os.system('"C:\Program Files\Jampal\ptts.vbs" -u ' + tempFilePath)

    if commandArgs.festival_tts:
        # festival tts
        os.system('festival --tts < ' + tempFilePath)
    #os.system('espeak < /tmp/speech.txt')

    else:
        # espeak tts
        print("espeak")
        # for hardwareNumber in (2, 0, 1):
        #     if commandArgs.male:
        #         os.system('cat ' + tempFilePath + ' | espeak --stdout | aplay -D plughw:%d,0' % hardwareNumber)
        #     else:
        #         os.system('cat ' + tempFilePath + ' | espeak -ven-us+f%d -s170 --stdout | aplay -D plughw:%d,0' % (commandArgs.voice_number, hardwareNumber))

    os.remove(tempFilePath)



def handle_chat_message(args):

    print("chat message received:", args)
    rawMessage = args['message']
    withoutName = rawMessage.split(']')[1:]
    message = "".join(withoutName)
    say(message)


def moveAdafruitPWM(command):
    print("move adafruit pwm command", command)
    if command == 'L':
        pwm.setPWM(1, 0, 500)

        pwm.setPWM(0, 0, 445)

        time.sleep(0.5)
        pwm.setPWM(1, 0, 400)

        pwm.setPWM(0, 0, 335)


    if command == 'R':
        pwm.setPWM(1, 0, 300)

        pwm.setPWM(0, 0, 445)

        time.sleep(0.5)
        pwm.setPWM(1, 0, 400)

        pwm.setPWM(0, 0, 335)

    if command == 'F':
        pwm.setPWM(0, 0, 445)
        time.sleep(0.5)
        pwm.setPWM(0, 0, 335)
    if command == 'B':
        pwm.setPWM(0, 0, 200)
        time.sleep(0.5)
        pwm.setPWM(0, 0, 335)


def moveGoPiGo(command):
    if command == 'L':
        gopigo.left_rot()
        time.sleep(0.15)
        gopigo.stop()
    if command == 'R':
        gopigo.right_rot()
        time.sleep(0.15)
        gopigo.stop()
    if command == 'F':
        gopigo.forward()
        time.sleep(0.35)
        gopigo.stop()
    if command == 'B':
        gopigo.backward()
        time.sleep(0.35)
        gopigo.stop()



def handle_command(args):
        now = datetime.datetime.now()
        now_time = now.time()
        # if it's late, make the robot slower
        if now_time >= datetime.time(21,30) or now_time <= datetime.time(9,30):
            #print "within the late time interval"
            drivingSpeedActuallyUsed = nightTimeDrivingSpeedActuallyUsed
        else:
            drivingSpeedActuallyUsed = dayTimeDrivingSpeedActuallyUsed

        global drivingSpeed
        global handlingCommand

        #print "received command:", args
        # Note: If you are adding features to your bot,
        # you can get direct access to incomming commands right here.


        if handlingCommand:
            return

        handlingCommand = True

        #if 'robot_id' in args:
        #    print "args robot id:", args['robot_id']

        #if 'command' in args:
        #    print "args command:", args['command']



        if 'command' in args and 'robot_id' in args and args['robot_id'] == robotID:

            print(('got command', args))

            command = args['command']

            if commandArgs.type == 'adafruit_pwm':
                moveAdafruitPWM(command)

            if commandArgs.type == 'gopigo':
                moveGoPiGo(command)

            if commandArgs.type == 'serial':
                sendSerialCommand(command)

            if commandArgs.type == 'motor_hat' and motorsEnabled:
                motorA.setSpeed(drivingSpeed)
                motorB.setSpeed(drivingSpeed)
                if command == 'F':
                    drivingSpeed = drivingSpeedActuallyUsed
                    for motorIndex in range(4):
                        runMotor(motorIndex, forward[motorIndex])
                    time.sleep(straightDelay)
                if command == 'B':
                    drivingSpeed = drivingSpeedActuallyUsed
                    for motorIndex in range(4):
                        runMotor(motorIndex, backward[motorIndex])
                    time.sleep(straightDelay)
                if command == 'L':
                    drivingSpeed = turningSpeedActuallyUsed
                    for motorIndex in range(4):
                        runMotor(motorIndex, left[motorIndex])
                    time.sleep(turnDelay)
                if command == 'R':
                    drivingSpeed = turningSpeedActuallyUsed
                    for motorIndex in range(4):
                        runMotor(motorIndex, right[motorIndex])
                    time.sleep(turnDelay)
                if command == 'U':
                    #mhArm.getMotor(1).setSpeed(127)
                    #mhArm.getMotor(1).run(Adafruit_MotorHAT.BACKWARD)
                    incrementArmServo(1, 10)
                    time.sleep(0.05)
                if command == 'D':
                    #mhArm.getMotor(1).setSpeed(127)
                    #mhArm.getMotor(1).run(Adafruit_MotorHAT.FORWARD)
                    incrementArmServo(1, -10)
                    time.sleep(0.05)
                if command == 'O':
                    #mhArm.getMotor(2).setSpeed(127)
                    #mhArm.getMotor(2).run(Adafruit_MotorHAT.BACKWARD)
                    incrementArmServo(2, -10)
                    time.sleep(0.05)
                if command == 'C':
                    #mhArm.getMotor(2).setSpeed(127)
                    #mhArm.getMotor(2).run(Adafruit_MotorHAT.FORWARD)
                    incrementArmServo(2, 10)
                    time.sleep(0.05)

            if commandArgs.type == 'motor_hat':
                turnOffMotors()
            if commandArgs.type == 'l298n':
                runl298n(command)
                #setMotorsToIdle()
        if commandArgs.type == 'motozero':
            runmotozero(command)
            if commandArgs.led == 'max7219':
                if command == 'LED_OFF':
                    SetLED_Off()
                if command == 'LED_FULL':
                    SetLED_On()
                    SetLED_Full()
                if command == 'LED_MED':
                    SetLED_On()
                    SetLED_Med()
                if command == 'LED_LOW':
                    SetLED_On()
                    SetLED_Low()
                if command == 'LED_E_SMILEY':
                    SetLED_On()
                    SetLED_E_Smiley()
                if command == 'LED_E_SAD':
                    SetLED_On()
                    SetLED_E_Sad()
                if command == 'LED_E_TONGUE':
                    SetLED_On()
                    SetLED_E_Tongue()
                if command == 'LED_E_SUPRISED':
                    SetLED_On()
                    SetLED_E_Suprised()
        handlingCommand = False

def runl298n(direction):
    if direction == 'F':
        GPIO.output(StepPinForward, GPIO.HIGH)
        time.sleep(l298n_sleeptime * l298n_rotatetimes)
        GPIO.output(StepPinForward, GPIO.LOW)
    if direction == 'B':
        GPIO.output(StepPinBackward, GPIO.HIGH)
        time.sleep(l298n_sleeptime * l298n_rotatetimes)
        GPIO.output(StepPinBackward, GPIO.LOW)
    if direction == 'L':
        GPIO.output(StepPinLeft, GPIO.HIGH)
        time.sleep(l298n_sleeptime)
        GPIO.output(StepPinLeft, GPIO.LOW)
    if direction == 'R':
        GPIO.output(StepPinRight, GPIO.HIGH)
        time.sleep(l298n_sleeptime)
        GPIO.output(StepPinRight, GPIO.LOW)

def runmotozero(direction):
    if direction == 'F':
        GPIO.output(Motor1B, GPIO.HIGH)
        GPIO.output(Motor1Enable,GPIO.HIGH)

        GPIO.output(Motor2B, GPIO.HIGH)
        GPIO.output(Motor2Enable, GPIO.HIGH)

        GPIO.output(Motor3A, GPIO.HIGH)
        GPIO.output(Motor3Enable, GPIO.HIGH)

        GPIO.output(Motor4B, GPIO.HIGH)
        GPIO.output(Motor4Enable, GPIO.HIGH)

        time.sleep(0.3)

        GPIO.output(Motor1B, GPIO.LOW)
        GPIO.output(Motor2B, GPIO.LOW)
        GPIO.output(Motor3A, GPIO.LOW)
        GPIO.output(Motor4B, GPIO.LOW)
    if direction == 'B':
        GPIO.output(Motor1A, GPIO.HIGH)
        GPIO.output(Motor1Enable, GPIO.HIGH)

        GPIO.output(Motor2A, GPIO.HIGH)
        GPIO.output(Motor2Enable, GPIO.HIGH)

        GPIO.output(Motor3B, GPIO.HIGH)
        GPIO.output(Motor3Enable, GPIO.HIGH)

        GPIO.output(Motor4A, GPIO.HIGH)
        GPIO.output(Motor4Enable, GPIO.HIGH)

        time.sleep(0.3)

        GPIO.output(Motor1A, GPIO.LOW)
        GPIO.output(Motor2A, GPIO.LOW)
        GPIO.output(Motor3B, GPIO.LOW)
        GPIO.output(Motor4A, GPIO.LOW)

    if direction =='L':
        GPIO.output(Motor3B, GPIO.HIGH)
        GPIO.output(Motor3Enable, GPIO.HIGH)

        GPIO.output(Motor1A, GPIO.HIGH)
        GPIO.output(Motor1Enable, GPIO.HIGH)

        GPIO.output(Motor2B, GPIO.HIGH)
        GPIO.output(Motor2Enable, GPIO.HIGH)

        GPIO.output(Motor4B, GPIO.HIGH)
        GPIO.output(Motor4Enable, GPIO.HIGH)

        time.sleep(0.3)

        GPIO.output(Motor3B, GPIO.LOW)
        GPIO.output(Motor1A, GPIO.LOW)
        GPIO.output(Motor2B, GPIO.LOW)
        GPIO.output(Motor4B, GPIO.LOW)

    if direction == 'R':
        GPIO.output(Motor3A, GPIO.HIGH)
        GPIO.output(Motor3Enable, GPIO.HIGH)

        GPIO.output(Motor1B, GPIO.HIGH)
        GPIO.output(Motor1Enable, GPIO.HIGH)

        GPIO.output(Motor2A, GPIO.HIGH)
        GPIO.output(Motor2Enable, GPIO.HIGH)

        GPIO.output(Motor4A, GPIO.HIGH)
        GPIO.output(Motor4Enable, GPIO.HIGH)

        time.sleep(0.3)

        GPIO.output(Motor3A, GPIO.LOW)
        GPIO.output(Motor1B, GPIO.LOW)
        GPIO.output(Motor2A, GPIO.LOW)
        GPIO.output(Motor4A, GPIO.LOW)

def handleStartReverseSshProcess(args):
    print("starting reverse ssh")
    ws_send("reverse_ssh_info", "starting")
    returnCode = subprocess.call(["/usr/bin/ssh", "-X", "-i", "/home/pi/reverse_ssh_key1.pem", "-N", "-R", "2222:localhost:22", "ubuntu@52.52.204.174"])
    ws_send("reverse_ssh_info", "return code: " + str(returnCode))
    print("reverse ssh process has exited with code", str(returnCode))


def handleEndReverseSshProcess(args):
    print("handling end reverse ssh process")
    resultCode = subprocess.call(["killall", "ssh"])
    print("result code of killall ssh:", resultCode)

def on_handle_command(*args):
   _thread.start_new_thread(handle_command, args)

def on_handle_exclusive_control(*args):
   _thread.start_new_thread(handle_exclusive_control, args)

def on_handle_chat_message(*args):
   _thread.start_new_thread(handle_chat_message, args)

def startReverseSshProcess(*args):
   _thread.start_new_thread(handleStartReverseSshProcess, args)

def endReverseSshProcess(*args):
   _thread.start_new_thread(handleEndReverseSshProcess, args)

# I have sent values from 2 buttons for swicthing a led with event 'control'

def myWait():
  # socketIO.wait()
  _thread.start_new_thread(myWait, ())


if commandArgs.type == 'motor_hat':
    if motorsEnabled:
        # create a default object, no changes to I2C address or frequency
        mh = Adafruit_MotorHAT(addr=0x60)
        #mhArm = Adafruit_MotorHAT(addr=0x61)


def turnOffMotors():
    mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
    mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)
    #mhArm.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
    #mhArm.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
    #mhArm.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
    #mhArm.getMotor(4).run(Adafruit_MotorHAT.RELEASE)


if commandArgs.type == 'motor_hat':
    if motorsEnabled:
        atexit.register(turnOffMotors)
        motorA = mh.getMotor(1)
        motorB = mh.getMotor(2)

def ipInfoUpdate():
    ws_send('ip_information',
                  {'ip': subprocess.check_output(["hostname", "-I"]), 'robot_id': robotID})

def sendChargeState():
    charging = GPIO.input(chargeIONumber) == 1
    chargeState = {'robot_id': robotID, 'charging': charging}
    ws_send('charge_state', chargeState)
    print("charge state:", chargeState)

def sendChargeStateCallback(x):
    sendChargeState()

if commandArgs.type == 'motor_hat':
    GPIO.add_event_detect(chargeIONumber, GPIO.BOTH)
    GPIO.add_event_callback(chargeIONumber, sendChargeStateCallback)


def identifyRobotId():
    ws_send('identify_robot_id', robotID);



#setMotorsToIdle()





waitCounter = 0


identifyRobotId()



if platform.system() == 'Darwin':
    pass
    #ipInfoUpdate()
elif platform.system() == 'Linux':
    ipInfoUpdate()


lastInternetStatus = False


def on_server_recv(cmd):
    payload = cmd["payload"]
    print(payload)
    if 'command' in payload:
        print("[on_server_recv] passing in command '%s'" % payload["command"])
        handle_command(dict(command = payload["command"], robot_id = robotID))
    else:
      print("no command to handle")

    #from communication import socketIO
    # socketIO.on('command_to_robot', on_handle_command)
    # socketIO.on('exclusive_control', on_handle_exclusive_control)
    # socketIO.on('chat_message_with_name', on_handle_chat_message)
    # socketIO.on('reverse_ssh_8872381747239', startReverseSshProcess)
    # socketIO.on('end_reverse_ssh_8872381747239', endReverseSshProcess)


def receive_commands():
    print("waiting for commands1")
    while True:
        print("waiting for commands2")
        msg = ws.recv() # waits for anything from the phoenix server
        print("got message from server")
        cmd = json.loads(msg)
        print(cmd)
        on_server_recv(cmd)

_thread.start_new_thread(receive_commands, ())

while True:
    # socketIO.wait(seconds=1)

    internetStatus = isInternetConnected()
    if internetStatus != lastInternetStatus:
        if internetStatus:
            say("ok")
        else:
            say("missing internet connection")
    lastInternetStatus = internetStatus

    if commandArgs.auto_wifi:
        if commandArgs.secret_key is not None:
            configWifiLogin(commandArgs.secret_key)

    if (waitCounter % 60) == 0:

        # tell the server what robot id is using this connection
        identifyRobotId()

        if platform.system() == 'Linux':
            ipInfoUpdate()

        if commandArgs.type == 'motor_hat':
            sendChargeState()

    waitCounter += 1
