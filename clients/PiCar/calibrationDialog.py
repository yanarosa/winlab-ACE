import struct
from socket_wrapper import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

class calibrationDialog(QDialog):

    def __init__(self, commands_out_socket, parent=None):
        super(calibrationDialog, self).__init__(parent)
        self.comm_socket=commands_out_socket
        left_button=QPushButton("Calibrate Left")
        right_button=QPushButton("Calibrate Right")
        ok_button=QPushButton("OK")
        layout=QGridLayout()
        layout.addWidget(left_button, 0, 0)
        layout.addWidget(right_button, 0, 1)
        layout.addWidget(ok_button, 1, 1)
        self.setLayout(layout)

        ok_button.clicked.connect(self.accept)
        left_button.clicked.connect(self.calib_left)
        right_button.clicked.connect(self.calib_right)

    def calib_left(self):
        message_buf=struct.pack("IhBB", 0, 0, 3, 4) #calibration left message
        print("sending calib left message")
        send_stuff(self.comm_socket, message_buf) 

    def calib_right(self):
        message_buf=struct.pack("IhBB", 0, 0, 3, 5) #calibration right message
        print("sending calib right message")
        send_stuff(self.comm_socket, message_buf) 


