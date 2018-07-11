import sys
import io
import socket
import struct
import threading
import datetime
import time
import picamera
import numpy as np

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

sys.path.append('/home/pi/winlab-ACE/cars/PiCar')
from socket_wrapper import *
from calibrationDialog import calibrationDialog

if len(sys.argv)!=2:
    print("must include ip address of car as command line argument")
    sys.exit(1)
car_ip=sys.argv[1]

time_format='%Y-%m-%d_%H-%M-%S'

button_names={ 0:'A',
        1:'B',
        2:'X',
        3:'Y',
        4:'LB',
        5:'RB',
        6:'screen',
        7:'menu',
        8:'xbox' }

analog_names={0:'js1-x',
        1:'js1-y',
        2:'LT',
        3:'js2-x',
        4:'js2-y',
        5:'RT',
        6:'DPad-x',
        7:'DPad-y'}

#we're using a bunch of global variables. Should probably fix that in the future
global image_frame #buffer of rgb data read from client_socket_stream
global commands #variable to hold most recent values of STR and THR from client_socket_stream
global data_lock #lock used to ensure nice sharing of image_frame and commands
global emitter #global instance of emitter class, used to generate a signal for a new data frame
global client_socket_stream #socket streaming data to the client from the car
global client_socket_commands #socket sending commands from the client to the car
global stream_in_thread #thread to read new data frames from client_socket_stream
global commands_out_thread #thread to write new commands to client_socket_commands
global stop_event #event to stop the two threads
global command_lock #lock to allow only one thread to write to client_socket_commands


class ClientGUI(QMainWindow):

    def __init__(self, parent=None):
        global emitter
        super(ClientGUI, self).__init__(parent)

        self.image_label=QLabel()
        self.THR_label=QLabel("0")
        self.STR_label=QLabel("0")
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        emitter.new_image.connect(self.update)

        start_button=QPushButton("start")
        stop_button=QPushButton("stop")
        dc_start=QPushButton("start data collection")
        dc_stop=QPushButton("stop data collection")
        calib_button=QPushButton("calibrate")
        start_button.clicked.connect(self.start_act)
        stop_button.clicked.connect(self.stop_act)

        layout=QGridLayout()
        layout.addWidget(self.image_label, 0, 0, 3, 2)
        layout.addWidget(QLabel("steering value: "), 0, 2, 1, 1)
        layout.addWidget(self.THR_label, 0, 3, 1, 1)
        layout.addWidget(QLabel("throttle value: "), 1, 2, 1, 1)
        layout.addWidget(self.STR_label, 1, 3, 1, 1)
        layout.addWidget(dc_start, 2, 2, 1, 1)
        layout.addWidget(dc_start, 2, 3, 1, 1)
        layout.addWidget(start_button, 3, 0, 1, 1)
        layout.addWidget(stop_button, 3, 1, 1, 1)
        layout.addWidget(calib_button, 3, 2, 1, 1)
        centralwidget=QWidget()
        centralwidget.setLayout(layout)
        self.setCentralWidget(centralwidget)

        self.setWindowTitle("Image Player")
        self.show()

    def stop_act(self):
        global stop_event
        global stream_in_thread
        global commands_out_thread
        stop_event.set() #event to stop threads
        commands_out_thread.join() #join command thread after setting stop event. This thread should return no problem.
        message_buf=struct.pack("IhBB", 0, 0, 3, 1)#stream stop command
        command_lock.acquire()
        send_stuff(client_socket_commands, message_buf)
        command_lock.release()
        stream_in_thread.join() #join stream thread after sending stop command to make sure it's not hanging on a read

    def start_act(self):
        global client_socket_stream
        global client_socket_commands
        global stream_in_thread
        global commands_out_thread
        #TBH, initiating a stream with a command over the other socket is a little unnecessary. As long as we know what
        #order to connect, we shouldn't need to specify to start the stream
        client_socket_commands.connect((car_ip, 8005)) #connect to command socket first
        message_buf=struct.pack("IhBB", 0, 0, 3, 0)#stream start command
        command_lock.acquire()
        send_stuff(client_socket_commands, message_buf)
        command_lock.release()
        time.sleep(.5)
        client_socket_stream.connect((car_ip, 8000)) #should be able to connect after car receives the stream start command
        commands_out_thread.start()
        stream_in_thread.start()

    def start_dc(self):
        global command_lock
        global client_socket_commands
        message_buf=struct.pack("IhBB", 0, 0, 3, 6)#data collection start command
        command_lock.acquire()
        send_stuff(client_socket_commands, message_buf)
        command_lock.release()

    def stop_dc(self):
        global command_lock
        global client_socket_commands
        message_buf=struct.pack("IhBB", 0, 0, 3, 7)#data collection stop command
        command_lock.acquire()
        send_stuff(client_socket_commands, message_buf)
        command_lock.release()

    def update(self):
        global data_lock
        global image_frame
        global commands
        data_lock.acquire()
        qimg=QImage(image_frame.getbuffer(), 128, 96, 128*3, QImage.Format_RGB888)
        self.THR_label.setText(str(commands[1]))
        self.STR_label.setText(str(commands[0]))
        data_lock.release()
        self.image_label.setPixmap(QPixmap.fromImage(qimg.mirrored(True, True).scaled(640, 480)))

    def calibrate(self):
        global client_socket_commands
        global command_lock
        message_buf=struct.pack("IhBB", 0, 0, 3, 2) #calibration start message
        command_lock.acquire()
        send_stuff(client_socket_commands, message_buf)
        cali_dialog=calibrationDialog(client_socket_commands)
        cali_dialog.exec_()
        message_buf=struct.pack("IhBB", 0, 0, 3, 3) #calibration stop message
        send_stuff(client_socket_commands, message_buf)
        command_lock.release()

