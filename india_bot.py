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


def get_data():
    url = 'https://api.covid19india.org/data.json'
    page = requests.get(url)
    df = pd.DataFrame(json.loads(page.content)['statewise'])
    df.state = df.state.apply(lambda x: x[:6])
    df = df.set_index('state').iloc[:, :6]
    df = df[df.deltaconfirmed != '0'].rename(
        {'active': 'Active', 'confirmed': 'Total', 'deaths': 'Deaths', 'deltaconfirmed': 'New'}, axis=1)
    return df.astype(int).sort_values(['New', 'Total'], ascending=False)[['New', 'Total', 'Deaths']]


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

total_cases = df.iloc[0, 1]

while True:
    try:
        df_new = get_data()

        curr_time = get_relative_date(zone='Asia/Kolkata', format='%Y-%m-%d %H:%M')
        curr_time_message = f'Case update at: {curr_time}'
        
        if total_cases != df_new.iloc[0, 1]:  # checking total case change
            total_cases = df_new.iloc[0, 1]  # updating total case 
            df_update = df_new
            df_update.to_csv(f'data/update-{curr_date}.csv', index=False)
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
            bot.send_message(f'Starting update for {curr_date} IST. Checks for update every hour.')
            df = df_new
            curr_date = date
            df.to_csv(f'data/{curr_date}.csv', index=False)
        
        time.sleep(3600)
    except:
        time.sleep(60)



