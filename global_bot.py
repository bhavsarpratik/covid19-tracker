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
    url = 'https://www.worldometers.info/coronavirus'
    page = requests.get(url)
    doc = lh.fromstring(page.content)
    tr_elements = doc.xpath('//*[@id="main_table_countries_today"]/tbody[1]')
    rows = []
    #For each row, store each first element (header) and an empty list
    for t in tr_elements[0]:
        row = [x.text_content() for x in t.findall('td')[:-1]]
        rows.append(row)

    columns = ['Country', 'Cases', 'New', 'Deaths',
               'New Deaths', 'Recovered', 'Active', 'x', 'x', 'x', 'x', 'x']
    df = pd.DataFrame(rows, columns=columns).iloc[:, :5].fillna(0)
    df = df.replace('  ', '').replace(' ', '').replace(',', '', regex=True).replace('', 0)
    df.dropna(inplace=True)

    for col in df.columns[1:]:
        df[col] = df[col].replace('+', '').apply(pd.to_numeric).astype(int)

    df.Country = df.Country.apply(lambda x: x.replace('\n', ''))

    return df.sort_values(['New', 'Cases'], ascending=False)


bot = TelegramMessenger('global-config.json')
curr_date = get_relative_date(format='%Y-%m-%d')

try:
    df = pd.read_csv(f'data/global-{curr_date}.csv')
except:
    df = get_data()
    df.to_csv(f'data/global-{curr_date}.csv', index=False)

total_cases = df.New.sum()
print(total_cases)

while True:
    date = get_relative_date(format='%Y-%m-%d')
    if date != curr_date:
        print(f'Starting update for {curr_date} GMT. Updates every 3 hours and shows for countries with more than 50 new cases.')

    try:
        df_new = get_data()
    except:
        df_new = df
    curr_time = get_relative_date(format='%Y-%m-%d %H:%M')
    curr_time_message = f'Case update at: {curr_time}'
    total_cases_new = df_new.New.sum()
    print(total_cases_new)

    if total_cases != total_cases_new:  # checking total case change
        total_cases = total_cases_new  # updating total case 
        df_update = df_new[df_new['New'] > 50]
        df_update = df_update[['Country', 'New',
                               'Cases', 'Deaths']].sort_values(['New', 'Cases'], ascending=False)
        
        df_update.to_csv(f'data/update-global-{curr_date}.csv', index=False)
        
        df_update.Country = df_update.Country.apply(lambda x: x[:8])
        df_update = df_update.rename(
            {'Country': 'Place'}, axis=1).set_index('Place').round()

        for g, sub_df in df_update.groupby(np.arange(len(df_update)) // 100): # Needed due to telegram 4096 char limit
            message = get_clean_table(sub_df)
            bot.send_message(message)
    else:
        message = 'No new cases'

    print(curr_time_message)
    print(message)
    if date != curr_date:
        curr_date = date
        df.to_csv(f'data/global-{curr_date}.csv', index=False)
    
    time.sleep(3600*3)



