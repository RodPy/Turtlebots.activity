# Copyright (c) 2011 Bastian Venthur
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


"""
This module provides access to the data provided by the AR.Drone.
"""

import select
import socket
import threading
import multiprocessing

import libardrone

ARDRONE_NAVDATA_PORT = 5554
ARDRONE_VIDEO_PORT = 5555
ARDRONE_COMMAND_PORT = 5556

ARDRONE_DIRECCION = '192.168.1.1'

class ARDroneNetworkProcess(multiprocessing.Process):
    """ARDrone Network Process.

    This process collects data from the video and navdata port, converts the
    data and sends it to the IPCThread.
    """

    def __init__(self, nav_pipe, video_pipe, com_pipe):
        multiprocessing.Process.__init__(self)
        self.nav_pipe = nav_pipe
        self.com_pipe = com_pipe

    def run(self):

        nav_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        nav_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        nav_socket.setblocking(0)
        nav_socket.bind(('', ARDRONE_NAVDATA_PORT))    
        try:
            nav_socket.sendto("\x01\x00\x00\x00", (ARDRONE_DIRECCION, ARDRONE_NAVDATA_PORT))
        except:
            print "arnetwork: error al inicializar puerto navdata"
            
        stopping = False
        while not stopping:
            inputready, outputready, exceptready = select.select([nav_socket, self.com_pipe], [], [])
            for i in inputready:
				# Recibo datos de navegacion del drone.
                if i == nav_socket:
                    while 1:
                        try:
                            data = nav_socket.recv(65535)
                        except IOError:
                            # we consumed every packet from the socket and
                            # continue with the last one
                            break
                    navdata = libardrone.decode_navdata(data)
                    self.nav_pipe.send(navdata)
				# Me avisaron que tengo que irme.
                elif i == self.com_pipe:
                    _ = self.com_pipe.recv()
                    stopping = True
                    break
        nav_socket.close()


class IPCThread(threading.Thread):
    """Inter Process Communication Thread.

    This thread collects the data from the ARDroneNetworkProcess and forwards
    it to the ARDrone.
    """

    def __init__(self, drone):
        threading.Thread.__init__(self)
        self.drone = drone
        self.stopping = False

    def run(self):
        while not self.stopping:
            inputready, outputready, exceptready = select.select([self.drone.nav_pipe], [], [], 1)
            for i in inputready:
                if i == self.drone.nav_pipe:
                    while self.drone.nav_pipe.poll():
                        navdata = self.drone.nav_pipe.recv()
                    self.drone.navdata = navdata

    def stop(self):
        """Stop the IPCThread activity."""
        self.stopping = True

