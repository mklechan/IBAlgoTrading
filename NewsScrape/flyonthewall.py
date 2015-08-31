import urllib, urllib2, cookielib, re
from bs4 import BeautifulSoup
from time import gmtime, localtime, strftime
import sys
from datetime import datetime, date

theurl = "http://www.theflyonthewall.com/beta/news.php"
theurl2 = "http://www.theflyonthewall.com/beta/paraDesarrollar/getNews.php"
loginurl = "http://www.theflyonthewall.com/login.php"
loginurl2 = "http://www.theflyonthewall.com/beta/paraDesarrollar/login.php"

username = ""
password = ""
txheader =  {'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}
data = {'username':username, 'password':password}

import dbutil

__homeserv = dbutil.db(h='127.0.0.1', schema='mchan')
__cursor = __homeserv.cursor


txdata = urllib.urlencode(data)
# Setup Cookie manager
cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
resp = opener.open(theurl)
resp = opener.open(loginurl2, txdata)
# Now get the unlocked data
try:
   resp2 = opener.open(theurl)
except urllib2.HTTPError, e:
    print 'The server couldn\'t fulfill the request.'
    print 'Error code: ', e.code
except urllib2.URLError, e:
    print 'We failed to reach a server.'
    print 'Reason: ', e.reason

# Parse the page response
soup = BeautifulSoup(resp2.read())
# Grab the necessary data

for i in soup.find_all('li'):
    if i.has_key('id'):
        if i['id'].startswith('li_'):
	    xvar = i
            id = re.sub(r'li_', '', i['id'])
            time = i.find(id="horaCompleta").string
            tickers = []
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
	    sql = """INSERT IGNORE INTO mchan.flyonthewall
		     VALUES (%i, '%s', '%s', '%s', '%s', '%s', '%s', '%s')""" \
		     % (int(id), time, now, tickers_str, classification, headline.replace("'","\\'").replace("theflyonthewall.com",""), text.replace("'", "\\'").replace("theflyonthewall.com",""), links_str)
	    if __cursor.execute(sql):
                print(id, time, classification, tickers, headline, text, links_str)
	    id = None; tickers_str = None; classification = None; headline = None; text = None; 
__homeserv.commit()


