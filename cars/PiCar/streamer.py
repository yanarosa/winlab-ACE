import io
import socket 
import struct
import threading
from socket_wrapper import *
from observer import *

class Streamer(Observer):
    def __init__(self, sock):
        self.sock=sock
        self.observe("new_data", self.send)


    def send(self, flag):
        try:
            image=io.BytesIO(flag.image.getvalue())
            imsize=image.seek(0, io.SEEK_END)
            THR=flag.THR
            STR=flag.STR
            send_stuff(self.sock, struct.pack('<Lhh', imsize, THR, STR))
            image.seek(0)
            nsent=send_stuff(self.sock, image.read())
            if nsent==-1:
                print("client closed connection, stopping")
                Flag("BrokenPipe", {})
        except socket.error:
            print("connection broken, client no longer recieving")
            print(datetime.datetime.now().strftime(time_format))
            Flag("BrokenPipe", {})




