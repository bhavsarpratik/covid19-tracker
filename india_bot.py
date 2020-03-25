"""
Author: Pratik Bhavsar
Github: https://github.com/bhavsarpratik/covid19-tracker
"""

from dateutil.relativedelta import relativedelta
from pytz import timezone
import numpy as np
import pandas as pd
import requests
import lxml.html as lh

from tabulate import tabulate
import json, time, datetime
import telegram


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


class TelegramMessenger:
    """
    https://forums.fast.ai/t/training-metrics-as-notifications-on-mobile-using-callbacks/17330/4

    Utilizes this API Library:
       https://github.com/python-telegram-bot/python-telegram-bot
    To install:
       pip install python-telegram-bot --upgrade

    {"api_key": "462203107:<your API key>",
     "chat_id": "<your chat ID>"}

    Here's how you get an API key:
       https://core.telegram.org/api/obtaining_api_id
    Here's how you get your chat ID:
       https://stackoverflow.com/questions/32423837/telegram-bot-how-to-get-a-group-chat-id

    """

    def __init__(self, cred_file_path):
        self.__credentials = json.loads(open(cred_file_path).read())
        # Initialize bot
        self.bot = telegram.Bot(token=self.__credentials['api_key'])

    def send_message(self, message='Done'):
        self.bot.send_message(parse_mode='HTML', chat_id=self.__credentials['chat_id'], text=message)


def get_relative_date(zone='Asia/Kolkata', format='%Y-%m-%d', **kwargs):
    tz = timezone(zone)
    time = datetime.datetime.now(tz)
    time_relative = time + relativedelta(**kwargs)
    return time_relative.strftime(format)


bot = TelegramMessenger('india-config.json')
curr_date = get_relative_date(format='%Y-%m-%d')

try:
    df = pd.read_csv(f'data/{curr_date}.csv')
except:
    df = get_data()
    df.to_csv(f'data/{curr_date}.csv', index=False)

df = df[['State', 'Confirmed']]
total_cases = df.iloc[0, 1]

while True:
    df_new = get_data()
    curr_time = get_relative_date(format='%Y-%m-%d %H:%M')
    curr_time_message = f'Case update at: {curr_time}'
    
    if total_cases != df_new.iloc[0, 2]:  # checking total case change
        total_cases = df_new.iloc[0, 2]  # updating total case 
        df_update = df_new
        df_update = df_update.merge(
            df.rename({'Confirmed': 'old_confirmed'}, axis=1))
        df_update['New'] = df_update['Confirmed'] - df_update['old_confirmed']
        df_update = df_update[df_update['New'] != 0]
        df_update = df_update[['State', 'New',
                               'Confirmed', 'Deaths']].sort_values(['New', 'Confirmed'], ascending=False)
        
        df_update.to_csv(f'data/update-{curr_date}.csv', index=False)
        df_update.State = df_update.State.apply(lambda x: x[:8])
        df_update = df_update.rename({'Confirmed': 'Case'}, axis=1).set_index('State')
        
        message = '<pre>' + tabulate(df_update, headers='keys', tablefmt='orgtbl', numalign="right") + '</pre>'
        bot.send_message(message)
    else:
        message = 'No new cases'

    print(curr_time_message)
    print(message)

    date = get_relative_date(format='%Y-%m-%d')
    if date != curr_date:
        # message = tabulate(df_new.set_index('State'), headers='keys',
        #                    tablefmt='simple', numalign="right")
        # bot.send_message('Cases till yesterday')
        bot.send_message(f'Starting update for {curr_date} IST')
        df = df_new[['State', 'Confirmed']]
        curr_date = date
        df.to_csv(f'data/{curr_date}.csv', index=False)
    
    time.sleep(60)



