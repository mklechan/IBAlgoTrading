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
callback = ArtemisIBWrapper()

# Instantiate a socket object, allowing us to call TWS directly. Pass our
# callback object so TWS can respond.
tws = EPosixClientSocket(callback)

# Connect to tws running on localhost
#tws.eConnect("", 7496, 47, poll_interval=1)
tws.eConnect("", 7496, 47)
accountNumber = ''
# Simple contract for GOOG
contract = Contract()
#contract.conId = 114376112
contract.exchange = "SMART"
contract.symbol = "PRXL"
contract.secType = "STK"
#contract.right = "PUT"
contract.currency = "USD"
#contract.secType = 'OPT'
#contract.strike = 24
#contract.expiry = '20121116'
today = datetime.today()

#callback.tickDataEnd = False 
#tws.reqMktData(1, contract, "", 1)
#while (not callback.tickDataEnd):
#    pass
#print "Market data request sent, ASK price is: ", callback.askPrice
#askPrice = 23.04
callback.contractDataEnd = False
callback.StrikesHash = dict()
callback.Strikes = []

#tws.reqContractDetails(1, contract)
#while not callback.contractDataEnd:
#    pass
#for i in range(0, len(sorted(callback.Strikes))):
#    if sorted(callback.Strikes)[i] > askPrice:
#         callStrikePrice = sorted(callback.Strikes)[i-1]
#         callConId = callback.StrikesHash[callStrikePrice][0]
#         callMultiplier = callback.StrikesHash[callStrikePrice][1]
#         putStrikePrice = sorted(callback.Strikes)[i]
#         putConId = callback.StrikesHash[putStrikePrice][0]
#         putMultiplier = callback.StrikesHash[putStrikePrice][1]
#         break

order = Order()
order.orderId = 7
order.clientId = 46
order.action = "SELL"
order.totalQuantity = 78  # may have to calculate a smarter number
order.orderType = "MKT"
order.tif = "DAY" 
order.transmit = True
order.sweepToFill = False
order.outsideRth = True


callback.accountEnd = False
portfolioList = []
callback.portfolioContract = None
callback.portfolioPosition = None

tws.reqAccountUpdates(1, accountNumber)
#while (not callback.accountEnd):
#    callback.portfolioContract = None 
#    callback.portfolioPosition = None
#    max_wait = timedelta(seconds=6) + datetime.now()
#    while (callback.portfolioPosition is None or callback.portfolioContract is None):
#        if datetime.now() > max_wait:
#            break
#    if callback.portfolioPosition is not None and callback.portfolioContract is not None:
#	myContract = Contract() 
#	myContract.exchange = "SMART"
#	myContract.currency = "USD"
#	myContract.symbol = callback.portfolioContractSymbol
#	myContract.conId = callback.portfolioContractConId
#	myContract.secType = callback.portfolioContractSecType
#	myContract.strike = callback.portfolioContractStrike
#	myContract.expiry = callback.portfolioContractExpiry
#	myContract.right = callback.portfolioContractRight
#	myPosition = callback.portfolioPosition
#        portfolioList.append((myContract, myPosition))
#
tws.reqAccountUpdates(0, accountNumber)


#contract.symbol = "alkdjflk"
#callback.askPrice = None
#tws.reqMktData(2, contract, "", 1)
#max_wait = timedelta(seconds=30) + datetime.now()
#while callback.askPrice is None:
#    if datetime.now() > max_wait:
#	print "max wait giving up"
#	break
#print callback.askPrice

#print "\nDisconnecting..."
#tws.eDisconnect()
#time.sleep(1)

# Request some historical data.
#callback.lastClose = None
#callback.close = None
#tws.reqHistoricalData(
#        2,                                          #tickerId,
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

callback.askPrice = None
callback.lastPrice = None
callback.closePrice = None
callback.tickDataEnd = False
tws.reqMktData(2, contract, "", 0)

max_wait = timedelta(seconds=30) + datetime.now()
while callback.askPrice is None:
    time.sleep(0.0001)
    if datetime.now() > max_wait:
       print "max wait giving up"
       break
tws.cancelMktData(2)
print "Here's the ask price: ", callback.askPrice

