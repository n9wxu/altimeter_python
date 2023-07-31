import board
import time
from digitalio import DigitalInOut, Direction, Pull
import analogio
import busio
import storage
import adafruit_bmp280
import supervisor
import microcontroller
import os
import gc

# define the Hardware for the board
sda1_pin = board.GP18
scl1_pin = board.GP19
sda0_pin = board.GP20
scl0_pin = board.GP21

sense1_pin = board.A0
sense2_pin = board.A1
pixel_pin = board.GP1
fire1_pin = board.GP9
fire2_pin = board.GP11
pyro_low_pin = board.GP10
led_pin = board.GP25

tx_pin = board.GP0
rx_pin = board.GP1

# configure the system
flying = False

sense1 = analogio.AnalogIn(sense1_pin)
sense2 = analogio.AnalogIn(sense2_pin)

pyro_low = DigitalInOut(pyro_low_pin)
pyro_low.switch_to_output(value=False)

fire1 = DigitalInOut(fire1_pin)
fire1.switch_to_output(value=False)

fire2 = DigitalInOut(fire2_pin)
fire2.switch_to_output(value=False)

i2c = busio.I2C(scl0_pin, sda0_pin)
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, 0x77)

bmp280.sea_level_pressure = 1013.25
bmp280.mode = adafruit_bmp280.MODE_NORMAL
bmp280.standby_period = adafruit_bmp280.STANDBY_TC_500
bmp280.iir_filter = adafruit_bmp280.IIR_FILTER_X16
bmp280.overscan_pressure = adafruit_bmp280.OVERSCAN_X16
bmp280.overscan_temperature = adafruit_bmp280.OVERSCAN_X2

filename = "data.csv"

# Setup LED
led_pin = board.GP25
led = DigitalInOut(led_pin)
led.switch_to_output()


# accepts hecaPascals and returns feet
def makeAltitude(p) -> float:
    # use the sea level and 15C to compute the current altitude
    seaLevelPressure = 1013.25
    temperature = 15.0 + 273.15
    altitude = ((((seaLevelPressure / p) ** (1 / 5.257)) - 1) * temperature) / 0.0065
    return altitude * 3.28084


# simple function to test if a file is present
def exists(f):
    os.sync()
    if f in os.listdir("/"):
        print("found " + f)
        return True
    else:
        return False


if exists(filename):
    print("Standing by for file transfer. To fly and log, remove USB cable.")
    while True:
        led.value = True
        time.sleep(0.1)
        led.value = False
        time.sleep(0.1)

loopTime = 0

led.value = True  # turn on LED solid for the durration of the logging

gc.collect()  # garbage collect the memory

history = 20

ramLimit = False
flying = False
logging = True
launchTime = 0
launchAltitude = 0
peakAltitude = 0
apogee = False
# 200 data points to seed the pressure sum
mission_data = []
for i in range(0, history):
    mission_data.append(bmp280.pressure)
startTime = time.monotonic_ns()
armed = False
previousSample = 0
while logging:
    now = time.monotonic_ns()
    if now - previousSample > 50000000:
        previousSample = now

        try:
            mission_data.append(bmp280.pressure)
        except Exception as e:
            ramLimit = True
            logging = False

        avgAltitude = makeAltitude(sum(mission_data[-history:]) / history)
        altitude = makeAltitude(sum(mission_data[-3:]) / 3)
        if altitude > peakAltitude:
            peakAltitude = altitude

        if not flying:
            mission_data.pop(0)
            launchTime = (
                now  # keep updating the launchTime.  This will stop when we are saving.
            )
            # sit on the pad for 10 seconds
            if not armed:
                if (now - startTime) > 10000000000:
                    print("armed")
                    armed = True
            else:
                # launch detector
                if abs(altitude - avgAltitude) > 10:
                    launchTime = now
                    launchAltitude = altitude
                    print("Launch")
                    print("Altitude : " + str(altitude))
                    print("avgAltitude : " + str(avgAltitude))
                    print("Launch Time Set To: ", launchTime)
                    flying = True
        else:

            # apogee detector.  peak is 10 ft lower than average altitude
            if not apogee and peakAltitude - avgAltitude > 10:
                apogee = True
                peakAltitude = peakAltitude - launchAltitude

            # landing detector
            print(altitude, avgAltitude, abs(altitude - avgAltitude))
            if abs(altitude - avgAltitude) < 1.0:
                logging = False
            # maximum flight detector 10 minutes
            if now - launchTime > 600000000000:
                logging = False


flying = False
mission_time = (now - launchTime) / 1000000000
if len(mission_data):
    dT = mission_time / len(mission_data)
else:
    dT = 0.05

print(".")
print("landed")
print("Altitude : " + str(altitude))
print("avgAltitude : " + str(avgAltitude))
print("mission elapsed time : " + str(mission_time))
print("maximum Altitude : " + str(peakAltitude))
print("saving the data")
file = open(filename, "wt")
print("Log File Created")
file.write("mission time = " + str(mission_time) + "\n")
file.write("Maximum Altitude = " + str(peakAltitude) + "\n")
file.write("dt," + str(dT) + "\n")
file.write("sample number, pressure\n")
count = 0
for d in mission_data:
    file.write(str(count) + "," + str(d) + "\n")
    count += 1
file.flush()
file.close()
os.sync()

led.value = False  # Turn off LED to indicate logging is complete


print("Finished")
while True:
    led.value = True
    time.sleep(0.5)
    led.value = False
    time.sleep(0.5)
