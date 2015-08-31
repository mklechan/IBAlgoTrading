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
from DataDownloadIBWrapper import ArtemisIBWrapper
#from ArtemisIBWrapper import ArtemisIBWrapper
###

# Instantiate our callback object
callback = ArtemisIBWrapper()

# Instantiate a socket object, allowing us to call TWS directly. Pass our
# callback object so TWS can respond.
tws = EPosixClientSocket(callback)

# Connect to tws running on localhost
tws.eConnect("", 7496, 46, poll_interval=1)
accountNumber = ''
contract = Contract()
contract.exchange = "SMART"
contract.symbol = "TOT"
contract.secType = "STK"
#contract.right = "PUT"
contract.currency = "USD"
#contract.secType = 'OPT'
#contract.strike = 24
#contract.expiry = '20121116'
today = datetime.today()


#tws.reqAccountUpdates(1, accountNumber)
#tws.reqAccountUpdates(0, accountNumber)


callback.histTickerID = contract.symbol 
tws.reqHistoricalData(
        1,                                          #tickerId,
        contract,                                   #contract,
        datetime(2012, 11, 2, 23, 59, 59).strftime("%Y%m%d %H:%M:%S"),       #endDateTime,
        "2 D",                                      #durationStr,
        "1 min",                                    #barSizeSetting,
        "TRADES",                                   #whatToShow,
        0,                                          #useRTH,
        1                                           #formatDate
    )
