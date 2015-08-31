import urllib, urllib2, cookielib, re
from urllib2 import HTTPError, URLError
from httplib import IncompleteRead, BadStatusLine
from ssl import SSLError
from bs4 import BeautifulSoup
from time import gmtime, localtime, strftime
import sys
from datetime import datetime, date

theurl = "http://www.theflyonthewall.com/beta/news.php"
txheader =  {'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

def scan():

	# From 4pm to 6pm EST we will hit the server without Privoxy, we get 200ms response time. o'wise its 400ms
	mylocaltime = datetime.now()
	if mylocaltime.hour >= 13 and mylocaltime.hour <= 16:
	    cj = cookielib.CookieJar()
	    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	else:
	    proxy_support = urllib2.ProxyHandler({"http" : "127.0.0.1:8118"})
	    opener = urllib2.build_opener(proxy_support)

	try:
	    resp = opener.open(theurl)
	except HTTPError:
	    #print "HTTPError found"
	    return []
	except SSLError:
	    #print "SSLError found"
	    return []
	except URLError:
	    #print "URLError found"
	    return []
	
	# Parse the page response
	try:
	    soup = BeautifulSoup(resp.read())
	except IncompleteRead:
	    print "Incomplete Read"
	    return []
	except BadStatusLine:
	    print "BadStatusLine"
	    return []
	# Grab the necessary data
	events = []
	
	for i in soup.find_all('li'):
	    if i.has_key('id'):
	        if i['id'].startswith('li_'):
		    xvar = i
	            id = re.sub(r'li_', '', i['id'])
	            time = i.find(id="horaCompleta").string
	            tickers = []
		    headline = None
		    text = None
		    links = []
		    links_str = ""
	            for j in i.find_all(attrs={'onclick':re.compile("^searchSymbols")}):
	                  clean_ticker = re.sub(r'\(|\)|\+', '', j.string)
	                  tickers.append(clean_ticker)
	            if(i.find(attrs={'class':'Headline'})):
	                  headline = i.find(attrs={'class':'Headline'}).string
		    elif(i.find(attrs={'class':'withOutHeadline'})):
			  headline = i.find(attrs={'class':'withOutHeadline'}).string
			  text = i.find(attrs={'class':'withOutHeadline'}).string
	            if(i.find(attrs={'class':re.compile("^nw")})):
	                  text = i.find(attrs={'class':re.compile("^nw")}).get_text()
		    elif(i.find(attrs={'class':'pAlone'})):
			  text = i.find(attrs={'class':'pAlone'}).get_text()
	            if(i.find(attrs={'class':re.compile("^iconos")})):
	                  classification = i.find(attrs={'class':re.compile("^iconos")})['title']
		    for j in i.find_all('a'):
			  links.append(j.get('href'))
		    now = strftime("%Y-%m-%d %H:%M:%S", localtime())
		    tickers_str = ','.join(tickers)
		    links_str = ','.join(links)
		    # Cant find a headline or story
		    if (headline == None and text == None):
			  continue 
		    if (headline == None):
			  headline = text
		    event = dict({'id':id, 'release_datetime':time, 'classification':classification, 'ticker':tickers, 'headline':headline, 'story':text})
		    events.append(event)
		    id = None; tickers_str = None; classification = None; headline = None; text = None; 
	return events
	
	
