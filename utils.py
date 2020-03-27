import json, datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone

import telegram
from tabulate import tabulate


def get_relative_date(zone='UTC', format='%Y-%m-%d', **kwargs):
    tz = timezone(zone)
    time = datetime.datetime.now(tz)
    time_relative = time + relativedelta(**kwargs)
    return time_relative.strftime(format)

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
        self.bot.send_message(
            parse_mode='HTML', chat_id=self.__credentials['chat_id'], text=message)


def get_clean_table(df):
    message = tabulate(df, headers='keys',
                       tablefmt='simple', numalign="center")
    return '<pre>' + message + '</pre>'
