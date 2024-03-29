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
from numpy import array,asarray,sqrt
from sklearn.ensemble import RandomForestRegressor,RandomForestClassifier



node0 = date(2014, 3, 20)
node1 = date(2013, 9, 20)
node2 = date(2012, 9, 24)

period0 = {'start': node0, 'end': date.today(), 'name': 'p0'}
period1 = {'start': node1, 'end': node0, 'name': 'p1'}
period2 = {'start': node2, 'end': node1, 'name': 'p2'}

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
    json_data = open('companies')
    data = json.load(json_data)
    json_data.close()
    return data[period['name']]


def download_period_stocks_charts(period, company_list):
    for company in company_list:
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

def genetate_feature(odered_date_stocks_dict, company_list, period,is_for_eval):
    feature_list = []
    target_list = []
    stock_dict = {}
    count = 0
    for company in company_list:
        stock_dict[company] = []
    for single_date in odered_date_stocks_dict.keys():
        for stock_rank in odered_date_stocks_dict[single_date]['rank']:
            stock_dict[stock_rank['name']].append(stock_rank['rank'])
    for stock_name in stock_dict.keys():
        rank_list = stock_dict[stock_name]
        for i in xrange(len(rank_list)):
            if i>3 :
                if is_for_eval:
                    avg = (rank_list[i-4]+rank_list[i-3]+rank_list[i-2]+rank_list[i-1])/4.0
                    if (avg>22 or avg<8):
                        feature_list.append([int(rank_list[i-4]/5),int(rank_list[i-3]/5),
                            int(rank_list[i-2]/5),int(rank_list[i-1]/5)]) 
                        target_list.append(rank_list[i])
                        count+=1
                else:
                    feature_list.append([int(rank_list[i-4]/5),int(rank_list[i-3]/5),
                            int(rank_list[i-2]/5),int(rank_list[i-1]/5)]) 
                    target_list.append(rank_list[i])
                    count+=1
    print count
    return feature_list,target_list


def buildForest(feature_list, target_list):
    rf = RandomForestRegressor(n_estimators=50)
    clf= rf.fit(feature_list, target_list)
    return rf,clf

def eval_forest(rf, feature_list, target_list):
    scores=cross_validation.cross_val_score(rf,asarray(feature_list),asarray(target_list),score_func=metrics.mean_squared_error)
    print sqrt(scores)

def evaluate(clf,feature_list,target_list):
    sum = 0.0
    for i in xrange(len(feature_list)):
        rank = round(clf.predict(feature_list[i])[0])
        print(feature_list[i])
        print (str(target_list[i])+" "+str(rank))
        sum+=(rank - target_list[i])**2
    print sqrt(sum/float(len(target_list)))

def get_avg_RMSE(clf,odered_date_stocks_dict):
    pass
def main():
    # get_company_list(period1)
    #price_dict, trend_dict = read_stock(period1, "MMM")
    #from_date = period1['start']
    #to_date = period1['end']
    # for single_date in daterange(from_date, to_date):
    #    if trend_dict.has_key(single_date):
    #        print trend_dict[single_date]
    
    p1_company_list = get_company_list(period1)
    p1_ordered_date_stocks_dict = get_period_stocks_info(period1, p1_company_list)
    p2_company_list = get_company_list(period2)
    p2_ordered_date_stocks_dict = get_period_stocks_info(period2, p2_company_list)
    p0_ordered_date_stocks_dict = get_period_stocks_info(period0, p1_company_list)
    #generate_csv(p1_ordered_date_stocks_dict, p1_company_list, period1)
    #for day in xrange(2,10):
    #    get_trend_spread(p1_ordered_date_stocks_dict, p1_company_list, period1, day)
    p1_feature_list,p1_target_list = genetate_feature(p1_ordered_date_stocks_dict, p1_company_list, period1, False)
    p2_feature_list,p2_target_list = genetate_feature(p2_ordered_date_stocks_dict, p2_company_list, period2, False)
    p0_feature_list,p0_target_list = genetate_feature(p0_ordered_date_stocks_dict, p1_company_list, period0, True)

    feature_list = p1_feature_list + p2_feature_list
    target_list = p1_target_list + p2_target_list
    rf,clf = buildForest(feature_list, target_list)
    eval_forest(rf, feature_list, target_list)
    evaluate(clf,p0_feature_list,p0_target_list)
    print "finished!"
    #date_stocks_list = odered_date_stocks_dict.items()
    # for i in xrange(len(date_stocks_list)):
    #    print date_stocks_list[i][0]
    
    #download_period_stocks_charts(period0,get_company_list(period1))
    #download_period_stocks_charts(period1,get_company_list(period1))
    #download_period_stocks_charts(period2,get_company_list(period2))
    
if __name__ == "__main__":
    main()