def cleanup():
        global client_socket_stream
        global client_socket_commands
        client_socket_stream.close()
        client_socket_commands.close()
        
class Emitter(QObject):
    new_image=pyqtSignal()

def stream_in_process(stop_ev, sock, emitter):
    global data_lock
    global commands
    global image_frame
    try:
        while not stop_ev.isSet(): 
            image_data=struct.unpack('<Lhh', read_stuff(sock, struct.calcsize('<Lhh')).getbuffer())
            data_lock.acquire()
            image_frame=read_stuff(sock, image_data[0])
            image_frame.seek(0)
            commands=(image_data[1], image_data[2])
            data_lock.release()
            emitter.new_image.emit()
        print("process shutting down now")
        sock.shutdown(socket.SHUT_RDWR)

    except BrokenPipeError:
        print("connection broken, server no longer sending")
        print(datetime.datetime.now().strftime(time_format))
        stop_ev.set()
            
def commands_out_process(stop_ev, js_out, commands_out_sock):
    #thread for outputting commands
    global command_lock
    try: 
        while not stop_ev.isSet():
            evbuf=js_out.read(8)
            if evbuf:
                time, value, in_type, in_id=struct.unpack('IhBB', evbuf)
                print(in_type, in_id) 
                command_lock.acquire()
                send_stuff(commands_out_sock, evbuf) 
                command_lock.release()
                if in_type==1 and button_names[in_id]=='xbox' and value==1:
                    stop_event.set()
    except BrokenPipeError:
        print("command connection broken, server no longer recieving")
        print(datetime.datetime.now().strftime(time_format))
        stop_ev.set()

joystick_file='/dev/input/js0'
js_out=open(joystick_file, 'rb')

#define global variables:
emitter=Emitter() #used to emit signal when there is a new image
data_lock=threading.Lock() #lock for using image_frame buffer
image_frame=io.BytesIO() #buffer for image data
stop_event=threading.Event()
client_socket_stream=socket.socket() 
client_socket_commands=socket.socket() 
stream_in_thread=threading.Thread(target=stream_in_process, args=[stop_event, client_socket_stream, emitter])
commands_out_thread=threading.Thread(target=commands_out_process, args=[stop_event, js_out, client_socket_commands])


app=QApplication(sys.argv)
app.aboutToQuit.connect(cleanup)
player=ClientGUI()
app.exec_()
