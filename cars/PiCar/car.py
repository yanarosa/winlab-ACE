import sys
from observer import *

sys.path.append('/home/pi/Sunfounder_PiCar')
import picar
import picar.front_wheels, picar.back_wheels
from picar.SunFounder_PCA9685 import Servo


class car(Observer):
    def __init__(self):
        picar.setup() 
        self.bw=picar.back_wheels.Back_Wheels()
        self.fw=picar.front_wheels.Front_Wheels()
        self.fw.turning_max=40 
        self.fw.offset=0 
        self.bw.speed=0
        self.fw.turn(90)
        self.calib_mode=False
        self.observe("calib_start", self.calib_start)
        self.observe("calib_stop", self.calib_stop)
        self.observe("calib_left", self.cali_left)
        self.observe("calib_right", self.cali_right)

    def go(self, STR, THR):
        if self.calib_mode==False:
            if THR==0: 
                self.bw.speed=0 
                self.bw.stop() 
            elif THR<0: 
                self.bw.backward() 
                self.bw.speed=abs(THR) 
            else: 
                self.bw.forward() 
                self.bw.speed=THR 
            self.fw.turn(STR)

    def calib_start(self, flag):
        self.calib_flag=True
        self.fw.calibration()

    def calib_stop(self, flag):
        self.calib_flag=False
        self.fw.cali_ok()

    def cali_left(self, flag):
        self.fw.cali_left()

    def cali_right(self, flag):
        self.fw.cali_right()
