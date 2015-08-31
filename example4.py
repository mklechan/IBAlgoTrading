''' Simple example of using the SWIG generated TWS wrapper to request historical
data from interactive brokers.

Note:
* Communication with TWS is asynchronous; requests to TWS are made through the
EPosixClientSocket class and TWS responds at some later time via the functions
in our EWrapper subclass.
* If you're using a demo account TWS will only respond with a limited time
period, no matter what is requested. Also the data returned is probably wholly
unreliable.

'''

from datetime import datetime, timedelta
import time

from swigibpy import EWrapper, EPosixClientSocket, Contract, Order

import sys
sys.path.append('/home/mchan/git/Artemis/SwigIbPy/')
from ArtemisIBWrapper import ArtemisIBWrapper
###

# Instantiate our callback object
class testTWS(object):
    def __init__(self):
        self.callback = ArtemisIBWrapper()
	self.tws = EPosixClientSocket(self.callback)
	self.tws.eConnect("", 7496, 44, poll_interval=1)

    def run(self):
	# Simple contract for GOOG
	contract = Contract()
	#contract.conId = 114376112
	contract.exchange = "SMART"
	contract.symbol = "ATK"
	contract.secType = "STK"
	#contract.right = "PUT"
	contract.currency = "USD"
	#contract.secType = 'OPT'
	#contract.strike = 24
	#contract.expiry = '20121116'
	today = datetime.today()

	order = Order()
	order.orderId = 89
	order.clientId = 44
	order.action = "BUY"
	order.totalQuantity = 1  # may have to calculate a smarter number
	order.orderType = "MKT"
	order.tif = "DAY" 
	order.transmit = True
	order.sweepToFill = True
	order.outsideRth = True

	contract.symbol = "alkjdf"
	self.callback.askPrice = None
	self.tws.reqMktData(2, contract, "", 1)
	max_wait = timedelta(seconds=30) + datetime.now()
	while self.callback.askPrice is None:
	    if datetime.now() > max_wait:
		print "max wait giving up"
		break
	print self.callback.askPrice


if __name__ == '__main__':
	myTest = testTWS()
	myTest.run()


#print "\nDisconnecting..."
#tws.eDisconnect()
#time.sleep(1)

# Request some historical data.
#callback.lastClose = None
#callback.close = None
#tws.reqHistoricalData(
#        1,                                          #tickerId,
#        contract,                                   #contract,
#        today.strftime("%Y%m%d %H:%M:%S %Z"),       #endDateTime,
#        "1 D",                                      #durationStr,
#        "1 hour",                                    #barSizeSetting,
#        "BID_ASK",                                   #whatToShow,
#        0,                                          #useRTH,
#        1                                           #formatDate
#    )
#
#while (callback.close is None):
#    pass


#callback.accountEnd = False
#tws.reqAccountUpdates(1, '')
#while not callback.accountEnd:
#    pass

