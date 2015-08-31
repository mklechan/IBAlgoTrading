import strategy
import fowscanner
import datetime
import multiprocessing
import time
import sys
from swigibpy import EWrapper, EPosixClientSocket, Contract
sys.path.append('/home/mchan/git/Artemis/SwigIbPy')
from ArtemisIBWrapper import ArtemisIBWrapper


callback = ArtemisIBWrapper()
tws = EPosixClientSocket(callback)
# Connect the socket
socketnum = 10
tws.eConnect("", 7496, socketnum, poll_interval=1)

for i in range(0,4):
    socketnum += 1
    tws.eDisconnect()
    print "Socket number: ", socketnum
    tws.eConnect("", 7496, socketnum, poll_interval=1)
    time.sleep(3)
