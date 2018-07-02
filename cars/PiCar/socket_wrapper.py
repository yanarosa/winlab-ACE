import io
import socket
import struct

def send_stuff(sock, stuff):
    stufflen=len(stuff)
    totalsent=0
    while totalsent<stufflen:
        sent=sock.send(stuff[totalsent:])
        if sent==0:
            return -1
        totalsent=totalsent+sent
    return totalsent

def read_stuff(sock, stufflen):
    chunks=io.BytesIO()
    bytes_recd=0 
    while bytes_recd<stufflen:
        chunk=sock.recv(8)
        if chunk=='':
            return -1
        chunks.write(chunk)
        bytes_recd=bytes_recd+len(chunk)
    return chunks 

class SocketReader(object):
    #this class packages a client connection with a reader function

    def __init__(self, connection):
        self.conn=connection

    def read(self, nbytes):
        try:
            res=read_stuff(self.conn, nbytes)
            return res
        except socket.error:
            print("Socket connection broken")
            return -1


