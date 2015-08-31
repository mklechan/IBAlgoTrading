import strategy
import fowscanner
import datetime
import time
import sys
from swigibpy import EWrapper, EPosixClientSocket, Contract, TWSError, Order
sys.path.append('/home/mchan/git/Artemis/SwigIbPy')
#from ArtemisIBWrapperSilent import ArtemisIBWrapper
import ArtemisIBWrapperSilent
sys.path.append('/home/mchan/git/Artemis/util')
import dbutil
#import pdb

class TradeManager(object):
    def __init__(self):
	self.accountNumber = ''
	self.optionExpiry = '20121221'   # This needs manual updating!
	self.maxAskBidRatio = 1.25
	self.maxAskLastPriceRatio = 1.02
	self.maxOrderQueueLength = 3
	# Create a file for TWS logging
        self.twslog_fh = open('/home/mchan/git/Artemis/twslog.txt', 'a', 0)
	self.twslog_fh.write("Session Started " + str(datetime.datetime.now()) + "\n")
	self.callback = ArtemisIBWrapperSilent.ArtemisIBWrapper() 
	self.tws = EPosixClientSocket(self.callback)
	self.orderIdCount = 1 # This will be updated automatically
	self.requestIdCount = 1
	self.invested = False
	self.maxLimitPriceFactor = 1.02  # No limit orders above 2% of current ask price
	# Connect the socket
	self.socketnum = 30
	self.tws.eConnect("", 7496, self.socketnum, poll_interval=1)
	# Strategy Generic object, has methods for interpreting consensus out/under performance
	self.Strat = strategy.Strategy()
	# Queue for orders
	self.orderQueue = []
	# Setup DB connector
	self.db = dbutil.db(h='127.0.0.1', schema='mchan')
	
	# Query Cash Account Balance
	self.updateBuyingPowerNextId()

    def updateBuyingPowerNextId(self):
        self.callback.myNextValidId = None
        self.callback.buyingPower = None
        self.tws.reqAccountUpdates(1, self.accountNumber)
        while (self.callback.buyingPower is None or self.callback.myNextValidId is None):
            pass
        self.buyingPower = float(self.callback.buyingPower)
        self.orderIdCount = int(self.callback.myNextValidId)
        print "Buying Power recognized: ", self.buyingPower, " Next valid id recognized: ", self.orderIdCount
        self.tws.reqAccountUpdates(0, self.accountNumber)

    def calcInvSize(self):
	'''
	Calculates proper investment size
	'''
	# We take the total size of the portfolio, cash plus stock, and we divide by four
	# The reasoning is that we want to avoid the day pattern trader restriction
	# Dividing our portfolio size by four ensures that we have enough capital
	# to trade for the four trading opportunities that will happen until we can
	# finally sell our positions
	# This also allows for diversification
	self.updateBuyingPowerNextId()
	portfolioList = self.getPortfolio()
	secMarketPositions = 0
	for myContract, myPosition, myMarketValue in portfolioList:
	    secMarketPositions += myMarketValue		
	totalPortfolioSize = secMarketPositions + self.buyingPower
	investmentSize = min(self.buyingPower, (totalPortfolioSize/4.0))
	print "CALCULATE INVESTMENT SIZE: ", str(investmentSize)
	return investmentSize 
	

    def twsReconnect(self):
	print "Reconnecting TWS"
	self.twslog_fh.write("Reconnecting TWS" + str(datetime.datetime.now()) + '\n')
	self.tws.eDisconnect()
	try:
	    self.tws.eConnect("", 7496, self.socketnum, poll_interval=1)
	except TWSError, e:
	    print e
 	    print "Attempting to reconnect:"
	    for i in range(0,5):
	        time.sleep(5)
	        print "Try ", i
	        try:
	            self.tws.eConnect("", 7496, self.socketnum, poll_interval=1)
	     	    break
		except TWSError, e:
		    print e

    def run(self):
	# Operates every half hour on the clock
	# If the hour is even reconnect the TWS socket	
	if (datetime.datetime.now().hour % 3 == 1 and datetime.datetime.now().minute == 0):
	    self.twsReconnect()
	if (datetime.datetime.now().hour == 6 and datetime.datetime.now().minute == 0):
	    # send in order
	    #self.submitOrders()
	    pass

	if (datetime.datetime.now().hour == 12 and datetime.datetime.now().minute == 30):
	    # leave positions
	    pass	
	

    def storeOrder(self, orderId, contract, order):
	myNow = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) 
	# Assumption here is that the order types are only STK or OPT
	if contract.secType == "STK":
	    self.db.execute('''INSERT INTO mchan.twsOrders VALUES (%i, "%s", "%s", "STK", NULL, NULL, NULL, "%s", %i, "%s");''' % \
				(orderId, contract.exchange, contract.symbol, order.action, order.totalQuantity, myNow))
	    self.db.commit() 
	else:
	    expiry = contract.expiry[0:4] + '-' + contract.expiry[4:6] + '-' + contract.expiry[6:8]
	    self.db.execute('''INSERT INTO mchan.twsOrders VALUES (%i, "%s", "%s", "OPT", "%s", "%s", %f, "%s", %i, "%s");''' % \
				(orderId, contract.exchange, contract.symbol, contract.right, expiry, contract.strike, order.action, order.totalQuantity, myNow))
	    self.db.commit()

    def submitOrders(self):
	for i in self.orderQueue:
	    self.tws.placeOrder(i['order'].orderId, i['contract'], i['order'])
	    self.storeOrder(i['order'].orderId, i['contract'], i['order'])
	self.orderQueue = []
	    
    def createContract(self, ticker, secType):
	contract = Contract()
	contract.exchange = "SMART" # Default exchange, IB routing algo
	contract.symbol = ticker
	contract.secType = secType
	contract.currency = "USD"
	return contract

    def createOrderBuy(self):
	order = Order()
	order.orderId = self.orderIdCount	
	self.orderIdCount += 1
	order.clientId = self.socketnum
	order.action = "BUY"
	order.orderType = "MKT"
	order.tif = "DAY"
	order.transmit = True
	order.sweepToFill = True
	order.outsideRth = True
	return order

    def createMarketOrderEquityBuy(self, contract):
	order = self.createOrderBuy()
	# Tweak the default settings
	order.orderType = "LMT"

	# Grab the current ask price
	self.callback.askPrice = None
	self.callback.lastPrice = None
	self.callback.tickDataEnd = False
	# snapshot = 1 means get one snapshot of market data
	self.tws.reqMktData(self.requestIdCount, contract, "", 1)   # Arguments are id, contract, generic tick types, and snapshot 
	self.requestIdCount += 1
	# Wait until tws responds before proceeding
	#while (self.callback.askPrice is None):
	max_wait = datetime.timedelta(seconds=60) + datetime.datetime.now()
	while (self.callback.askPrice is None):
	    if datetime.datetime.now() > max_wait:
		print "Max wait period reached giving up on market data"	
		order.totalQuantity = 0
		return order

	askPrice = self.callback.askPrice
	lastPrice = self.callback.lastPrice
	print "Ask Price for order is: ", askPrice
	print "Last Price for order is: ", lastPrice
	print "Order Processing..."

 	# Bail if no ask price, or if the difference between ask and the last price is too high
	if askPrice == 0 or askPrice is None or (askPrice/lastPrice) > self.maxAskLastPriceRatio:
	    order.totalQuantity = 0
	    return order

	divPrice = askPrice 
	investmentSize = self.calcInvSize()
	# Need to get the ask price from IB.  wait until the call back variable is set	
	order.totalQuantity = int( investmentSize / divPrice )  # may have to calculate a smarter number
	order.lmtPrice = round(self.maxLimitPriceFactor * divPrice, 2)
	print "Order Quantitiy: ", order.totalQuantity, " Limit Price: ", order.lmtPrice
	return order
   
    def processEvent(self, event, direction, recTime):
	# Asynchronous order receiver
	#if self.invested:
	#    print "Already invested passing"
	#    return
	if direction == "LONG":
	    # Here we recieved a long signal.  We want to send a buy order asap, and then check to see if the market is closed
	    contract = self.createContract(str(event['ticker']), "STK")
	    order = self.createMarketOrderEquityBuy(contract)
	    # Make sure order.totalQuantity is decent size else break out
	    if order.totalQuantity == 0:
		print "Market for security is closed or not liquid, trying option market"
		if datetime.datetime.now().hour <= 9:
		    self.enqueueOptionOrder(event, direction, recTime)
		return
	    print "Placing order..."
	    self.callback.orderState = None
	    self.tws.placeOrder(order.orderId, contract, order)
	    time.sleep(2)
	    if self.callback.orderState == "PreSubmitted":
		# We know that the order happened outside of any trading whatsoever
		print "After market conditions. Appending to queue. Cancelling Order"
		self.tws.cancelOrder(order.orderId)	
		# We still want to send the order in the morning 
		if datetime.datetime.now().hour <= 9:
		    self.enqueueOptionOrder(event, direction, recTime)
	    else:
		pass
		#self.invested = True   # Order has gone through
	else:
	    # Short position but the IRA account cant allow shorting so we enqueue option order
	    # We also know that option markets after hours is non-existant
	    # We only want to enqueue morning orders	
	    # Later we can treat short orders like long orders, ie different types of strategies, not earnings releases which almost
	    # always occurs during non regular trading hours
	    if datetime.datetime.now().hour <= 9: 
	        self.enqueueOptionOrder(event, direction, recTime) 
	    else:
		print "Disallow shorting of after hours poor earnings report"

    def createOptionContract(self, ticker, direction):
	# Need to find current price of the equity
	contract = self.createContract(ticker, "STK")
	
	self.callback.lastPrice = None
	self.callback.closePrice = None
	self.callback.tickDataEnd = False 
	print "Create option contract For: ", contract.symbol, " Type: ", contract.secType
	# snapshot = 1 means get one snapshot of market data
	#print "Request ID " , self.requestIdCount
	self.tws.reqMktData(self.requestIdCount, contract, "", 1)   # Arguments are id, contract, generic tick types, and snapshot 
	self.requestIdCount += 1
	# Wait until tws responds before proceeding
	max_wait = datetime.timedelta(seconds=60) + datetime.datetime.now()
	#while (self.callback.lastPrice is None and self.callback.closePrice is None):
	while (not self.callback.tickDataEnd):
	    if datetime.datetime.now() > max_wait:
		print "Max wait period reached giving up on market data for create option contract"	
                break

	if self.callback.lastPrice is None and self.callback.closePrice is None:
	    return False

	lastPrice = self.callback.lastPrice if self.callback.lastPrice is not None else self.callback.closePrice

	# Setup the option contract to request further details
	contract.right = "CALL" if direction == "LONG" else "PUT"
        contract.secType = "OPT"
	contract.expiry = self.optionExpiry

	# Reset the callback object.  We'll get a list of option contracts with the given
	# ticker, expiry, and call/put.  But we need the right strke price.  
	# The reqContractDetails socket method will return a list of contracts with different Strikes
	# callback EWrapper class method will be called which appends values to the array Strikes
	# and fills out StrikesHash
	# StrikesHash is a dictionary keyed on strike price, with a value of a tuple, contractId and multiplier
	self.callback.Strikes = []
	self.callback.StrikesHash = dict()
	self.callback.contractDataEnd = False

	self.tws.reqContractDetails(self.requestIdCount, contract)
	self.requestIdCount += 1
	# Wait for contract data end
	max_wait = datetime.timedelta(seconds=60) + datetime.datetime.now()
	while not self.callback.contractDataEnd:
	    if datetime.datetime.now() > max_wait:
		print "Max wait period reached giving up on contract details data"	
                break

	if not self.callback.contractDataEnd:
	    return False
	
	# Get the JUST barely in the money call or put  These options seem to be the most liquid 
	# depends on call or put
	for i in range(0, len(sorted(self.callback.Strikes))):
	    if sorted(self.callback.Strikes)[i] > lastPrice:
		callStrikePrice = sorted(self.callback.Strikes)[i-1]
		callConId = self.callback.StrikesHash[callStrikePrice][0]
		callMultiplier = self.callback.StrikesHash[callStrikePrice][1]
		putStrikePrice = sorted(self.callback.Strikes)[i]
		putConId = self.callback.StrikesHash[putStrikePrice][0]
		putMultiplier = self.callback.StrikesHash[putStrikePrice][1]
		break

	# Fill out the rest of the option contract details
	contract.strike = callStrikePrice if direction == "LONG" else putStrikePrice
	contract.conId = callConId if direction == "LONG" else putConId
	contract.multiplier = callMultiplier if direction == "LONG" else putMultiplier
	return contract

