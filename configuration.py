import json


class Config:
    def __init__(self, default_config):
        try:
            with open(default_config) as f:
                default_config = json.load(f)
            self.LOGIN = default_config['LOGIN']
            self.PASSWORD = default_config['PASSWORD']
            self.USER_AGENT = default_config['USER_AGENT']
            self.COOKIES = default_config['COOKIES']
            self.AUTH_PAGE = default_config['AUTH_PAGE']
            self.TASKS_PAGE = default_config['TASKS_PAGE']
            self.NOTIFYER_TIMEOUT = default_config['NOTIFYER_TIMEOUT']
            self.DRIVER_TIMEOUT = default_config['DRIVER_TIMEOUT']
            self.REMIND_TIMEOUT = default_config['REMIND_TIMEOUT']
            self.TOKEN = default_config['TOKEN']
            self.ADMIN_ID = default_config['ADMIN_ID']
            self.ALLOW_CHAT_ID = default_config['ALLOW_CHAT_ID']
            self.CURR_CHAT_ID = default_config['CURR_CHAT_ID']
            self.CONTENT_TYPES = default_config['CONTENT_TYPES']
            self.LINK = default_config['LINK']
        except FileNotFoundError:
            raise Exception('Config file config/default_config.json is missing')

    def update_config(self, local_config):
        try:
            with open(local_config, 'r') as f:
                local_config = json.load(f)
            [list(map(lambda key: setattr(self, key, value.get(key)), value)) if isinstance(value, dict)
             else setattr(self, key, value) for key, value in local_config.items()]
        except FileNotFoundError:
            print('Updating config file config/local_config.json is missing')


config = Config('config/default_config.json')
# config.update_config('config/local_config.json')
