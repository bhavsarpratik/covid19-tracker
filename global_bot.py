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

    columns = ['Country', 'Confirmed', 'New', 'Deaths',
               'New Deaths', 'Recovered', 'Active', 'x', 'x', 'x']
    df = pd.DataFrame(rows, columns=columns)
    df = df.astype(str).replace('', 0).iloc[:, :-3]

    for col in df.columns[1:]:
        df[col] = df[col].str.replace(' ', '').replace(
            ',', '', regex=True).replace('+', '').apply(pd.to_numeric).fillna(0).astype(int)

    df = df.sort_values(['New', 'Confirmed'], ascending=False)
    total = df.sum().values
    total[0] = 'Total'
    return pd.concat([pd.DataFrame([total], columns=df.columns), df])


bot = TelegramMessenger('global-config.json')
curr_date = get_relative_date(format='%Y-%m-%d')

try:
    df = pd.read_csv(f'data/global-{curr_date}.csv')
except:
    df = get_data()
    df.to_csv(f'data/global-{curr_date}.csv', index=False)

# df = df[['Country', 'Confirmed']]
total_cases = df.New.sum()
print(total_cases)

while True:
    date = get_relative_date(format='%Y-%m-%d')
    if date != curr_date:
        print(f'Starting update for {curr_date} GMT. Updates every 6 hours and shows for countries with more than 50 new cases.')

    df_new = get_data()
    curr_time = get_relative_date(format='%Y-%m-%d %H:%M')
    curr_time_message = f'Case update at: {curr_time}'
    total_cases_new = df_new.New.sum()
    print(total_cases_new)

    if total_cases != total_cases_new:  # checking total case change
        total_cases = total_cases_new  # updating total case 
        df_update = df_new[df_new['New'] > 50]
        df_update = df_update[['Country', 'New',
                               'Confirmed', 'Deaths']].sort_values(['New', 'Confirmed'], ascending=False)
        
        df_update.to_csv(f'data/update-global-{curr_date}.csv', index=False)
        
        df_update.Country = df_update.Country.apply(lambda x: x[:8])
        df_update = df_update.rename({'Country': 'Place', 'Confirmed': 'Case'}, axis=1).set_index('Place')

        for g, sub_df in df_update.groupby(np.arange(len(df_update)) // 100): # Needed due to telegram 4096 char limit
            message = get_clean_table(sub_df)
            bot.send_message(message)
    else:
        message = 'No new cases'

    print(curr_time_message)
    print(message)
    if date != curr_date:
        # df = df_new[['Country', 'Confirmed']]
        curr_date = date
        df.to_csv(f'data/global-{curr_date}.csv', index=False)
    
    time.sleep(3600*6)



