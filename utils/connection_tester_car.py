import sys
import io
import socket 
import struct
import time
import datetime
import picamera
import threading

sys.path.append('/home/pi/winlab-ACE/cars/PiCar')
from socket_wrapper import *

button_names={0:'A',
        1:'B',
        2:'X',
        3:'Y',
        4:'LB',
        5:'RB',
        6:'screen',
        7:'menu',
        8:'xbox'}

analog_names={0:'js1-x',
        1:'js1-y',
        2:'LT',
        3:'js2-x',
        4:'js2-y',
        5:'RT',
        6:'dpad-x',
        7:'dpad-y'}


commands_server=socket.socket()
commands_server.bind(('', 8005))
commands_server.listen(0)
(commands_in_sock, address)=commands_server.accept()
print(address)


stop_event=threading.Event()
js_source=SocketReader(commands_in_sock) #joystick input from socket

try:
    while not stop_event.isSet():
        ev_buf=js_source.read(8)
        if ev_buf!=-1:
            time, value, in_type, in_id=struct.unpack('IhBB', ev_buf.getvalue())
            if in_type==2 and in_id in analog_names.keys():
                print("type: 2, id: %s, value: %d" %(analog_names[in_id], value))
            elif in_type==1 and in_id in button_names.keys():
                print("type: 1, id: %s, value: %d" %(button_names[in_id], value))
                if button_names[in_id]=="xbox":
                    stop_event.set()
                    print("quitting")
            elif in_type==3:
                print("type: 3, id: %d" %in_id)




finally:
    commands_in_sock.close()
    commands_server.close()
    print("connection closed")


