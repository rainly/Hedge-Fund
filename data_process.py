# coding=utf-8
from string import Template
from datetime import *
import time
import urllib
import urllib2
import os
import json
from pprint import pprint
import csv
from stock import *
import collections
from sklearn import cross_validation,metrics,svm
from numpy import array
from sklearn.ensemble import RandomForestRegressor

node1 = date(2013, 9, 20)
node2 = date(2012, 9, 24)


period1 = {'start': node1, 'end': date.today(), 'name': 'p1'}
period2 = {'start': node2, 'end': node1, 'name': 'p1'}

periods = [period1, period2]

base_url = Template('http://ichart.finance.yahoo.com/table.csv?\
s=${stock}&d=${toMonth}&e=${toDay}&f=${toYear}&g=d&a=${fromMonth}&b=${fromDay}\
&c=${fromYear}&ignore=.csv')


def download_history_chart(base_url, stock_name, period):
    from_date = period['start']
    to_date = period['end']
    url = base_url.substitute(
        stock=stock_name, fromDay=from_date.day, fromMonth=from_date.month,
        fromYear=from_date.year, toDay=to_date.day, toMonth=to_date.month, toYear=to_date.year)
    print url
    webFile = urllib2.urlopen(url)
    if not os.path.exists(period['name']):
        os.makedirs(period['name'])
    filename = os.path.join(period['name'], stock_name + '.csv')
    #filename = './'+period['name']+'/'+stock_name+'.csv'
    localFile = open(filename, 'w')
    localFile.write(webFile.read())


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def trend_compare(stock1, stock2):
    if stock1['trend'] - stock2['trend'] > 0:
        return -1
    if stock1['trend'] - stock2['trend'] < 0:
        return 1
    return 0


def get_company_list(period):
    json_data = open(period['name'] + '_companies')
    data = json.load(json_data)
    json_data.close()
    return data[period['name']]


def download_period_stocks_charts(period, company_list):
    for company in data[period['name']]:
        download_history_chart(base_url, company, period)


def read_stock(period, stock_name):
    from_date = period['start']
    to_date = period['end']
    price_dict = {}
    trend_dict = {}
    filename = os.path.join(period['name'], stock_name + '.csv')
    with open(filename, 'rb') as csvfile:
        detailed_info = csv.DictReader(csvfile)
        for row in detailed_info:
            price_dict[datetime.strptime(row['Date'], '%Y-%m-%d').date()] = float(
                row['Adj Close'])
        previous = -1.0
        for single_date in daterange(from_date, to_date):
            if price_dict.has_key(single_date):
                if previous != -1.0:
                    trend_dict[single_date] = (
                        price_dict[single_date] - previous) / previous
                previous = price_dict[single_date]
    return price_dict, trend_dict


def get_trend_rank(trend_list):
    rank_list = []
    sorted_trend_list = sorted(trend_list, cmp=trend_compare)
    for i in xrange(len(sorted_trend_list)):
        rank_list.append({'name': sorted_trend_list[i]['name'], 'rank': i + 1})
    return rank_list


def get_accumulate_trend_rank(current_price_dict, previous_price_dict, days):
    accumulate_trend_list = []
    for k in current_price_dict.keys():
        trend = (current_price_dict[k] - previous_price_dict[k]) / previous_price_dict[k]
        accumulate_trend_list.append({'name': k,
                                      'trend': trend})
    return sorted(accumulate_trend_list, cmp=trend_compare)


def get_period_stocks_info(period, company_list):
    #company_list = get_company_list(period)
    date_stocks_dict = {}
    for company in company_list:
        price_dict, trend_dict = read_stock(period, company)
        for single_date in trend_dict.keys():
            if not date_stocks_dict.has_key(single_date):
                date_stocks_dict[single_date] = {}
                date_stocks_dict[single_date]['price'] = {}
                date_stocks_dict[single_date]['trend'] = []
                #date_stocks_dict[single_date]['trend_spread'] = {}
            #date_stocks_dict[single_date]['price'].append(
            #    {'name': company, 'price': price_dict[single_date]})
            date_stocks_dict[single_date]['price'][company] = price_dict[single_date]
            date_stocks_dict[single_date]['trend'].append(
                {'name': company, 'trend': trend_dict[single_date]})
    odered_date_stocks_dict = collections.OrderedDict(
        sorted(date_stocks_dict.items()))
    for single_date in odered_date_stocks_dict.keys():
        odered_date_stocks_dict[single_date]['rank'] = get_trend_rank(
            odered_date_stocks_dict[single_date]['trend'])
        # print odered_date_stocks_dict[single_date]['rank']
    return odered_date_stocks_dict