#    def createOptionOrder(self, contract):
	
    def verifyOptionLiquidity(self, contract):
	print "Check option liquidity"
	bidClose = self.getLastClose(contract, "BID") 
	askClose = self.getLastClose(contract, "ASK") 
	if not bidClose or not askClose:
	    return False
	return False if (askClose / bidClose) > self.maxAskBidRatio else True
	
    def getLastClose(self, contract, askbid):
	self.callback.histClose = None  # closing bar value for ask/bid	
	self.tws.reqHistoricalData(self.requestIdCount, contract, datetime.datetime.today().strftime("%Y%m%d %H:%M:%S %Z"), \
				   "1 D", "1 hour", askbid, 0, 1) 
	self.requestIdCount += 1
	max_wait = datetime.timedelta(seconds=60) + datetime.datetime.now()
	while (self.callback.histClose is None):
	    if datetime.datetime.now() > max_wait:
		print "Max wait period reached giving up on last close price"	
                break
	close = self.callback.histClose if self.callback.histClose is not None else 10000000
	return float(close)

    def updateOrderQueueOrderSizes(self):
	# Goes through the orderQueue and sets the number of contracts to buy
	orderDollarSize = self.calcInvSize() / len(self.orderQueue)
	for i in self.orderQueue:
	    askClose = self.getLastClose(i['contract'], "ASK") 
	    contractPrice = askClose * int(i['contract'].multiplier)
	    i['order'].totalQuantity = int( (0.9 * orderDollarSize) / contractPrice )
	
    def enqueueOptionOrder(self, event, direction, recTime):
	# Go through current orderQueue and see if there are any worse out/under performance
	# Kick it out.  Max of three orders in orderQueue
	if len(self.orderQueue) == self.maxOrderQueueLength:
	    for i in self.orderQueue:
		if abs(self.Strat.calcConsensus(event['headline'])) <= abs(self.Strat.calcConsensus(i['event']['headline'])) \
		or event['ticker'] == i['event']['ticker']:
		    return
	
	optionContract = self.createOptionContract(str(event['ticker']), direction)
	# If we cant find market data to create option contract
	if not optionContract:
	    print "Option contract creation failed skipping order"
	    return
	# We come up with the optionOrder but we mush also check to see if the market is liquid enough. 
	if not self.verifyOptionLiquidity(optionContract):
	    print "Option order not liquid, skipping order"
	    return
	optionOrder = self.createOrderBuy()

	# Put the order in the queue or kick out a crappier one if its max length
	if len(self.orderQueue) < self.maxOrderQueueLength:
	    self.orderQueue.append({'event':event, 'order':optionOrder, 'contract':optionContract})	
	    print "Order appended to queue ", optionContract.symbol, " ", optionContract.secType, " ", optionContract.expiry, " ", optionContract.right, " ", optionContract.strike, " ", " NumContracts: ", optionOrder.totalQuantity
	else:
	    for i in range(0, len(self.orderQueue)):
		if abs(self.Strat.calcConsensus(event['headline'])) > abs(self.Strat.calcConsensus(self.orderQueue[i]['event']['headline'])):
		    del self.orderQueue[i]
		    self.orderQueue.append({'event':event, 'order':optionOrder, 'contract':optionContract})	
		    print "Order appended to queue ", optionContract.symbol, " ", optionContract.secType, " ", optionContract.expiry, " ", optionContract.right, " ", optionContract.strike, " ", " NumContracts: ", optionOrder.totalQuantity
	# Update the order sizes now that the queue has changed
	self.updateOrderQueueOrderSizes()

    def getPortfolio(self):
	'''
	Returns list of triplets of current (contract, position in number of shares/contracts, market value of position)
	'''
	portfolioList = []
	# setup call back variables 
	self.callback.accountEnd = False
	#self.callback.portfolioContract = None
	#self.callback.portfolioPosition = None
	#self.callback.portfolioSecMarketValue = None

	self.tws.reqAccountUpdates(1, self.accountNumber)
	while (not self.callback.accountEnd):
	    self.callback.portfolioContract = None
	    self.callback.portfolioPosition = None
	    self.callback.portfolioSecMarketValue = None
	    max_wait = datetime.timedelta(seconds=60) + datetime.datetime.now()
	    while (self.callback.portfolioPosition is None or self.callback.portfolioContract is None or self.callback.portfolioSecMarketValue is None):
	        if datetime.datetime.now() > max_wait:
	            break
	    if self.callback.portfolioPosition is not None and self.callback.portfolioContract is not None and self.callback.portfolioSecMarketValue is not None:
	        myContract = Contract()
	        myContract.exchange = "SMART"
	        myContract.currency = "USD"
	        myContract.symbol = self.callback.portfolioContractSymbol
	        myContract.conId = self.callback.portfolioContractConId
	        myContract.secType = self.callback.portfolioContractSecType
	        myContract.strike = self.callback.portfolioContractStrike
	        myContract.expiry = self.callback.portfolioContractExpiry
	        myContract.right = self.callback.portfolioContractRight
	        myPosition = self.callback.portfolioPosition
		mySecMarketValue = self.callback.portfolioSecMarketValue
	        portfolioList.append((myContract, myPosition, mySecMarketValue))

	self.tws.reqAccountUpdates(0, self.accountNumber)
	return portfolioList


    def sellOut(self):
	'''
	Dump all positions
	'''
	# need to clear orderQueue regularly
	self.orderQueue = []
	# Data holder for positions
	portfolioList = self.getPortfolio()

	if len(portfolioList) == 0:
	    print "No sellout orders today"
	    self.invested = False
	    return

	# Get list of tickers that we want to get sold. Need to follow day pattern trade restrictions (>24 holding period)
	maxTransactionDatetime = (datetime.datetime.now() - datetime.timedelta(days=1, seconds=60)).strftime("%Y-%m-%d %H:%M:%S")	
	minTransactionDatetime = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S") 
	sql = '''SELECT DISTINCT(ord.symbol) FROM mchan.twsOrders ord 
		 INNER JOIN mchan.twsOrderStatus st 
		 ON ord.orderId = st.orderId 
		 WHERE st.orderStatus = 'Filled' 
		 AND st.receive_date < '%s' 
		 AND st.receive_date > '%s';''' % (maxTransactionDatetime, minTransactionDatetime)		
	sellTickerList = self.db.query(sql)

	orderList = []
	print "Sell Out orders:"
	for curContract, curPosition, curMarketSize in portfolioList:
	    if curPosition == 0:
		print curContract.symbol, ": zero size position, skipping"
		continue
	    if [curContract.symbol] not in sellTickerList:
		continue
	    curOrder = self.createOrderBuy()
	    curOrder.totalQuantity = int(curPosition)
	    curOrder.action = "SELL"
	    curOrder.sweepToFill = False
	    orderList.append([curContract, curOrder])
	    print curContract.symbol, " ", curOrder.totalQuantity
	for orders in orderList:
	    # Arguments are orderId, contract, and order 
	    self.tws.placeOrder(orders[1].orderId, orders[0], orders[1])
	    #pass
	print "Sell orders sent out!"	
	#self.invested = False

