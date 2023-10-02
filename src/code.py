import time
import os
import gc
from config import configuration
from altimeter import makeAltitude

import save
import pyro

pyro = pyro.pyroHw()

config = configuration()

loopTime = 0

pyro.ledOn()

history = config.getHistory()
launchDetectAltitude = config.getLaunchDetection()

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
    p = pyro.readPressure()
    mission_data.append(p)
    print(str(p) + " : " + str(makeAltitude(p)) + " : " + str(len(mission_data)))
    time.sleep(0.050)

launchAltitude = makeAltitude(sum(mission_data[-history:]) / history)
peakAGL = 0

startTime = time.monotonic_ns()
armed = False
noPyro2 = False
previousSample = 0
lastTalk = 0
pyro1Index = 0
pyro2Index = 0


def getTimeMs() -> int:
    now = time.monotonic_ns() - startTime
    return now / 1000000


print("starting the loop")

while logging:
    now = getTimeMs()
    if now - previousSample > 50:
        previousSample = now

        try:
            p = pyro.readPressure()
            mission_data.append(p)
        except Exception as e:
            print("exception : " + str(e))
            ramLimit = True
            logging = False

        avgAltitude = makeAltitude(sum(mission_data[-history:]) / history)
        altitude = makeAltitude(sum(mission_data[-3:]) / 3)

        agl = altitude - launchAltitude
        avgAgl = avgAltitude - launchAltitude

        if agl > peakAGL:
            peakAGL = agl

        if not flying:
            while len(mission_data) > history:
                mission_data.pop(0)
            # sit on the pad for 1 seconds
            if not armed:
                if now > 1000:
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
                if abs(agl - avgAgl) > launchDetectAltitude:
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

                if now - lastTalk > 2000:
                    print("altitude : " + str(int((agl) / 100) * 100))
                    pyro.speak("altitude " + str(int((agl) / 100) * 100))
                    lastTalk = now
            # landing detector
            if avgAgl < 5.0:
                logging = False

            # maximum flight detector 1 minutes
            if now - launchTime > 60000:
                print("out of time")
                logging = False

flying = False
mission_time = float((now - launchTime)) / 1000.0
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

save.write(
    "data.csv",
    mission_data,
    mission_time,
    peakAGL,
    pyro1Index,
    pyro2Index,
    temperature,
    dT,
)

pyro.ledOff()

pyro.finish()
