# coding=utf-8
from string import Template
from datetime import *
import time
import urllib  
import urllib2  

period1 = date(2013, 9, 20)
preiod2 = date(2012, 9, 24)

period1.year

base_url = Template('http://ichart.finance.yahoo.com/table.csv?\
s=${stock}&d=${toMonth}&e=${toDay}&f=${toYear}&g=d&a=${fromMonth}&${fromDay}=12\
&c=${fromYear}&ignore=.csv')


def download_history_chart(base_url, stock_name,from_date,to_date):
	url = base_url.substitute(stock = stock_name, fromDay = from_date.day, fromMonth = from_date.month, 
		fromYear = from_date.year, toDay = to_date.day, toMonth = to_date.month, toYear = to_date.year)
	print url
	webFile = urllib2.urlopen(url)
	filename = stock_name+'.csv'
   	localFile = open(filename, 'w')
	localFile.write(webFile.read())

def main():
	download_history_chart(base_url, 'MMM', preiod2, period1)

if __name__ == "__main__":
    main()