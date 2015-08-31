import re
import sys
sys.path.append('/home/mchan/git/Artemis/util')
import dbutil

class Strategy(object):
    """
    Strategy class to define enter and exit points given a ticker, and event headline from theflyonthewall.com
    """
    def __init__(self):
	self.rank = None
	self.db = dbutil.db(h='127.0.0.1', schema='mchan')
        self.cursor = self.db.cursor

    def epsParse(self, value):
	if value == None or value == '':
	    return
        mult = -1 if re.search(r'\(', value) else 1
        divider = 100 if re.search(r'c', value) else 1
        mult = 1000*mult if re.search(r'B', value) else mult
        scrubbed = re.sub(r'[^0-9.]', '', value)
	try:
            return mult * float(scrubbed)/divider
	except ValueError, e:
	    print "ValueError ", e
	    return
            
    def earningsPerformance(self, actual, expected):
        mult = -1 if actual < expected else 1
        expected = expected if expected != 0 else 0.0001
        return mult * abs( (actual - expected) / expected)


    def calcConsensus(self, Headline):
	regex = re.compile('\d+c|\(\d+c\)|\(\$\d+.\d*[MB]*\)|\$\d+.\d*[MB]*|[cC]onsensus|from|estimate|outlook|vs\.')
	HeadlineValues = regex.findall(Headline)
	#print HeadlineValues
	parsedHeadline = []
	#print parsedHeadline
	for i in range(0, len(HeadlineValues)):
            if re.search(r'[cC]onsensus|from|estimate|outlook|vs\.', HeadlineValues[i]):
                if i+1 <= len(HeadlineValues)-1:
                    parsedHeadline.append(HeadlineValues[i+1])
		    break
            else:
                parsedHeadline.append(HeadlineValues[i])
	values = [self.epsParse(value) for value in parsedHeadline]	
	#print values
	if len(values) == 2:
            performance = self.earningsPerformance(values[0], values[1])
	    return performance
	elif len(values) == 3:
            lowActual = values[0]
            highActual = values[1]
            meanActual = (lowActual + highActual) / 2
            performance = self.earningsPerformance(meanActual, values[2])
	    return performance
	else:
	    return False


class LongEarningsGuidance(Strategy):
    """
    This strategy goes for earnings forecast surprises (headline contains 'sees') of greater than 3%
    Market cap of company must be < 5000M and > 500M
    Must have a  eq_region_rank of > 10
    Headline must not contain test with 'c)' since we do not want negative earnings companies
    Headline must not contain 'adjusted'
    Headline must contain 'consensus' and 'see'
    """

    def __init__(self):
	#Initialize the super class so variables are available
	Strategy.__init__(self)
	self.rank = 0
	self.surprise_min = 0.03
	self.marketcap_min = 500  # in millions
	self.marketcap_max = 5000
	self.eqscore_min = 7 

	
    def isEvent(self, Event):
        """
        Event is a dictionary with keys 'ticker', 'classification', 'headline'
	Function will return True/False
	"""
	hline = Event['headline']
	if Event['classification'] != 'Earnings':
	    return False
	# All conditions for allowing based on headline
	if not re.search(r'see|[cC]onsensus|rais|affirm|prior|estimate|outlook|from', hline) \
	or re.search(r'c\)|adjusted|report|says', hline):
	    return False

	# Must have either "consensus" or "from"
	if not re.search(r'[cC]onsensus|from', hline):
	    return False
 
	# Calculate the consensus eps surprise	
	#print self.calcConsensus(hline)
	if self.calcConsensus(hline) == False or self.calcConsensus(hline) < self.surprise_min:
	    return False
	#print "High enough outperform"
	# Now check some requirements that can only be found in sql tables, like market cap, eq score	
	sql = """SELECT s.market_cap_usd_mm FROM mchan.security_price s
		 INNER JOIN mchan.mapping m
		 ON m.security_id = s.security_id
		 WHERE m.ticker = '%s'
		 ORDER BY as_of_date DESC
		 LIMIT 1;""" % Event['ticker']
	marketcap = self.db.query(sql)
	try:
	    test = marketcap[0][0]
	except:
	    print "Cant get market cap for" , Event['ticker']
	    return False
	if marketcap[0][0] < self.marketcap_min or marketcap[0][0] > self.marketcap_max:
	    return False

	#print "Good marketcap"
	
	sql = """SELECT s.eq_region_rank FROM mchan.s_daily s
		 INNER JOIN mchan.mapping m
		 ON m.security_id = s.security_id
		 WHERE m.ticker = '%s'
		 ORDER BY as_of_date DESC
		 LIMIT 1;""" % Event['ticker']
	eqscore = self.db.query(sql)
	#print "EQ score is: " , eqscore[0][0]
	if eqscore[0][0] < self.eqscore_min:
	    return False 	
	#print "Good eq score"
        # We've made it! All conditions met, return True
	#print "Result is True LONG", Event
	return True 

    
class ShortEarningsGuidance(Strategy):
    """
    This strategy goes for earnings forecast surprises (headline contains 'sees') of worse than -5% 
    Market cap of company must be < 2000M and > 500M
    Must have a  eq of < 50
    Headline must contain 'consensus' and 'see'
    """

    def __init__(self):
	#Initialize the super class so variables are available
	Strategy.__init__(self)
	self.rank = 0
	self.surprise_max = -0.05
	self.marketcap_min = 500  # in millions
	self.marketcap_max = 2000
	self.eqscore_max = 75
#	self.eqscore_max = 50 

    def isEvent(self, Event):
        """
        Event is a dictionary with keys 'ticker', 'classification', 'headline'
	Function will return True/False
	"""
	hline = Event['headline']
	if Event['classification'] != 'Earnings':
	    return False
	# All conditions for allowing based on headline
	if not re.search(r'see|[cC]onsensus|lower|cuts|prior|outlook|from|estimate', hline):
	    return False
	if re.search(r'report|says', hline):
	    return False

	# Must have either "consensus" or "from"
	if not re.search(r'[cC]onsensus|from', hline):
	    return False

	# Calculate the consensus eps surprise	
	if self.calcConsensus(hline) == False or self.calcConsensus(hline) > self.surprise_max:
	    return False
	#print "High enough outperform"
	# Now check some requirements that can only be found in sql tables, like market cap, eq score	
	sql = """SELECT s.market_cap_usd_mm FROM mchan.security_price s
		 INNER JOIN mchan.mapping m
		 ON m.security_id = s.security_id
		 WHERE m.ticker = '%s'
		 ORDER BY as_of_date DESC
		 LIMIT 1;""" % Event['ticker']
	marketcap = self.db.query(sql)
	try:
	    test = marketcap[0][0]
	except:
	    print "Cant get market cap for" , Event['ticker']
	    return False
	if marketcap[0][0] < self.marketcap_min or marketcap[0][0] > self.marketcap_max:
	    return False

	#print "Good marketcap"
	
	sql = """SELECT s.eq_region_rank FROM mchan.s_daily s
		 INNER JOIN mchan.mapping m
		 ON m.security_id = s.security_id
		 WHERE m.ticker = '%s'
		 ORDER BY as_of_date DESC
		 LIMIT 1;""" % Event['ticker']
	eqscore = self.db.query(sql)
	#print "EQ score is: " , eqscore[0][0]
	if eqscore[0][0] > self.eqscore_max:
	    return False 	
	#print "Good eq score"
        # We've made it! All conditions met, return True
	#print "Result is True SHORT", Event
	return True
