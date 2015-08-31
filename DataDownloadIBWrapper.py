from datetime import datetime, timedelta
import time, sys
import pdb

sys.path.append('/home/mchan/git/Artemis/util')
import dbutil

from swigibpy import EWrapper, Contract, ContractDetails

###

tickTypeHash = {0:"bid size", 1:"bid price", 2:"ask price", 3:"ask size", 4:"last price", \
	5:"last size", 6:"high", 7:"low", 8:"volume", 9:"close price", 10:"bid option computation", \
	11:"ask option computation",  12:"last option computation", 13:"model option computation", \
	14:"open tick", 15:"low 13 week", 16:"high 13 week", 17:"low 26 week", 18:"high 26 week", \
	19:"low 52 week", 20:"high 52 week", 21:"avg volume", 22:"open interest", \
	23:"option historical vol", 24:"option implied vol", 25:"option bid exch", \
	26:"option ask exch", 27:"option call open interest", 28:"option put open interest", \
	29:"option call volume", 30:"option put volume", 31:"index future premium", \
	32:"bid exch", 33:"ask exch", 37:"mark price", 45:"last timestamp", \
	46:"shortable", 47:"fundamental ratios", 48:"rt volume", 49:"halted", \
	53:"cust option computation", 54:"trade count", 55:"trade rate", \
	56:"volume rate"}