def FOWScanner(tradeMgr):
    fh1 = open('/home/mchan/git/Artemis/fowscanlog.txt', 'a', 0)
    fh2 = open('/home/mchan/git/Artemis/signal.txt', 'a', 0)
    fh1.write("Starting Session" + str(datetime.datetime.now()) + '\n')
    fh2.write("Starting Session" + str(datetime.datetime.now()) + '\n')
    pastEvents = []

    longStrat = strategy.LongEarningsGuidance()
    shortStrat = strategy.ShortEarningsGuidance()
    while(1):
	myTimer = datetime.datetime.now()
	# Housekeeping, buy-in, sell-out section
	if (myTimer.minute % 15 == 0 and myTimer.second == 0):
	    print "Artemis HeartBeat ", str(myTimer)
	if (myTimer.hour == 6 and myTimer.minute == 28):
	    # OK to run many times during this minute
	    tradeMgr.submitOrders()	
	if (myTimer.hour == 6 and (myTimer.minute == 45 or myTimer.minute == 46)):
	    tradeMgr.sellOut()
	    time.sleep(120)

	# Article Scanning Section
        if len(pastEvents) > 500:
    	    pastEvents = []
        events = fowscanner.scan()
        for row in events:
	    if row['id'] not in pastEvents:
	         pastEvents.append(row['id'])
		 recTime = datetime.datetime.now()
	         fh1.write(str(row) + "  RECV" + str(recTime) + "\n")
	         if len(row['ticker']) != 1:
		    continue
	         event = dict({'ticker':row['ticker'][0], 'classification':row['classification'], 'headline':row['headline']})
	         if longStrat.isEvent(event):
	            print row, "  RECV", str(recTime)
		    print "LONG the above event!"
		    print " PROCESSED", str(datetime.datetime.now())
		    fh2.write(str(row) + " LONG" + str(datetime.datetime.now()) + " RECV:" + str(recTime) + " PROCESSED: " + str(datetime.datetime.now()) + "\n") 
		    # Basic time checking
		    print "Event NYC time: ", str(stryDateTime), "   Recv NYC time: ", str(datetime.datetime.now() + datetime.timedelta(hours=3))
		    stryDateTime = datetime.datetime.strptime(row['release_datetime'], "%Y-%m-%d %H:%M:%S")
		    if datetime.datetime.now() + datetime.timedelta(hours=3) < stryDateTime + datetime.timedelta(minutes=10):
		        tradeMgr.processEvent(event, "LONG", recTime)
		    else:
			print "Story too stale skipping!"

	         elif shortStrat.isEvent(event):
	            print row, "  RECV", str(recTime)
		    print "SHORT the above event!"
		    print " PROCESSED", str(datetime.datetime.now())
		    fh2.write(str(row) + " SHORT" + str(datetime.datetime.now()) + " RECV:" + str(recTime) + " PROCESSED: " + str(datetime.datetime.now()) + "\n") 
		    stryDateTime = datetime.datetime.strptime(row['release_datetime'], "%Y-%m-%d %H:%M:%S")
		    print "Event NYC time: ", str(stryDateTime), "   Recv NYC time: ", str(datetime.datetime.now() + datetime.timedelta(hours=3))
		    if datetime.datetime.now() + datetime.timedelta(hours=3) < stryDateTime + datetime.timedelta(minutes=10):
		        tradeMgr.processEvent(event, "SHORT", recTime)
		    else:
			print "Story too stale skipping!"
		 else:
		    fh1.write(" PROCESSED: " + str(datetime.datetime.now())) 

