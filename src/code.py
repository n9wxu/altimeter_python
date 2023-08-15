import time
import os
import gc
from altimeter import makeAltitude

# pick either pyro or test.  pyro uses the hardware.  Test uses a data file
import pyro

pyro = pyro.pyroHw()

# import test
# pyro = test.testSys()

# configure the system
flying = False

filename = "data.csv"


# simple function to test if a file is present
def exists(f) -> bool:
    os.sync()
    if f in os.listdir("/"):
        print("found " + f)
        return True
    else:
        return False


if exists(filename):
    print("Standing by for file transfer. To fly and log, remove USB cable.")
    while exists(filename):
        pyro.ledOn()
        time.sleep(0.1)
        pyro.ledOff()
        time.sleep(0.1)

loopTime = 0

pyro.ledOn()

gc.collect()  # garbage collect the memory

history = 20

ramLimit = False
flying = False
logging = True
launchTime = 0
pyroFireTime = 0
apogee = False
temperature = pyro.readTemperature()
# 200 data points to seed the pressure sum
mission_data = []
for i in range(0, history):
    mission_data.append(pyro.readPressure())

launchAltitude = makeAltitude(sum(mission_data[-history:]) / history)
peakAGL = 0

startTime = time.monotonic_ns()
armed = False
noPyro2 = False
previousSample = 0
lastTalk = 0
pyro1Index = 0
pyro2Index = 0

while logging:
    now = time.monotonic_ns()
    if now - previousSample > 50000000:
        previousSample = now

        try:
            mission_data.append(pyro.readPressure())
        except Exception as e:
            ramLimit = True
            logging = False

        avgAltitude = makeAltitude(sum(mission_data[-history:]) / history)
        altitude = makeAltitude(sum(mission_data[-3:]) / 3)

        agl = altitude - launchAltitude
        avgAgl = avgAltitude - launchAltitude

        if agl > peakAGL:
            peakAGL = agl

        if not flying:
            mission_data.pop(0)
            launchTime = (
                now  # keep updating the launchTime.  This will stop when we are saving.
            )
            # sit on the pad for 10 seconds
            if not armed:
                if (now - startTime) > 10000000000:
                    print("armed")
                    pyro.speak("call n9wxu")
                    if pyro.pyroTest():
                        pyro.speak("ready")
                    else:
                        pyro.speak("fail")
                    lastTalk = now
                    armed = True
            else:
                # launch detector
                if abs(agl - avgAgl) > 10:
                    launchTime = now
                    pyro.speak("launch")
                    lastTalk = now
                    print("Launch")
                    print("Altitude : " + str(agl))
                    print("avgAltitude : " + str(avgAgl))
                    print("Launch Altitide : " + str(launchAltitude))
                    print("Launch Time Set To: ", launchTime)
                    flying = True
        else:
            # apogee detector.  peak is 10 ft higher than current altitude
            if not apogee and ((peakAGL - agl) > 10):
                apogee = True
                pyroFireTime = now
                pyro.speak("apogee")
                pyro.speak("altitude " + str(peakAGL))
                print("altitude " + str(agl) + " : ", end="")
                pyro.firePyro1()
                pyro1Index = len(mission_data)
                lastTalk = now
            else:
                if apogee and not noPyro2 and agl < 500:
                    print("altitude " + str(agl) + " : ", end="")
                    pyro.firePyro2()
                    pyro2Index = len(mission_data)
                    noPyro2 = True
                    pyroFireTime = now

                if pyroFireTime and now - pyroFireTime > 500000000:
                    pyro.safeAllPyros()
                    pyroFireTime = 0

                if now - lastTalk > 2000000000:
                    print("altitude : " + str(int((agl) / 100) * 100))
                    pyro.speak("altitude " + str(int((agl) / 100) * 100))
                    lastTalk = now
            # landing detector
            if abs(agl - avgAgl) < 1.0:
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

pyro.speak("touchdown")
print(".")
print("landed")
print("Altitude : " + str(agl))
print("avgAltitude : " + str(avgAgl))
print("mission elapsed time : " + str(mission_time))
print("maximum Altitude : " + str(peakAGL))
print("saving the data")
file = open(filename, "wt")
print("Log File Created")
file.write("mission time = " + str(mission_time) + "\n")
file.write("Maximum Altitude = " + str(peakAGL) + "\n")
file.write("temp," + str(temperature) + "\n")
file.write("dt," + str(dT) + "\n")
file.write("sample number, pressure\n")
count = 0
for d in mission_data:
    file.write(str(count) + "," + str(d))
    if count == pyro1Index:
        file.write(", fire pyro 1")
    if count == pyro2Index:
        file.write(", fire pyro 2")
    file.write("\n")
    count += 1
file.flush()
file.close()

pyro.ledOff()

pyro.finish()