wrapper_db = dbutil.db(h='127.0.0.1', schema='mchan')
wrapper_db.execute('SET autocommit=0;')
class ArtemisIBWrapper(EWrapper):
    '''Callback object passed to TWS, these functions will be called directly
    by TWS.

    '''
    def deltaNeutralValidation(self, reqId, underComp):
	pass

    def marketDataType(self, reqid, marketDataType):
	print "Market Data Type: ", reqId, " ", marketDataType

    def winError(self, mesg, errorCode):
	print "Win error message: ", mesg, " ", errorCode

    def error(self, orderId, errorCode, errorString):
	print orderId, " ", errorCode, " ", errorString

    def nextValidId(self, orderId):
        '''Always called by TWS but not relevant for our example'''
	self.myNextValidId = orderId
	print "Next Valid Id: ", orderId

    def openOrderEnd(self):
        '''Always called by TWS but not relevant for our example'''
	print "Open Order end:"

    def tickEFP(self, tickerId, tickType, basisPoints, formattedBasisPoints, totalDividends, holdDays, futureExpiry, dividendImpact, dividendsToExpiry):
	pass

    def openOrder(self, orderId, contract, order, orderState):
	print "Open Order status:  Order Id: ", orderId, " Order State: ", orderState.status

    def managedAccounts(self, openOrderEnd):
        '''Called by TWS but not relevant for our example'''
        pass

    def historicalData(self, reqId, date, open, high,
                       low, close, volume,
                       barCount, WAP, hasGaps):

        if date[:8] == 'finished':
	    wrapper_db.commit()
	    wrapper_db.execute("COMMIT;")
	    wrapper_db.execute('SET autocommit=0;')
	    self.histTickerID = None
            print "History request complete"
        else:
	    try:
                date_str = datetime.strptime(date, "%Y%m%d").strftime("%d %b %Y")
	    except:
                date_str = (datetime.strptime(date, "%Y%m%d  %H:%M:%S") + timedelta(hours=3)).strftime("%d %b %Y %H:%M:%S")
                date = datetime.strptime(date, "%Y%m%d  %H:%M:%S") + timedelta(hours=3)

	    wrapper_db.execute('''INSERT IGNORE INTO mchan.pricing1Min VALUES ("%s", "%s", "%s", %i, %f, %i);''' %  (self.histTickerID, date.date().isoformat(),\
                                  date.time().isoformat(), 0, close, volume))
            print ( "%s %s - Open: %s, High: %s, Low: %s, Close: " +
                    "%s, Volume: %d" ) % (self.histTickerID, date_str, open, high, low, close, volume)

    def tickOptionComputation(self, reqId, tickType, impliedVol, delta, 
			      optPrice, pvDiv, gamma, vega, theta, undPrice):
	tickTypeStr = tickTypeHash[tickType]
	print ("Option Data  -Request ID: %s  -TickType: %s  -Implied Vol: %f" +
	       " -Delta: %f  -Option Price: %f  -PV Dividend: %f  -Gamma: %f  -Vega: %f  -Theta: %f" +
	       " -Underlying Price: %f") % (reqId, tickTypeStr, impliedVol, delta, optPrice, pvDiv, gamma, vega, theta, undPrice)

    def tickPrice(self, reqId, tickType, price, canAutoExecute):
	tickTypeStr = tickTypeHash[tickType]
	if tickType == 2:
	    self.askPrice = price
	elif tickType == 4:
	    self.lastPrice = price
	elif tickType == 9:
	    self.closePrice = price 
	print ("Pricing Data -Request ID: %s  -TickType: %s  -Price: %s  -CanAutoExecute: %s") % (reqId, tickTypeStr, price, canAutoExecute) 

    def tickGeneric(self, reqId, tickType, value):
	tickTypeStr = tickTypeHash[tickType]
	print ("TickGeneric Data -Request ID: %s  -TickType: %s  -Value: %s") % (reqId, tickTypeStr, value)

    def tickSize(self, reqId, field, size):
	fieldStr = tickTypeHash[field]
	print ("TickSize Data -Request ID: %s  -TickType: %s  -Size: %s") % (reqId, fieldStr, size)
		
    def tickSnapshotEnd(self, reqId):
	self.tickDataEnd = True
	print "Tick Data end"

    def tickString(self, reqId, tickType, value):
	tickTypeStr = tickTypeHash[tickType]
	print ("TickString Data -Request ID: %s  -TickType: %s  -Value: %s") % (reqId, tickTypeStr, value)

    def contractDetails(self, reqId, conDetails):
	print ("Contract Details Recieved")
	print "Options Summary: ContractID: ", conDetails.summary.conId, " Exchange: ", conDetails.summary.exchange, " Trading Hours: ",\
		 conDetails.tradingHours, " Strike: ", conDetails.summary.strike, " Multiplier: ", conDetails.summary.multiplier, \
                 " Expiry: ", conDetails.summary.expiry, " Right: " , conDetails.summary.right, " Currency: ", conDetails.summary.currency
	self.contractDetailsData = conDetails
	self.conId = conDetails.summary.conId
	self.exchange = conDetails.summary.exchange
	self.tradingHours = conDetails.tradingHours
        self.strike = conDetails.summary.strike
	self.Strikes.append(conDetails.summary.strike)
	self.StrikesHash[conDetails.summary.strike] = (conDetails.summary.conId, conDetails.summary.multiplier)
	self.multiplier = conDetails.summary.multiplier
	self.expiry = conDetails.summary.expiry
	self.right = conDetails.summary.right
	self.currency = conDetails.summary.currency

    def contractDetailsEnd(self, reqId):
	self.contractDataEnd = True
	print ("Contract Details End")

    def updateAccountValue(self, key, value, currency, account):
	if key == "BuyingPower":
	   self.buyingPower = value
	   # INITIALIZE
	   self.portfolioData = []
	#if key in ["BuyingPower", "AccountType", "CashBalance", "TotalCashBalance", "TotalCashValue"]:
	#   print key, " ", value
	print key, " ", value

    def updateAccountTime(self, timestmp):
	print timestmp

    def accountDownloadEnd(self, account):
	self.accountEnd = True
	print "Account Download End ", account

    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
	self.portfolioContractSymbol = contract.symbol
	self.portfolioContractSecType = contract.secType
	self.portfolioContractRight = contract.right
	self.portfolioContractExpiry = contract.expiry
	self.portfolioContractStrike = contract.strike
	self.portfolioContractConId = contract.conId
	self.portfolioSecMarketValue = marketValue
	self.portfolioPosition = position
	self.portfolioContract = contract
	print "Contract: ", contract.symbol, " ", contract.secType, " Position: ", position, " Market Value: ", marketValue, \
	     " Market Price: ", marketPrice, " averageCost: ", averageCost, " Unrealized PnL: ", unrealizedPNL, \
	     " Realized PnL: ", realizedPNL, " Account Name: ", accountName 
	try:
	    self.portfolioData.append({'symbol':contract.symbol, 'secType':contract.secType, 'right':contract.right, 'expiry':contract.expiry, \
					'strike':contract.strike, 'conId':contract.conId, 'marketValue':marketValue, 'Position':position})
	except:
	    pass

    def connectionClosed(self):
	print "TWS Connection closed at: ", str(datetime.now())

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld):
	#myNow = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
	#wrapper_db.execute('''INSERT INTO mchan.twsOrderStatus VALUES (%i, "%s", %i, %i, %i, %f, "%s");''' %  (orderId, status, clientId, filled, remaining, avgFillPrice, myNow))
	#wrapper_db.commit() 
	print "Order Status Alert, STATUS: ", status, " Filled: ", filled, " Remaining: ", remaining, " Avg Fill Price: ", avgFillPrice, \
		" PermId: ", permId, " ParentId: ", parentId, " Last fill Price: ", lastFillPrice, " Client Id: ", clientId, " Why Held: ", whyHeld
	self.orderState = status

    def execDetails(self, orderId, contract, execution):
	pass 

    def execDetailsEnd(self, requestId):
	pass

    def updateMktDepth(self, tickerId, position, operation, side, price, size):
	print "Market Depth"
	print "Ticker ID: ", tickerId, " Position: ", position, " Operation: ", operation, " Side: ", side, " Price: ", price, " Size: ", size
    
    def updateMktDepthL2(self, tickerId, position, marketMaker, operation, side, price, size):
	print "L2 Market Depth"
	print "Ticker ID: ", tickerId, " Market Maker: ", marketMaker," Position: ", position, " Operation: ", operation, " Side: ", side, " Price: ", price, " Size: ", size

    def updateNewsBulletin(self, msgId, msgType, message, origExchange):
	pass

    def receiveFA(self, faDataType, XML):
	pass
 
    def bondContractDetails(self, reqId, contractDetails):
	pass

    def scannerParameters(self, xml):
	pass

    def scannerData(self, reqId, rank, contractDetails, distance, benchmark, projection):
	pass

    def scannerDataEnd(self, reqId):
	pass
  
    def realtimeBar(self, reqId, time, open, high, low, close, volume, wap, count):
	pass

    def currentTime(self, time):
	pass

    def fundamentalData(self, reqId, data):
	pass

 