def TimerDaemon(tradeMgr):
    print "TimerDaemon started"
    print tradeMgr
    # Get to the 30 minute mark
    while(datetime.datetime.now().minute != 30):
	time.sleep(1)
    # Now sleep every 30 min
    while(1):
	print str(datetime.datetime.now())
	time.sleep(1800)
	tradeMgr.run()

if __name__ == '__main__':

    tradeMgr = TradeManager()	
    FOWScanner(tradeMgr)


# Psuedo Code
# Wait for stories to come in
# When story reaches send out order
#  If order fails because of:
#       1. Wrong order settings (no contract found)
#             then: skip order
#       2. Market Closed
#             then:  Add order to queue.  Wait for market open, order a market on open order
#
#  If no active order and 930am has reached:
#       Buy all orders and wait until 330pm and sell
#
#
#  Sending out orders
#     1. reqMktData to get current price of stock <- Wait for IB response
#     2. Come up with in the money option details.  Variables:  In the money Strike, Expiry, Call/Put, 
#     3. reqContractDetails to get contractID,  <- Wait for IB response
#     4. reqMktData to get option price <- Wait for IB response 
#     5. reqAccountUpdates to see how much Cash <- Wait for IB response
#     6. calculate number of option contracts to buy
#     7. placeOrder()
