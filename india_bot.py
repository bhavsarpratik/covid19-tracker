"""
Author: Pratik Bhavsar
Github: https://github.com/bhavsarpratik/covid19-tracker
"""

import numpy as np
import pandas as pd
import requests
import lxml.html as lh

import json, time

from utils import get_relative_date, TelegramMessenger, get_clean_table

data_url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSc_2y5N0I67wDU38DjDh35IZSIS30rQf7_NYZhtYYGU1jJYT6_kDx4YpF-qw0LSlGsBYP8pqM_a1Pd/pubhtml#'


def get_data():
    page = requests.get(data_url)
    doc = lh.fromstring(page.content)
    tr_elements = doc.xpath('//*[@id="1896310216"]/div/table/tbody')
    rows=[]
    #For each row, store each first element (header) and an empty list
    for t in tr_elements[0]:
        row = [x.text_content() for x in t.findall('td')[:-1]]
        rows.append(row)

    df = pd.DataFrame(rows[1:], columns=rows[0]).replace('', None).dropna().drop_duplicates()
    df[['Confirmed', 'Recovered', 'Deaths', 'Active']] = df[['Confirmed', 'Recovered', 'Deaths', 'Active']].apply(pd.to_numeric)
    return df


def get_newcases_time_series():
    url = 'https://api.covid19india.org/data.json'
    page = requests.get(url)
    df = pd.DataFrame(json.loads(page.content)[
                      'cases_time_series']).dropna().set_index('date')
    df = df.iloc[-10:, :1]
    # df.loc["Total"] = df.sum()
    df.columns = ['NewCases']
    df = df.astype(int)
    df['%Change'] = df.NewCases.pct_change()*100
    df = df[-7:]
    df['%Change'] = df['%Change'].astype(int).round(2).apply(lambda x: f'{x}%')
    return df


def get_total_time_series():
    url = 'https://api.covid19india.org/data.json'
    page = requests.get(url)
    df = pd.DataFrame(json.loads(page.content)[
                      'cases_time_series']).dropna().set_index('date')
    df = df[['totalconfirmed']].rename(
        {'totalconfirmed': 'TotalCases'}, axis=1)
    df = df.iloc[-10:, :1]
    df = df.astype(int)
    df['%Increase'] = df.TotalCases.pct_change()*100
    df = df[-7:]
    df['%Increase'] = df['%Increase'].astype(
        int).round(2).apply(lambda x: f'{x}%')
    return df


bot = TelegramMessenger('india-config.json')
curr_date = get_relative_date(zone='Asia/Kolkata', format='%Y-%m-%d')

try:
    df = pd.read_csv(f'data/{curr_date}.csv')
except:
    df = get_data()
    df.to_csv(f'data/{curr_date}.csv', index=False)

df = df[['State', 'Confirmed']]
total_cases = df.iloc[0, 1]

while True:
    df_new = get_data()
    curr_time = get_relative_date(zone='Asia/Kolkata', format='%Y-%m-%d %H:%M')
    curr_time_message = f'Case update at: {curr_time}'
    
    if total_cases != df_new.iloc[0, 2]:  # checking total case change
        total_cases = df_new.iloc[0, 2]  # updating total case 
        df_update = df_new
        df_update = df_update.merge(
            df.rename({'Confirmed': 'old_confirmed'}, axis=1))
        df_update['New'] = df_update['Confirmed'] - df_update['old_confirmed']
        df_update = df_update[df_update['Confirmed'] != 0]
        df_update = df_update[['State', 'New',
                               'Confirmed', 'Deaths']].sort_values(['New', 'Confirmed'], ascending=False)
        
        df_update.to_csv(f'data/update-{curr_date}.csv', index=False)
        
        df_update.State = df_update.State.apply(lambda x: x[:8])
        df_update = df_update.rename({'Confirmed': 'Case'}, axis=1).set_index('State')

        message = get_clean_table(df_update)

        bot.send_message(message)
    else:
        message = 'No new cases'

    print(curr_time_message)
    print(message)

    date = get_relative_date(zone='Asia/Kolkata', format='%Y-%m-%d')
    if date != curr_date:
        time.sleep(3600*6)
        try:
            message = get_clean_table(get_newcases_time_series())
            bot.send_message(message)
            message = get_clean_table(get_total_time_series())
            bot.send_message(message)
        except:
            print('API failed')
        bot.send_message(f'Starting update for {curr_date} IST. Checks for update every 30 minutes.')
        df = df_new[['State', 'Confirmed']]
        curr_date = date
        df.to_csv(f'data/{curr_date}.csv', index=False)
    
    time.sleep(1800)



