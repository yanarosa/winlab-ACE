import threading
import datetime
from observer import *

class DataCollector(Observer):
    def __init__(self):
        self.observe("dc_start", self.start_collecting)
        self.observe("dc_stop", self.stop_collecting)


    def start_collecting

