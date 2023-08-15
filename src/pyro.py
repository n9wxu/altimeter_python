import board
from digitalio import DigitalInOut, Direction, Pull
import analogio
import busio
import adafruit_bmp280
import time


class pyroHw:
    # define the Hardware for the board
    def __init__(self):
        self.sda1_pin = board.GP18
        self.scl1_pin = board.GP19
        self.sda0_pin = board.GP20
        self.scl0_pin = board.GP21

        self.sense1_pin = board.A0
        self.sense2_pin = board.A1
        self.pixel_pin = board.GP1
        self.fire1_pin = board.GP9
        self.fire2_pin = board.GP11
        self.pyro_low_pin = board.GP10
        self.led_pin = board.GP25
        self.tx_pin = board.GP0
        self.rx_pin = board.GP1
        # Setup LED
        self.led_pin = board.GP25
        self.led = DigitalInOut(self.led_pin)
        self.led.switch_to_output()
        self.sense1 = analogio.AnalogIn(self.sense1_pin)
        self.sense2 = analogio.AnalogIn(self.sense2_pin)
        self.pyro_low = DigitalInOut(self.pyro_low_pin)
        self.pyro_low.switch_to_output(value=False)
        self.fire1 = DigitalInOut(self.fire1_pin)
        self.fire1.switch_to_output(value=False)
        self.fire2 = DigitalInOut(self.fire2_pin)
        self.fire2.switch_to_output(value=False)
        self.uart = busio.UART(self.tx_pin, self.rx_pin, baudrate=115200)
        self.i2c = busio.I2C(self.scl0_pin, self.sda0_pin)
        self.bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, 0x77)
        self.bmp280.sea_level_pressure = 1013.25
        self.bmp280.mode = adafruit_bmp280.MODE_NORMAL
        self.bmp280.standby_period = adafruit_bmp280.STANDBY_TC_500
        self.bmp280.iir_filter = adafruit_bmp280.IIR_FILTER_X16
        self.bmp280.overscan_pressure = adafruit_bmp280.OVERSCAN_X16
        self.bmp280.overscan_temperature = adafruit_bmp280.OVERSCAN_X2

    def ledOn(self):
        self.led.value = True

    def ledOff(self):
        self.led.value = False

    def pyroTest(self) -> bool:
        self.fire1.value = False
        self.fire2.value = False
        self.pyro_low.value = True
        result = self.sense1.value < 1000 and self.sense2.value < 1000
        self.pyro_low.value = False
        return result

    def firePyro1(self):
        print("pyro 1 fire")
        self.uart.write("ignite 1\n".encode())
        self.pyro_low.value = True
        self.fire1.value = True

    def firePyro2(self):
        print("pyro 2 fire")
        self.uart.write("ignite 2\n".encode())
        self.pyro_low.value = True
        self.fire2.value = True

    def safeAllPyros(self):
        print("pyro safe")
        self.pyro_low.value = False
        self.fire1.value = False
        self.fire2.value = False

    def readPressure(self) -> float:
        return self.bmp280.pressure

    def speak(self, msg):
        self.uart.write((msg + "\n").encode())

    def readTemperature(self) -> float:
        return bmp280.temperature

    def finish(self):
        print("finished")
        while True:
            self.ledOn()
            time.sleep(0.25)
            self.ledOff()
            time.sleep(0.25)
