from dateutil.relativedelta import relativedelta
from pytz import timezone
import numpy as np
import pandas as pd
import requests
import lxml.html as lh

from tabulate import tabulate
import json, time, datetime
import telegram


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
               'New Deaths', 'Recovered', 'Active', 'x', 'x']
    df = pd.DataFrame(rows, columns=columns)
    df = df.replace('', 0).iloc[:, :-2]

    for col in df.columns[1:]:
        df[col] = df[col].astype(str).str.replace(' ', '').replace(
            ',', '', regex=True).replace('+', '').apply(pd.to_numeric)

    df.dropna(inplace=True)
    df['Deaths'] = df['Deaths'].astype(int)
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


def get_relative_date(zone='UTC', format='%Y-%m-%d', **kwargs):
    tz = timezone(zone)
    time = datetime.datetime.now(tz)
    time_relative = time + relativedelta(**kwargs)
    return time_relative.strftime(format)


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
print(df.head(100))

while True:
    df_new = get_data()
    curr_time = get_relative_date(format='%Y-%m-%d %H:%M')
    curr_time_message = f'Case update at: {curr_time}'
    total_cases_new = df_new.New.sum()
    print(total_cases_new)
    print(df_new.head(100))
    if total_cases != total_cases_new:  # checking total case change
        total_cases = total_cases_new  # updating total case 
        df_update = df_new
        # df_update = df_update.merge(
        #     df.rename({'Confirmed': 'old_confirmed'}, axis=1))
        # df_update['New'] = df_update['Confirmed'] - df_update['old_confirmed']
        df_update = df_update[df_update['New'] != 0]
        df_update = df_update[['Country', 'New',
                               'Confirmed', 'Deaths']].sort_values(['New', 'Confirmed'], ascending=False)
        
        df_update.to_csv(f'data/update-global-{curr_date}.csv', index=False)
        
        for g, sub_df in df_update.groupby(np.arange(len(df_update)) // 40): # Needed due to telegram 4096 char limit
            print(sub_df.shape)
            message = tabulate(sub_df.set_index('Country'), headers='keys',
                            tablefmt='simple', numalign="right")
            bot.send_message(message)
    else:
        message = 'No new cases'

    print(curr_time_message)
    print(message)

    date = get_relative_date(format='%Y-%m-%d')
    if date != curr_date:
        bot.send_message(f'Starting update for {curr_date} GMT')
        # df = df_new[['Country', 'Confirmed']]
        curr_date = date
        df.to_csv(f'data/global-{curr_date}.csv', index=False)
    
    time.sleep(60)



