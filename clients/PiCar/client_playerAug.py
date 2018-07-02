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


def read_stuff(sock, stufflen):
    chunks=io.BytesIO()
    bytes_recd=0
    while bytes_recd<stufflen:
        chunk=sock.recv(min(stufflen-bytes_recd, 8192))
        if chunk=='':
            return -1
        chunks.write(chunk)
        bytes_recd=bytes_recd+len(chunk)
    return chunks

def send_stuff(sock, stuff):
    stufflen=len(stuff)
    totalsent=0
    while totalsent<stufflen:
        sent=sock.send(stuff[totalsent:])
        if sent==0:
            return -1
        totalsent=totalsent+sent
    return totalsent


global image_frame 
global lock
global emitter
global client_socket_stream
global client_socket_commands
global client_thread 
global stop_event
global commands_out_thread

class ImagePlayer(QMainWindow):

    def __init__(self, parent=None):
        global emitter
        super(ImagePlayer, self).__init__(parent)

        self.image_label=QLabel()
        self.THR_label=QLabel("0")
        self.STR_label=QLabel("0")
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        emitter.new_image.connect(self.update)
        start_button=QPushButton("start")
        stop_button=QPushButton("stop")
        start_button.clicked.connect(self.start_act)
        stop_button.clicked.connect(self.stop_act)
        layout=QGridLayout()
        layout.addWidget(self.image_label, 0, 0, 1, 2)
        layout.addWidget(start_button, 1, 0, 1, 1)
        layout.addWidget(stop_button, 1, 1, 1, 1)
        centralwidget=QWidget()
        centralwidget.setLayout(layout)
        self.setCentralWidget(centralwidget)

        self.setWindowTitle("Image Player")
        self.show()

    def stop_act(self):
        global stop_event
        global client_thread
        stop_event.set()
        client_thread.join()
        

    def start_act(self):
        global client_socket_stream
        global client_socket_commands
        global client_thread
        global commands_out_thread
        client_socket_commands.connect((car_ip, 8005))
        client_socket_stream.connect((car_ip, 8000))
        client_thread.start()
        commands_out_thread.start()


    def update(self):
        global lock
        global image_frame
        lock.acquire()
        qimg=QImage(image_frame.getbuffer(), 128, 96, 128*3, QImage.Format_RGB888)
        lock.release()
        self.image_label.setPixmap(QPixmap.fromImage(qimg.mirrored(True, True).scaled(640, 480)))

def cleanup():
        global client_socket_stream
        global client_socket_commands
        client_socket_stream.close()
        client_socket_commands.close()
        
class Emitter(QObject):
    new_image=pyqtSignal()

def client_process(stop_ev, sock, emitter):
    global lock
    global image_frame
    try:
        while not stop_ev.isSet(): 
            image_data=struct.unpack('<Lhh', read_stuff(sock, struct.calcsize('<Lhh')).getbuffer())
            lock.acquire() 
            image_frame=read_stuff(sock, image_data[0])
            image_frame.seek(0)
            lock.release()
            emitter.new_image.emit()
        print("process shutting down now")
        sock.shutdown(socket.SHUT_RDWR)

    except BrokenPipeError:
        print("connection broken, server no longer sending")
        print(datetime.datetime.now().strftime(time_format))
        stop_ev.set()
            
def commands_out_process(stop_event, js_out, commands_out_sock):
    #thread for outputting commands
    try: 
        while not stop_event.isSet():
            evbuf=js_out.read(8)
            time, value, in_type, in_id=struct.unpack('IhBB', evbuf)
            print(in_type, in_id) 
            if evbuf:
                send_stuff(commands_out_sock, evbuf) 
                if in_type==1 and button_names[in_id]=='xbox' and value==1:
                    stop_event.set()
    except BrokenPipeError:
        print("command connection broken, server no longer recieving")
        print(datetime.datetime.now().strftime(time_format))
        stop_event.set()

joystick_file='/dev/input/js0'
js_out=open(joystick_file, 'rb')

#define global variables:
emitter=Emitter() #used to emit signal when there is a new image
lock=threading.Lock() #lock for using image_frame buffer
image_frame=io.BytesIO() #buffer for image data
stop_event=threading.Event()
client_socket_stream=socket.socket() 
client_socket_commands=socket.socket() 
client_thread=threading.Thread(target=client_process, args=[stop_event, client_socket_stream, emitter])
commands_out_thread=threading.Thread(target=commands_out_process, args=[stop_event, js_out, client_socket_commands])


app=QApplication(sys.argv)
app.aboutToQuit.connect(cleanup)
player=ImagePlayer()
app.exec_()
