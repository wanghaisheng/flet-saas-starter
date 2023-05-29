from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Union

import flet as ft


class accountStatus:
    FARMED: str = 'Farmed'
    NOT_FARMED: str = 'Not farmed'
    LOCKED: str = 'Your account has been locked'
    SUSPENDED: str = 'Your account has been suspended'
    UNUSUAL_ACTIVITY: str = 'Unusual activity detected'
    ERROR: str = 'Unknown error'
    PC_LOGIN_FAILED: str = 'PC login failed'
    MOBILE_LOGIN_FAILED: str = 'Mobile login failed'
    SEARCH_WORDS_ERROR: str = "Couldn't get search words"
    PROXY_DEAD: str = 'Proxy is dead'

    @classmethod
    def error_list(cls):
        return (
            cls.LOCKED,
            cls.UNUSUAL_ACTIVITY,
            cls.ERROR,
            cls.PC_LOGIN_FAILED,
            cls.MOBILE_LOGIN_FAILED,
            cls.SEARCH_WORDS_ERROR,
            cls.PROXY_DEAD,
        )


class Account:
    sample_log = {
        'Last check': str(date.today()),
        'Status': 'Not farmed',
        "Today's points": 0,
        'Points': 0,
        'Daily': False,
        'Punch cards': False,
        'More promotions': False,
        'MSN shopping game': False,
        'PC searches': False,
        'Mobile searches': False,
    }

    def __init__(self, account: dict, index: int, page: ft.Page):
        self.account = account
        self.index = index
        self.page = page
        self.log: dict = account.get('log', False)
        if not self.log or self.log == {}:  # If log is empty
            self.account['log'] = self.sample_log
            self.log = account.get('log')
        self.username: str = account['username']
        self.password: str = account['password']
        self.proxy: Union[str, None] = account.get('proxy', None)
        self.pc_user_agent: Union[str, None] = account.get(
            'pc_user_agent', None
        )
        self.mobile_user_agent: Union[str, None] = account.get(
            'mobile_user_agent', None
        )
        self.redeem_goal_title: str = ''
        self.redeem_goal_price: str = -1
        self.pc_remaining_searches = -1
        self.mobile_remaining_searches = -1
        self._points: int = account.get('log', None).get('Points', 0)
        self._earned_points: int = account.get('log', None).get(
            "Today's points", 0
        )
        self._status: str = account.get('log', None).get(
            'Status', 'Not farmed'
        )
        self._last_check: str = account.get('log', None).get(
            'Last check', 'Never'
        )
        self._points_counter = -1
        self._starting_points = -1
        self._section = '-'
        self._detail = '-'

    def get_dict(self) -> dict:
        account = {
            'username': self.username,
            'password': self.password,
            'log': self.account['log'],
        }
        if self.proxy:
            account['proxy'] = self.proxy
        if self.pc_user_agent:
            account['pc_user_agent'] = self.pc_user_agent
        if self.mobile_user_agent:
            account['mobile_user_agent'] = self.mobile_user_agent
        self.account = account
        return account

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if self._status != value:
            self._status = value
            self.account['log']['Status'] = value

    @property
    def last_check(self):
        return self._last_check

    @last_check.setter
    def last_check(self, value):
        if self._last_check != value:
            self._last_check = value
            self.account['log']['Last check'] = value

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, value):
        if self._points != value:
            self._points = value
            self.account['log']['Points'] = value

    @property
    def earned_points(self):
        return self._earned_points

    @earned_points.setter
    def earned_points(self, value):
        if self._earned_points != value:
            self._earned_points = value
            self.account['log']["Today's points"] = value

    @property
    def points_counter(self):
        return self._points_counter

    @points_counter.setter
    def points_counter(self, value):
        if self._points_counter != value:
            self._points_counter = value

    @property
    def starting_points(self):
        return self._starting_points

    @starting_points.setter
    def starting_points(self, value):
        if self._starting_points != value:
            self._starting_points = value

    @property
    def section(self):
        return self._section

    @section.setter
    def section(self, value):
        if self._section != value:
            self._section = value

    @property
    def detail(self):
        return self._detail

    @detail.setter
    def detail(self, value):
        if self._detail != value:
            self._detail = value

    def update_value_in_log(self, key: str, value: Union[str, int, bool]):
        self.account['log'][key] = value

    def get_log_value(self, key: str) -> Union[str, bool, int]:
        return self.account['log'][key]

    def need_log_correction(self) -> bool:
        return (
            self.last_check == str(date.today())
            and self.status != accountStatus.FARMED
        )

    def correct_log(self):
        self.account['log']['Daily'] = False
        self.account['log']['Punch cards'] = False
        self.account['log']['More promotions'] = False
        self.account['log']['MSN shopping game'] = False
        self.account['log']['PC searches'] = False
        self.account['log']['Mobile searches'] = False

    def was_finished(self) -> bool:
        return self.status == accountStatus.FARMED and self.last_check == str(
            date.today()
        )

    def was_locked(self) -> bool:
        return self.status == accountStatus.LOCKED

    def was_suspended(self) -> bool:
        return self.status == accountStatus.SUSPENDED

    def got_unusual_activity(self) -> bool:
        return self.status == accountStatus.UNUSUAL_ACTIVITY

    def ran_into_error(self) -> bool:
        return self.status in (
            accountStatus.ERROR,
            accountStatus.PC_LOGIN_FAILED,
            accountStatus.MOBILE_LOGIN_FAILED,
            accountStatus.SEARCH_WORDS_ERROR,
        )

    def need_farm(self) -> bool:
        conditions = []
        if (
            self.page.client_storage.get('MRFarmer.daily_quests')
            and not self.account['log']['Daily']
        ):
            conditions.append(True)
        if (
            self.page.client_storage.get('MRFarmer.punch_cards')
            and not self.account['log']['Punch cards']
        ):
            conditions.append(True)
        if (
            self.page.client_storage.get('MRFarmer.more_activities')
            and not self.account['log']['More promotions']
        ):
            conditions.append(True)
        if (
            self.page.client_storage.get('MRFarmer.msn_shopping_game')
            and not self.account['log']['MSN shopping game']
        ):
            conditions.append(True)
        if (
            self.page.client_storage.get('MRFarmer.pc_search')
            and not self.account['log']['PC searches']
        ):
            conditions.append(True)
        if (
            self.page.client_storage.get('MRFarmer.mobile_search')
            and not self.account['log']['Mobile searches']
        ):
            conditions.append(True)
        if any(conditions):
            return True
        else:
            return False

    def is_pc_need(self) -> bool:
        """Check if browser for PC is needed or not based on farm options and account status"""
        if (
            self.page.client_storage.get('MRFarmer.daily_quests')
            and self.account['log']['Daily'] == False
        ):
            return True
        elif (
            self.page.client_storage.get('MRFarmer.punch_cards')
            and self.account['log']['Punch cards'] == False
        ):
            return True
        elif (
            self.page.client_storage.get('MRFarmer.more_activities')
            and self.account['log']['More promotions'] == False
        ):
            return True
        elif (
            self.page.client_storage.get('MRFarmer.msn_shopping_game')
            and self.account['log']['MSN shopping game'] == False
        ):
            return True
        elif (
            self.page.client_storage.get('MRFarmer.pc_search')
            and self.account['log']['PC searches'] == False
        ):
            return True
        else:
            return False

    def is_mobile_need(self) -> bool:
        return (
            self.page.client_storage.get('MRFarmer.mobile_search')
            and not self.get_log_value('Mobile searches')
            and (
                self.mobile_remaining_searches > 0
                or self.mobile_remaining_searches == -1
            )
        )

    def clean_log(self):
        """Delete Daily, Punch cards, More promotions, PC searches and Mobile searches from logs"""
        self.account['log'].pop('Daily', None)
        self.account['log'].pop('Punch cards', None)
        self.account['log'].pop('More promotions', None)
        self.account['log'].pop('MSN shopping game', None)
        self.account['log'].pop('PC searches', None)
        self.account['log'].pop('Mobile searches', None)

    def get_user_agent(self, isMobile: bool = False) -> str:
        if not isMobile:
            if self.pc_user_agent is None:
                return self.page.client_storage.get('MRFarmer.pc_user_agent')
            else:
                return self.pc_user_agent
        else:
            if self.mobile_user_agent is None:
                return self.page.client_storage.get(
                    'MRFarmer.mobile_user_agent'
                )
            else:
                return self.mobile_user_agent

    def is_ready_for_redeem(self) -> bool:
        if (
            self.redeem_goal_title != ''
            and self.redeem_goal_price != -1
            and self.points >= self.redeem_goal_price
        ):
            return True
        else:
            return False

    def get_redeem_message(self) -> str:
        if self.redeem_goal_price > 0:
            redeem_count = self.points // self.redeem_goal_price
        else:
            redeem_count = 1
        if redeem_count > 1:
            return f'🎁 Ready to redeem: {self.redeem_goal_title} for {self.redeem_goal_price} points ({redeem_count}x)\n\n'
        else:
            return f'🎁 Ready to redeem: {self.redeem_goal_title} for {self.redeem_goal_price} points\n\n'

    def finish(self):
        self.earned_points = self.points_counter - self.starting_points
        self.points = self.points_counter
        self.status = accountStatus.FARMED
        self.clean_log()