def generate_csv(odered_date_stocks_dict, company_list, period):
    field_list = []
    stock_dict = {}
    stock_list = []
    field_list.append('stock_code')
    for day in odered_date_stocks_dict.keys():
        field_list.append(day.isoformat())
    for company in company_list:
        stock_dict[company] = {}
    for single_date in odered_date_stocks_dict.keys():
        for stock_rank in odered_date_stocks_dict[single_date]['rank']:
            stock_dict[stock_rank['name']][
                single_date.isoformat()] = stock_rank['rank']
    for stock_name in stock_dict.keys():
        stock_dict[stock_name]['stock_code'] = stock_name
        stock_list.append(stock_dict[stock_name])
    filename = './trend_rank/' + period['name'] + '.csv'
    f = open(filename, 'wb')
    f.write(u'\ufeff'.encode('utf8'))
    dict_writer = csv.DictWriter(f, field_list)
    dict_writer.writer.writerow(field_list)
    dict_writer.writerows(stock_list)


def get_trend_spread(odered_date_stocks_dict, company_list, period, days):
    high_count ,low_count, spread_after_count, spread_after_acc = 0, 0, 0, 0.0
    date_stocks_list = odered_date_stocks_dict.items()
    list_length = len(date_stocks_list)
    trend_spread_list = []
    for i in xrange(len(date_stocks_list)):
        if (i - days + 1) > 0 and i+1 < len(date_stocks_list):
            trend_list = get_accumulate_trend_rank(
                date_stocks_list[i][1]['price'],
                date_stocks_list[i - days + 1][1]['price'], days)
            high_today = date_stocks_list[i][1]['price'][trend_list[0]['name']]
            high_after = date_stocks_list[i+1][1]['price'][trend_list[0]['name']]
            low_today = date_stocks_list[i][1]['price'][trend_list[-1]['name']]
            low_after = date_stocks_list[i+1][1]['price'][trend_list[-1]['name']]
            high_trend = (high_after - high_today)/high_today*100
            low_trend = (low_after-low_today)/low_today*100
            trend_spread_list.append({'date': date_stocks_list[i][0].isoformat(),
                                    'trend_spread': (trend_list[0]['trend'] - trend_list[-1]['trend']) * 100,
                                    'high':trend_list[0]['name'],
                                    'high_today': high_today,
                                    'high_after': high_after,
                                    'high_trend': high_trend,
                                    'low':trend_list[-1]['name'],
                                    'low_today': low_today,
                                    'low_after': low_after,
                                    'low_trend': low_trend,
                                    'spread_after': low_trend - high_trend})
            if high_today > high_after:
                high_count += 1
            if low_today < low_after:
                low_count += 1
            if low_trend - high_trend > 0:
                spread_after_count += 1
            spread_after_acc += low_trend - high_trend
    print 'days : ' + str(days)+ ' high_count : ' + str(high_count) + ' low_count : ' + str(low_count) + \
    ' spread_after_count : ' + str(spread_after_count)+' spread_after_acc : ' + str(spread_after_acc/len(date_stocks_list))
    generate_trend_spread_csv(trend_spread_list, period, days)


def generate_trend_spread_csv(trend_spread_list, period, days):
    field_list = ['date', 'trend_spread','high','high_today','high_after','high_trend',
    'low','low_today','low_after','low_trend','spread_after']
    filename = './trend_spread/'+period['name'] + '_spread_'+ str(days) + '.csv'
    f = open(filename, 'wb')
    f.write(u'\ufeff'.encode('utf8'))
    dict_writer = csv.DictWriter(f, field_list)
    dict_writer.writer.writerow(field_list)
    dict_writer.writerows(trend_spread_list)

def genetate_feature():
    pass

def main():
    # get_company_list(period1)
    #price_dict, trend_dict = read_stock(period1, "MMM")
    #from_date = period1['start']
    #to_date = period1['end']
    # for single_date in daterange(from_date, to_date):
    #    if trend_dict.has_key(single_date):
    #        print trend_dict[single_date]
    company_list = get_company_list(period1)
    odered_date_stocks_dict = get_period_stocks_info(period1, company_list)
    generate_csv(odered_date_stocks_dict, company_list, period1)
    for day in xrange(2,10):
        get_trend_spread(odered_date_stocks_dict, company_list, period1, day)
    print "finished!"
    #date_stocks_list = odered_date_stocks_dict.items()
    # for i in xrange(len(date_stocks_list)):
    #    print date_stocks_list[i][0]
    
if __name__ == "__main__":
    main()
