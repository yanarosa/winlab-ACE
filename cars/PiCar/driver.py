import sys
import io
import socket 
import struct
import time
import datetime
import picamera
import threading

from controller_object import ControllerObject
from socket_wrapper import *
sys.path.append('/home/pi/Sunfounder_PiCar')
import picar
import picar.front_wheels, picar.back_wheels
from picar.SunFounder_PCA9685 import Servo

picar.setup()

bw=picar.back_wheels.Back_Wheels()
fw=picar.front_wheels.Front_Wheels()
pan_servo=Servo.Servo(1)
tilt_servo=Servo.Servo(2)

fw.offset=0
pan_servo.offset=10
tilt_servo.offset=0

bw.speed=0
fw.turn(90)
pan_servo.write(90)
tilt_servo.write(90)

time_format='%Y-%m-%d_%H-%M-%S'

stream_server=socket.socket()
commands_server=socket.socket()
stream_server.bind(('', 8000))
commands_server.bind(('', 8005))
stream_server.listen(0)
commands_server.listen(0)
(commands_in_sock, address)=commands_server.accept()
(stream_out_sock, address)=stream_server.accept()

stream=io.BytesIO()
stop_event=threading.Event()
commands_lock=threading.Lock()
car_commands=[0, 0]

def server_process(stop_ev, sock, stream):
    try:
        while not stop_ev.isSet():
            if stream.tell()!=0:
                imsize=stream.tell()
                commands_lock.acquire()
                THR, STR=car_commands
                commands_lock.release()
                send_stuff(sock, struct.pack('<Lhh', imsize, THR, STR))
                stream.seek(0)
                nsent=send_stuff(sock, stream.read())
                if nsent==-1:
                    print("client closed connection, stopping")
                    stop_ev.set()
                stream.seek(0)
                stream.truncate()
            time.sleep(.0001)
        #send_stuff(client_socket, struct.pack('<L', 0))
    except socket.error:
        print("connection broken, client no longer recieving")
        print(datetime.datetime.now().strftime(time_format))
        stop_ev.set()

js_source=SocketReader(commands_in_sock) #joystick input from socket
server_thread=threading.Thread(target=server_process, args=[stop_event, stream_out_sock, stream])
controller=ControllerObject(js_source) #controller handler
controller.start_thread()


try:
    camera=picamera.PiCamera()
    camera.resolution=(128, 96)
    camera.framerate=20
    server_thread.start()
    time.sleep(2)
    camera.start_recording(stream, format='rgb')
    while not stop_event.isSet():
        commands=controller.carpoll()
        if len(commands)==1:
            stop_event.set()
        else:
            commands_lock.acquire()
            car_commands=commands
            commands_lock.release()
            if commands[0]==0:
                bw.speed=0
                bw.stop()
            elif commands[0]<0:
                bw.backward()
                bw.speed=abs(commands[0])
            else:
                bw.forward()
                bw.speed=commands[0]
            fw.turn(commands[1])
        time.sleep(.01)
    camera.stop_recording()
    server_thread.join()

finally:
    stream_out_sock.close()
    stream_server.close()
    controller.stop_thread()
    commands_in_sock.close()
    commands_server.close()
    print("connection closed")
