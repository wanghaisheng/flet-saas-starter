import copy
import json
import os
import platform
import random
import subprocess
import time
import traceback
import urllib.parse
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import List, Literal, Type, Union

import flet as ft
import ipapi
import requests
from func_timeout import FunctionTimedOut, func_set_timeout
from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    ElementNotVisibleException,
    InvalidSessionIdException,
    JavascriptException,
    NoAlertPresentException,
    NoSuchElementException,
    SessionNotCreatedException,
    TimeoutException,
    UnexpectedAlertPresentException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.exceptions import MaxRetryError, NewConnectionError

from .account import Account, accountStatus
from .exceptions import *
from .other_functions import resource_path

PC_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.58'
MOBILE_USER_AGENT = 'Mozilla/5.0 (Linux; Android 12; SM-N9750) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36 EdgA/112.0.1722.46'


def retry_on_500_errors(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        driver: WebDriver = args[1]
        error_codes = [
            'HTTP ERROR 500',
            'HTTP ERROR 502',
            'HTTP ERROR 503',
            'HTTP ERROR 504',
            'HTTP ERROR 505',
        ]
        result = function(*args, **kwargs)
        while True:
            try:
                status_code = driver.execute_script(
                    'return document.readyState;'
                )
                if status_code == 'complete' and not any(
                    error_code in driver.page_source
                    for error_code in error_codes
                ):
                    return result
                elif status_code == 'loading':
                    return result
                else:
                    raise Exception('Page not loaded')
            except Exception as e:
                if any(
                    error_code in driver.page_source
                    for error_code in error_codes
                ):   # Check if the page contains 500 errors
                    driver.refresh()   # Recursively refresh
                else:
                    raise Exception(
                        f'another exception occurred during handling 500 errors: {e}'
                    )

    return wrapper


class Farmer:
    base_url = 'https://rewards.bing.com/'

    def __init__(self, page: ft.Page, parent, home_page, accounts_page):
        from src.ui import Accounts, Home, UserInterface

        self.page = page
        self.parent: UserInterface = parent
        self.home_page: Home = home_page
        self.accounts_page: Accounts = accounts_page
        self.accounts_list: list = self.page.session.get('MRFarmer.accounts')
        self.accounts: List[Account] = [
            Account(account, idx, page)
            for idx, account in enumerate(self.accounts_list)
        ]
        self.accounts_path = Path(
            self.page.client_storage.get('MRFarmer.accounts_path')
        )
        self.points_counter: int = 0
        self.finished_accounts: list = []
        self.failed_accounts: list = []
        self.locked_accounts: list = []
        self.suspended_accounts: list = []
        self.current_account: dict = None
        self.browser: WebDriver = None
        self.starting_points: int = None
        self.point_counter: int = 0
        self.account_index: int = None
        self.lang, self.geo, self.tz = self.get_ccode_lang_and_offset()
        self.words = self.open_words_file()

    def create_message(self):
        """Create message from logs to send to Telegram"""
        today = date.today().strftime('%d/%m/%Y')
        total_earned = 0
        total_overall = 0
        message = f'📅 Daily report {today}\n\n'
        for index, account in enumerate(self.accounts, 1):
            redeem_message = None
            if account.is_ready_for_redeem():
                redeem_message = account.get_redeem_message()
            if account.was_finished():
                status = '✅ Farmed'
                total_earned += account.earned_points
                total_points = account.points
                total_overall += total_points
                message += f'{index}. {account.username}\n📝 Status: {status}\n⭐️ Earned points: {account.earned_points}\n🏅 Total points: {total_points}\n'
                if redeem_message:
                    message += redeem_message
                else:
                    message += '\n'
            elif account.was_suspended():
                status = '❌ Suspended'
                message += (
                    f'{index}. {account.username}\n📝 Status: {status}\n\n'
                )
            elif account.was_locked():
                status = '⚠️ Locked'
                message += (
                    f'{index}. {account.username}\n📝 Status: {status}\n\n'
                )
            elif account.got_unusual_activity():
                status = '⚠️ Unusual activity detected'
                message += (
                    f'{index}. {account.username}\n📝 Status: {status}\n\n'
                )
            elif account.ran_into_error():
                status = f'⛔️ {account.status}'
                message += (
                    f'{index}. {account.username}\n📝 Status: {status}\n\n'
                )
            else:
                status = f'Farmed on {account.last_check}'
                total_earned += account.earned_points
                total_points = account.points
                total_overall += total_points
                message += f'{index}. {account.username}\n📝 Status: {status}\n⭐️ Earned points: {account.earned_points}\n🏅 Total points: {total_points}\n'
                if redeem_message:
                    message += redeem_message
                else:
                    message += '\n'
        message += f'💵 Total earned points: {total_earned} (${total_earned/1300:0.02f}) (€{total_earned/1500:0.02f})'
        message += f'\n💵 Total points overall: {total_overall} (${total_overall/1300:0.02f}) (€{total_overall/1500:0.02f})'
        return message

    def send_report_to_messenger(self, message: str):
        if self.page.client_storage.get('MRFarmer.send_to_telegram'):
            self.send_to_telegram(message)
        if self.page.client_storage.get('MRFarmer.send_to_discord'):
            self.send_to_discord(message)

    def send_to_telegram(self, message: str):
        token = self.page.client_storage.get('MRFarmer.telegram_token')
        chat_id = self.page.client_storage.get('MRFarmer.telegram_chat_id')
        try:
            url = f'https://api.telegram.org/bot{token}/sendMessage'
            data = {'chat_id': chat_id, 'text': message}
            if self.page.client_storage.get('MRFarmer.telegram_proxy_switch'):
                proxy = self.page.client_storage.get('MRFarmer.telegram_proxy')
                requests.post(
                    url, json=data, proxies={'https': f'http://{proxy}'}
                )
            else:
                requests.post(url, json=data)
        except Exception as E:
            self.parent.open_snack_bar(
                f"Couldn't send report to Telgeram: {E}"
            )

    def send_to_discord(self, message: str):
        webhook_url = self.page.client_storage.get(
            'MRFarmer.discord_webhook_url'
        )
        if len(message) > 2000:
            messages = [
                message[i : i + 2000] for i in range(0, len(message), 2000)
            ]
            for ms in messages:
                content = {
                    'username': '⭐️ Microsoft Rewards Bot ⭐️',
                    'content': ms,
                }
                response = requests.post(webhook_url, json=content)
        else:
            content = {
                'username': '⭐️ Microsoft Rewards Bot ⭐️',
                'content': message,
            }
            response = requests.post(webhook_url, json=content)
        if response.status_code == 204:
            pass
        else:
            self.parent.open_snack_bar(
                f"Couldn't send report message to your Discord with status code {response.status_code}"
            )

    def check_internet_connection(self):
        system = platform.system()
        while True:
            try:
                if not self.parent.is_farmer_running:
                    return False
                if system == 'Windows':
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.check_output(
                        ['ping', '-n', '1', '8.8.8.8'],
                        timeout=5,
                        startupinfo=si,
                    )
                elif system == 'Linux':
                    subprocess.check_output(
                        ['ping', '-c', '1', '8.8.8.8'], timeout=5
                    )
                self.home_page.update_section('-')
                self.home_page.update_detail('-')
                return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                self.home_page.update_section('No internet connection...')
                self.home_page.update_detail('Checking...')
                time.sleep(1)

    def get_or_create_logs(self):
        """Read logs and check whether account farmed or not"""
        for account in self.accounts:
            try:
                try:
                    datetime.strptime(account.last_check, '%Y-%m-%d')
                except Exception:
                    account.last_check = str(date.today())
                if account.was_finished():
                    self.finished_accounts.append(account.username)
                elif account.was_suspended():
                    self.suspended_accounts.append(account.username)
                elif account.need_log_correction():
                    if account.log.keys() != account.sample_log.keys():
                        account.correct_log()
                        continue
                    if not account.need_farm():
                        account.clean_log()
                        self.finished_accounts.append(account.username)
                    else:
                        continue
                else:
                    account.status = accountStatus.NOT_FARMED
                    account.correct_log()
                if (
                    not isinstance(account.points, int)
                    and not account.points == 'N/A'
                ):
                    account.points = 0
            except KeyError as e:
                account['log'][e.args[0]] = account.sample_log[e.args[0]]
                account.update_value_in_log(
                    e.args[0], account.sample_log[e.args[0]]
                )
                account.correct_log()
            finally:
                self.accounts_list[account.index] = account.get_dict()
        self.update_accounts()
        self.home_page.update_overall_infos()

    def update_accounts(self):
        """Update logs with new data"""
        accounts = [account.get_dict() for account in self.accounts]
        self.page.session.set('MRFarmer.accounts', accounts)
        self.parent.update_accounts_file()

    def is_element_exists(
        self, browser: WebDriver, _by: By, element: str
    ) -> bool:
        """Returns True if given element exists else False"""
        try:
            browser.find_element(_by, element)
        except NoSuchElementException:
            return False
        return True

    def find_between(self, s: str, first: str, last: str) -> str:
        try:
            start = s.index(first) + len(first)
            end = s.index(last, start)
            return s[start:end]
        except ValueError:
            return ''

    def is_proxy_working(self, proxy: str):
        """Check if proxy is working or not"""
        try:
            requests.get(
                'https://www.google.com/', proxies={'https': proxy}, timeout=5
            )
            return True
        except:
            return False

    def calculate_sleep(self, default_sleep: Union[float, int]):
        """
        Sleep calculated with this formular:
        on FAST: random.uniform((default_sleep/2) * 0.5, (default_sleep/2) * 1.5)
        on SUPER_FAST: random.uniform((default_sleep/4) * 0.5, (default_sleep/4) * 1.5)
        else: default_sleep
        """
        if self.page.client_storage.get('MRFarmer.speed') == 'Super fast':
            return random.uniform(
                (default_sleep / 4) * 0.5, (default_sleep / 4) * 1.5
            )
        elif self.page.client_storage.get('MRFarmer.speed') == 'Fast':
            return random.uniform(
                (default_sleep / 2) * 0.5, (default_sleep / 2) * 1.5
            )
        else:
            return default_sleep

    @staticmethod
    def account_browser(
        page: ft.Page, account: dict, accounts_page
    ) -> WebDriver:
        def create_browser():
            if page.client_storage.get('MRFarmer.edge_webdriver'):
                options = EdgeOptions()
            else:
                options = ChromeOptions()
            accounts_path = Path(
                page.client_storage.get('MRFarmer.accounts_path')
            )
            options.add_argument(
                f'--user-data-dir={accounts_path.parent}/Profiles/{account["username"]}/PC'
            )
            options.add_argument(
                'user-agent='
                + page.client_storage.get('MRFarmer.pc_user_agent')
            )
            options.add_argument('lang=en')
            options.add_argument(
                '--disable-blink-features=AutomationControlled'
            )
            prefs = {
                'profile.default_content_setting_values.geolocation': 2,
                'credentials_enable_service': False,
                'profile.password_manager_enabled': False,
                'webrtc.ip_handling_policy': 'disable_non_proxied_udp',
                'webrtc.multiple_routes_enabled': False,
                'webrtc.nonproxied_udp_enabled': False,
                'detach': True,
            }
            options.add_experimental_option('prefs', prefs)
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option(
                'excludeSwitches', ['enable-automation']
            )
            if page.client_storage.get('MRFarmer.headless'):
                options.add_argument('--headless')
            if page.client_storage.get('MRFarmer.use_proxy') and account.get(
                'proxy', False
            ):
                options.add_argument(f'--proxy-server={account["proxy"]}')
            options.add_argument('log-level=3')
            options.add_argument('--start-maximized')
            if page.client_storage.get('MRFarmer.edge_webdriver'):
                browser_service = EdgeService()
            else:
                browser_service = ChromeService()
            if platform.system() == 'Linux':
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
            if platform.system() == 'Windows':
                browser_service.creationflags = subprocess.CREATE_NO_WINDOW
            if page.client_storage.get('MRFarmer.edge_webdriver'):
                browser = webdriver.Edge(
                    options=options, service=browser_service
                )
            else:
                browser = webdriver.Chrome(
                    options=options, service=browser_service
                )
            return browser

        browser = create_browser()
        while accounts_page.is_browser_running_status() and isinstance(
            browser, WebDriver
        ):
            time.sleep(1)
            continue
        else:
            if isinstance(browser, WebDriver):
                browser.quit()

    def browser_setup(self, account: Account, isMobile: bool = False):
        # Create Chrome browser
        if self.page.client_storage.get('MRFarmer.edge_webdriver'):
            options = EdgeOptions()
        else:
            options = ChromeOptions()
        if self.page.client_storage.get('MRFarmer.session'):
            if not isMobile:
                options.add_argument(
                    f'--user-data-dir={self.accounts_path.parent}/Profiles/{account.username}/PC'
                )
            else:
                options.add_argument(
                    f'--user-data-dir={self.accounts_path.parent}/Profiles/{account.username}/Mobile'
                )
        options.add_argument(f'user-agent={account.get_user_agent(isMobile)}')
        options.add_argument('lang=' + self.lang.split('-')[0])
        options.add_argument('--disable-blink-features=AutomationControlled')
        prefs = {
            'profile.default_content_setting_values.geolocation': 2,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'webrtc.ip_handling_policy': 'disable_non_proxied_udp',
            'webrtc.multiple_routes_enabled': False,
            'webrtc.nonproxied_udp_enabled': False,
            'profile.managed_default_content_settings.images': 1,
        }
        if self.page.client_storage.get('MRFarmer.disable_images'):
            prefs['profile.managed_default_content_settings.images'] = 2
        options.add_experimental_option('prefs', prefs)
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option(
            'excludeSwitches', ['enable-automation']
        )
        if self.page.client_storage.get('MRFarmer.headless'):
            options.add_argument('--headless')
        if (
            self.page.client_storage.get('MRFarmer.use_proxy')
            and account.proxy
        ):
            if self.is_proxy_working(account.proxy):
                options.add_argument(f'--proxy-server={account.proxy}')
                self.home_page.update_proxy(account.proxy)
            else:
                if self.page.client_storage.get(
                    'MRFarmer.skip_on_proxy_failure'
                ):
                    raise ProxyIsDeadException
                else:
                    self.home_page.update_proxy(
                        f'{account.proxy} is not working'
                    )
        options.add_argument('log-level=3')
        options.add_argument('--start-maximized')
        if self.page.client_storage.get('MRFarmer.edge_webdriver'):
            browser_service = EdgeService()
        else:
            browser_service = ChromeService()
        if platform.system() == 'Linux':
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        if platform.system() == 'Windows':
            browser_service.creationflags = subprocess.CREATE_NO_WINDOW
        if self.page.client_storage.get('MRFarmer.edge_webdriver'):
            browser = webdriver.Edge(options=options, service=browser_service)
        else:
            browser = webdriver.Chrome(
                options=options, service=browser_service
            )
        return browser

    def login(
        self, browser: WebDriver, account: Account, isMobile: bool = False
    ):
        """Login into  Microsoft account"""

        def close_welcome_tab():
            """close welcome tab if it exists"""
            time.sleep(2)
            if len(browser.window_handles) > 1:
                current_window = browser.current_window_handle
                for handler in browser.window_handles:
                    if handler != current_window:
                        browser.switch_to.window(handler)
                        time.sleep(0.5)
                        browser.close()
                browser.switch_to.window(current_window)

        def answer_to_break_free_from_password():
            # Click No thanks on break free from password question
            time.sleep(2)
            browser.find_element(By.ID, 'iCancel').click()
            time.sleep(5)

        def answer_updating_terms():
            # Accept updated terms
            time.sleep(2)
            browser.find_element(By.ID, 'iNext').click()
            time.sleep(5)

        def accept_privacy():
            time.sleep(3)
            self.wait_until_visible(browser, By.ID, 'id__0', 15)
            browser.execute_script(
                'window.scrollTo(0, document.body.scrollHeight);'
            )
            self.wait_until_clickable(browser, By.ID, 'id__0', 15)
            browser.find_element(By.ID, 'id__0').click()
            WebDriverWait(browser, 25).until_not(
                EC.visibility_of_element_located((By.ID, 'id__0'))
            )
            time.sleep(5)

        def wait_to_load_blank_page():
            wait = WebDriverWait(browser, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            wait.until_not(EC.title_is(''))
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'title')))
            wait.until(
                lambda driver: driver.execute_script(
                    'return document.readyState'
                )
                == 'complete'
            )

        def continue_login_process():
            self.home_page.update_detail('Microsoft Rewards...')
            self.rewards_login(browser, account, isMobile)
            self.home_page.update_detail('Bing...')
            self.check_bing_login(browser, account, isMobile)

        def enter_email():
            self.wait_until_visible(browser, By.ID, 'loginHeader', 10)
            browser.find_element(By.NAME, 'loginfmt').send_keys(
                account.username
            )
            browser.find_element(By.ID, 'idSIButton9').click()
            WebDriverWait(browser, 30).until_not(
                EC.visibility_of_element_located((By.NAME, 'loginfmt'))
            )
            time.sleep(self.calculate_sleep(5))

        def enter_password():
            self.wait_until_clickable(browser, By.ID, 'i0118', 10)
            browser.find_element(By.ID, 'i0118').send_keys(account.password)
            time.sleep(2)
            browser.find_element(By.ID, 'idSIButton9').click()
            WebDriverWait(browser, 30).until_not(
                EC.visibility_of_element_located((By.ID, 'i0118'))
            )
            time.sleep(self.calculate_sleep(5))

        def stay_signed_in_or_not():
            if self.page.client_storage.get('MRFarmer.session'):
                # Click Yes to stay signed in.
                browser.find_element(By.ID, 'idSIButton9').click()
            else:
                # Click No.
                browser.find_element(By.ID, 'idBtn_Back').click()

        login_message = (
            'Logging in...' if not isMobile else 'Logging in Mobile...'
        )
        self.home_page.update_section(login_message)
        # Close welcome tab for new sessions
        if self.page.client_storage.get('MRFarmer.session'):
            close_welcome_tab()
        # Access to bing.com
        self.go_to_url(browser, 'https://login.live.com/')
        # Check if account is already logged in
        if self.page.client_storage.get(
            'MRFarmer.session'
        ) and not self.is_element_exists(browser, By.ID, 'i0116'):
            if self.is_element_exists(browser, By.ID, 'i0118'):
                enter_password()
                if self.is_element_exists(
                    browser, By.ID, 'idSIButton9'
                ) and self.is_element_exists(browser, By.ID, 'idBtn_Back'):
                    stay_signed_in_or_not()
            if (
                browser.title == 'Microsoft account privacy notice'
                or self.is_element_exists(
                    browser,
                    By.XPATH,
                    '//*[@id="interruptContainer"]/div[3]/div[3]/img',
                )
            ):
                accept_privacy()
            if browser.title == '':
                wait_to_load_blank_page()
            if (
                browser.title == "We're updating our terms"
                or self.is_element_exists(browser, By.ID, 'iAccrualForm')
            ):
                answer_updating_terms()
            self.answer_to_security_info_update(browser)
            # Click No thanks on break free from password question
            if self.is_element_exists(browser, By.ID, 'setupAppDesc'):
                answer_to_break_free_from_password()
            if (
                browser.title == 'Microsoft account | Home'
                or self.is_element_exists(browser, By.ID, 'navs_container')
            ):
                continue_login_process()
                return
            elif (
                browser.title == 'Your account has been temporarily suspended'
            ):
                raise AccountLockedException('Your account has been locked !')
            elif (
                self.is_element_exists(browser, By.ID, 'mectrl_headerPicture')
                or self.is_element_exists(browser, By.ID, 'meControl')
                or 'Sign In or Create' in browser.title
            ):
                if self.is_element_exists(
                    browser, By.ID, 'mectrl_headerPicture'
                ):
                    browser.find_element(By.ID, 'mectrl_headerPicture').click()
                    WebDriverWait(browser, 30).until_not(
                        EC.visibility_of_element_located(
                            (By.ID, 'mectrl_headerPicture')
                        )
                    )
                    time.sleep(2)
                elif self.is_element_exists(browser, By.ID, 'meControl'):
                    browser.find_element(By.ID, 'meControl').click()
                    WebDriverWait(browser, 30).until_not(
                        EC.visibility_of_element_located((By.ID, 'meControl'))
                    )
                    time.sleep(2)
                else:
                    raise LoginFailedException(
                        'could not locate sign in button',
                        account.username,
                        isMobile,
                    )
                if self.is_element_exists(browser, By.ID, 'newSessionLink'):
                    self.wait_until_visible(
                        browser, By.ID, 'newSessionLink', 10
                    )
                    browser.find_element(By.ID, 'newSessionLink').click()
                elif self.is_element_exists(browser, By.ID, 'i0118'):
                    self.wait_until_visible(browser, By.ID, 'i0118', 10)
                    browser.find_element(By.ID, 'i0118').send_keys(
                        account.password
                    )
                    time.sleep(2)
                    browser.find_element(By.ID, 'idSIButton9').click()
                    WebDriverWait(browser, 30).until_not(
                        EC.visibility_of_element_located(
                            (By.ID, 'idSIButton9')
                        )
                    )
                    time.sleep(5)
                else:
                    raise LoginFailedException(
                        'could not relogin to account',
                        account.username,
                        isMobile,
                    )
                self.home_page.update_section('Logged in')
                continue_login_process()
                return None
        enter_email()
        enter_password()
        try:
            if (
                browser.title == 'Microsoft account privacy notice'
                or self.is_element_exists(
                    browser,
                    By.XPATH,
                    '//*[@id="interruptContainer"]/div[3]/div[3]/img',
                )
            ):
                accept_privacy()
            if browser.title == '':
                wait_to_load_blank_page()
            if (
                browser.title == "We're updating our terms"
                or self.is_element_exists(browser, By.ID, 'iAccrualForm')
            ):
                answer_updating_terms()
            self.answer_to_security_info_update(browser)
            if self.is_element_exists(
                browser, By.ID, 'idSIButton9'
            ) and self.is_element_exists(browser, By.ID, 'idBtn_Back'):
                stay_signed_in_or_not()
            self.answer_to_security_info_update(browser)
            # Click No thanks on break free from password question
            if self.is_element_exists(browser, By.ID, 'setupAppDesc'):
                answer_to_break_free_from_password()
        except NoSuchElementException:
            # Check for if account has been locked.
            if (
                browser.title == 'Your account has been temporarily suspended'
                or self.is_element_exists(
                    browser,
                    By.CLASS_NAME,
                    'serviceAbusePageContainer  PageContainer',
                )
            ):
                raise AccountLockedException('Your account has been locked !')
            elif browser.title == 'Help us protect your account':
                raise UnusualActivityException('Unusual activity detected')
            else:
                raise UnhandledException('Unknown error !')
        # Wait 5 seconds
        time.sleep(5)
        # Click Security Check
        try:
            browser.find_element(By.ID, 'iLandingViewAction').click()
        except (NoSuchElementException, ElementNotInteractableException) as e:
            pass
        # Wait complete loading
        try:
            self.wait_until_visible(browser, By.ID, 'KmsiCheckboxField', 10)
        except (TimeoutException) as e:
            pass
        # Click next
        try:
            browser.find_element(By.ID, 'idSIButton9').click()
            # Wait 5 seconds
            time.sleep(5)
        except (NoSuchElementException, ElementNotInteractableException) as e:
            pass
        continue_login_process()

    def answer_to_security_info_update(self, browser: WebDriver):
        """Clicks on looks good if it asks for security info update"""
        if (
            browser.title == 'Is your security info still accurate?'
            or self.is_element_exists(browser, By.ID, 'iLooksGood')
        ):
            time.sleep(2)
            browser.find_element(By.ID, 'iLooksGood').click()
            time.sleep(5)

    @retry_on_500_errors
    def go_to_url(self, browser: WebDriver, url: str):
        browser.get(url)

    def rewards_login(
        self, browser: WebDriver, account: Account, isMobile: bool = False
    ):
        """Login into Microsoft rewards and check account"""
        self.go_to_url(browser, self.base_url)
        self.answer_to_security_info_update(browser)
        try:
            time.sleep(self.calculate_sleep(10))
            # click on sign up button if needed
            if self.is_element_exists(
                browser, By.ID, 'start-earning-rewards-link'
            ):
                browser.find_element(
                    By.ID, 'start-earning-rewards-link'
                ).click()
                time.sleep(5)
                browser.refresh()
                time.sleep(5)
        except:
            pass
        time.sleep(self.calculate_sleep(10))
        # Check for ErrorMessage in Microsoft rewards page
        try:
            error = browser.find_element(By.ID, 'error')
            error.is_displayed()
            if 'suspended' in browser.find_element(
                By.XPATH, '//*[@id="error"]/h1'
            ).get_attribute('innerHTML'):
                raise AccountSuspendedException(
                    'Your account has been suspended !'
                )
            elif 'country' in browser.find_element(
                By.XPATH, '//*[@id="error"]/h1'
            ).get_attribute('innerHTML'):
                raise RegionException(
                    'Microsoft Rewards is not available in your region !'
                )
            else:
                raise UnhandledException(
                    "There's an error on your MS Rewards page!"
                )
        except NoSuchElementException:
            self.answer_to_security_info_update(browser)
            self.wait_until_visible(browser, By.ID, 'app-host', 30)
            (
                account.redeem_goal_title,
                account.redeem_goal_price,
            ) = self.get_redeem_goal(browser)
            if account.starting_points == -1:
                account.starting_points = self.get_account_points(browser)
                account.points_counter = account.starting_points
            self.home_page.update_points_counter(account.points_counter)
            if isMobile:
                account.mobile_remaining_searches = (
                    self.get_remaining_searches(browser)[1]
                )

    @func_set_timeout(300)
    def check_bing_login(
        self, browser: WebDriver, account: Account, isMobile: bool = False
    ):
        self.go_to_url(browser, 'https://bing.com/')
        time.sleep(self.calculate_sleep(15))
        # try to get points at first if account already logged in
        if self.page.client_storage.get('MRFarmer.session'):
            try:
                if not isMobile:
                    try:
                        points_counter = int(
                            browser.find_element(By.ID, 'id_rc').get_attribute(
                                'innerHTML'
                            )
                        )
                    except ValueError:
                        if browser.find_element(By.ID, 'id_s').is_displayed():
                            browser.find_element(By.ID, 'id_s').click()
                            time.sleep(15)
                            self.check_bing_login(browser, account, isMobile)
                        time.sleep(2)
                        points_counter = int(
                            browser.find_element(By.ID, 'id_rc')
                            .get_attribute('innerHTML')
                            .replace(',', '')
                        )
                else:
                    browser.find_element(By.ID, 'mHamburger').click()
                    time.sleep(1)
                    points_counter = int(
                        browser.find_element(By.ID, 'fly_id_rc').get_attribute(
                            'innerHTML'
                        )
                    )
            except:
                pass
            else:
                self.home_page.update_points_counter(points_counter)
                return None
        # Accept Cookies
        try:
            browser.find_element(By.ID, 'bnp_btn_accept').click()
        except:
            pass
        if isMobile:
            # close bing app banner
            if self.is_element_exists(browser, By.ID, 'bnp_rich_div'):
                try:
                    browser.find_element(
                        By.XPATH, '//*[@id="bnp_bop_close_icon"]/img'
                    ).click()
                except NoSuchElementException:
                    pass
            try:
                time.sleep(1)
                browser.find_element(By.ID, 'mHamburger').click()
            except:
                try:
                    browser.find_element(By.ID, 'bnp_btn_accept').click()
                except:
                    pass
                time.sleep(1)
                if self.is_element_exists(
                    browser,
                    By.XPATH,
                    '//*[@id="bnp_ttc_div"]/div[1]/div[2]/span',
                ):
                    browser.execute_script(
                        """var element = document.evaluate('/html/body/div[1]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                            element.remove();"""
                    )
                    time.sleep(5)
                time.sleep(1)
                try:
                    browser.find_element(By.ID, 'mHamburger').click()
                except:
                    pass
            try:
                time.sleep(1)
                browser.find_element(By.ID, 'HBSignIn').click()
                time.sleep(5)
                self.answer_to_security_info_update(browser)
            except:
                pass
            try:
                time.sleep(2)
                browser.find_element(By.ID, 'iShowSkip').click()
                time.sleep(3)
            except:
                if (
                    str(browser.current_url).split('?')[0]
                    == 'https://account.live.com/proofs/Add'
                ):
                    self.finished_accounts.append(account.username)
                    self.accounts[self.account_index]['log'][
                        'Last check'
                    ] = 'Requires manual check!'
                    self.update_accounts()
                    raise Exception
        time.sleep(5)
        # Refresh page
        self.go_to_url(browser, 'https://bing.com/')
        time.sleep(self.calculate_sleep(15))
        # Update Counter
        try:
            if not isMobile:
                try:
                    account.points_counter = int(
                        browser.find_element(By.ID, 'id_rc').get_attribute(
                            'innerHTML'
                        )
                    )
                except:
                    if browser.find_element(By.ID, 'id_s').is_displayed():
                        browser.find_element(By.ID, 'id_s').click()
                        time.sleep(15)
                        self.check_bing_login(browser, account, isMobile)
                    time.sleep(5)
                    account.points_counter = int(
                        browser.find_element(By.ID, 'id_rc')
                        .get_attribute('innerHTML')
                        .replace(',', '')
                    )
            else:
                try:
                    browser.find_element(By.ID, 'mHamburger').click()
                except:
                    try:
                        browser.find_element(By.ID, 'bnp_close_link').click()
                        time.sleep(4)
                        browser.find_element(By.ID, 'bnp_btn_accept').click()
                    except:
                        pass
                    time.sleep(1)
                    browser.find_element(By.ID, 'mHamburger').click()
                time.sleep(1)
                account.points_counter = int(
                    browser.find_element(By.ID, 'fly_id_rc').get_attribute(
                        'innerHTML'
                    )
                )
        except:
            self.check_bing_login(browser, account, isMobile)
        else:
            self.home_page.update_points_counter(account.points_counter)

    def wait_until_visible(
        self,
        browser: WebDriver,
        by_: By,
        selector: str,
        time_to_wait: int = 10,
    ):
        WebDriverWait(browser, time_to_wait).until(
            EC.visibility_of_element_located((by_, selector))
        )

    def wait_until_clickable(
        self,
        browser: WebDriver,
        by_: By,
        selector: str,
        time_to_wait: int = 10,
    ):
        WebDriverWait(browser, time_to_wait).until(
            EC.element_to_be_clickable((by_, selector))
        )

    def wait_until_question_refresh(self, browser: WebDriver):
        tries = 0
        refreshCount = 0
        while True:
            try:
                browser.find_elements(By.CLASS_NAME, 'rqECredits')[0]
                return True
            except:
                if tries < 10:
                    tries += 1
                    time.sleep(0.5)
                else:
                    if refreshCount < 5:
                        browser.refresh()
                        refreshCount += 1
                        tries = 0
                        time.sleep(5)
                    else:
                        return False

    def wait_until_quiz_loads(self, browser: WebDriver):
        tries = 0
        refreshCount = 0
        while True:
            try:
                browser.find_element(
                    By.XPATH, '//*[@id="currentQuestionContainer"]'
                )
                return True
            except:
                if tries < 10:
                    tries += 1
                    time.sleep(0.5)
                else:
                    if refreshCount < 5:
                        browser.refresh()
                        refreshCount += 1
                        tries = 0
                        time.sleep(5)
                    else:
                        return False

    def get_dashboard_data(self, browser: WebDriver) -> dict:
        tries = 0
        dashboard = None
        while not dashboard and tries <= 5:
            try:
                dashboard = self.find_between(
                    browser.find_element(By.XPATH, '/html/body').get_attribute(
                        'innerHTML'
                    ),
                    'var dashboard = ',
                    ';\n        appDataModule.constant("prefetchedDashboard", dashboard);',
                )
                dashboard = json.loads(dashboard)
            except:
                tries += 1
                if tries == 6:
                    raise Exception('Could not locate dashboard')
                browser.refresh()
                self.wait_until_visible(browser, By.ID, 'app-host', 30)
        return dashboard

    def get_account_points(self, browser: WebDriver) -> int:
        return self.get_dashboard_data(browser)['userStatus'][
            'availablePoints'
        ]

    def get_redeem_goal(self, browser: WebDriver):
        user_status = self.get_dashboard_data(browser)['userStatus']
        return (
            user_status['redeemGoal']['title'],
            user_status['redeemGoal']['price'],
        )

    def get_ccode_lang_and_offset(self) -> tuple:
        try:
            nfo = ipapi.location()
            lang = nfo['languages'].split(',')[0]
            geo = nfo['country']
            tz = str(round(int(nfo['utc_offset']) / 100 * 60))
            return (lang, geo, tz)
        except:
            return ('en-US', 'US', '-480')

    def reset_tabs(self, browser: WebDriver):
        try:
            curr = browser.current_window_handle

            for handle in browser.window_handles:
                if handle != curr:
                    browser.switch_to.window(handle)
                    time.sleep(0.5)
                    browser.close()
                    time.sleep(0.5)

            browser.switch_to.window(curr)
            time.sleep(0.5)
            self.go_to_url(browser, self.base_url)
        except:
            self.go_to_url(browser, self.base_url)
        finally:
            self.wait_until_visible(browser, By.ID, 'app-host', 30)

    def get_answer_code(self, key: str, string: str) -> str:
        """Get answer code for this or that quiz"""
        t = 0
        for i in range(len(string)):
            t += ord(string[i])
        t += int(key[-2:], 16)
        return str(t)

    def open_words_file(self):
        try:
            return (
                open(resource_path('assets/searchwords.txt'), 'r')
                .read()
                .splitlines()
            )
        except:
            return None

    def bing_searches(
        self, browser: WebDriver, account: Account, isMobile: bool = False
    ):
        """Complete Bing searches PC/Mobile"""

        def get_google_trends(numberOfwords: int) -> list:
            search_terms = []
            i = 0
            while len(search_terms) < numberOfwords:
                i += 1
                r = requests.get(
                    'https://trends.google.com/trends/api/dailytrends?hl='
                    + self.lang
                    + '&ed='
                    + str(
                        (date.today() - timedelta(days=i)).strftime('%Y%m%d')
                    )
                    + '&geo='
                    + self.geo
                    + '&ns=15'
                )
                google_trends = json.loads(r.text[6:])
                for topic in google_trends['default']['trendingSearchesDays'][
                    0
                ]['trendingSearches']:
                    search_terms.append(topic['title']['query'].lower())
                    for related_topic in topic['relatedQueries']:
                        search_terms.append(related_topic['query'].lower())
                search_terms = list(set(search_terms))
            del search_terms[numberOfwords : (len(search_terms) + 1)]
            return search_terms

        def get_related_terms(word: str) -> list:
            try:
                r = requests.get(
                    'https://api.bing.com/osjson.aspx?query=' + word,
                    headers={'User-agent': PC_USER_AGENT},
                )
                return r.json()[1]
            except:
                return []

        def bing_search(word: str, isMobile: bool):
            try:
                if not isMobile:
                    browser.find_element(By.ID, 'sb_form_q').clear()
                    time.sleep(1)
                else:
                    self.go_to_url(browser, 'https://bing.com')
            except:
                self.go_to_url(browser, 'https://bing.com')
            time.sleep(2)
            searchbar = browser.find_element(By.ID, 'sb_form_q')
            if self.page.client_storage.get('MRFarmer.speed') != 'Normal':
                searchbar.send_keys(word)
                time.sleep(self.calculate_sleep(1))
            else:
                for char in word:
                    searchbar.send_keys(char)
                    time.sleep(random.uniform(0.2, 0.4))
            searchbar.submit()
            time.sleep(self.calculate_sleep(random.randint(12, 24)))
            points = 0
            try:
                points = self.get_points_from_bing(browser, account, isMobile)
            except:
                points = account.points_counter
            return points

        if not isMobile:
            self.home_page.update_section('PC Bing Searches')
            numberOfSearches = account.pc_remaining_searches
        else:
            numberOfSearches = account.mobile_remaining_searches
            self.home_page.update_section('Mobile Bing Searches')
        self.home_page.update_detail(f'0/{numberOfSearches}')
        i = 0
        if self.words is not None:
            search_terms = random.sample(self.words, numberOfSearches)
        else:
            try:
                search_terms = get_google_trends(numberOfSearches)
                if len(search_terms) == 0:
                    raise GetSearchWordsException
            except:
                raise GetSearchWordsException
        for word in search_terms:
            i += 1
            self.home_page.update_detail(f'{i}/{numberOfSearches}')
            points = bing_search(word, isMobile)
            self.home_page.update_points_counter(points)
            if points <= account.points_counter and i > numberOfSearches:
                relatedTerms = get_related_terms(word)
                for term in relatedTerms:
                    points = bing_search(term, isMobile)
                    self.home_page.update_points_counter(points)
                    if points >= account.points_counter:
                        break
            if points >= account.points_counter:
                account.points_counter = points
            else:
                break

    def locate_rewards_card(
        self, browser: WebDriver, activity: dict
    ) -> WebElement:
        """Locate rewards card on the page"""
        time.sleep(self.calculate_sleep(5))
        all_cards = browser.find_elements(
            By.CLASS_NAME, 'rewards-card-container'
        )
        for card in all_cards:
            data_bi_id = card.get_attribute('data-bi-id')
            if activity['offerId'] == data_bi_id:
                return card
        else:
            raise NoSuchElementException(
                f"could not locate the provided card: {activity['name']}"
            )

    def complete_daily_set(self, browser: WebDriver, account: Account):
        """Complete daily set tasks"""

        def complete_daily_set_search(_activity: dict):
            time.sleep(5)
            card = self.locate_rewards_card(browser, _activity)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(random.randint(13, 17)))
            points = self.get_points_from_bing(browser, account, False)
            account.points_counter = points
            self.home_page.update_points_counter(points)
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        def complete_daily_set_survey(_activity: dict):
            time.sleep(5)
            card = self.locate_rewards_card(browser, _activity)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(8))
            # Accept cookie popup
            if self.is_element_exists(browser, By.ID, 'bnp_container'):
                browser.find_element(By.ID, 'bnp_btn_accept').click()
                time.sleep(2)
            # Click on later on Bing wallpaper app popup
            if self.is_element_exists(
                browser, By.ID, 'b_notificationContainer_bop'
            ):
                browser.find_element(By.ID, 'bnp_hfly_cta2').click()
                time.sleep(2)
            self.wait_until_clickable(browser, By.ID, 'btoption0', 15)
            time.sleep(1)
            browser.find_element(
                By.ID, f'btoption{str(random.randint(0, 1))}'
            ).click()
            time.sleep(self.calculate_sleep(random.randint(10, 15)))
            points = self.get_points_from_bing(browser, account, False)
            account.points_counter = points
            self.home_page.update_points_counter(points)
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        def complete_daily_set_quiz(_activity: dict):
            time.sleep(5)
            card = self.locate_rewards_card(browser, _activity)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(12))
            if not self.wait_until_quiz_loads(browser):
                self.reset_tabs(browser)
                return
            # Accept cookie popup
            if self.is_element_exists(browser, By.ID, 'bnp_container'):
                browser.find_element(By.ID, 'bnp_btn_accept').click()
                time.sleep(2)
            self.wait_until_visible(browser, By.ID, 'overlayPanel', 25)
            self.wait_until_clickable(
                browser, By.XPATH, '//*[@id="rqStartQuiz"]', 25
            )
            time.sleep(2)
            browser.find_element(By.XPATH, '//*[@id="rqStartQuiz"]').click()
            time.sleep(3)
            numberOfQuestions = browser.execute_script(
                'return _w.rewardsQuizRenderInfo.maxQuestions'
            )
            numberOfOptions = browser.execute_script(
                'return _w.rewardsQuizRenderInfo.numberOfOptions'
            )
            for _ in range(numberOfQuestions):
                if numberOfOptions == 8:
                    answers = []
                    for i in range(8):
                        if (
                            browser.find_element(
                                By.ID, 'rqAnswerOption' + str(i)
                            )
                            .get_attribute('iscorrectoption')
                            .lower()
                            == 'true'
                        ):
                            answers.append('rqAnswerOption' + str(i))
                    for answer in answers:
                        # Click on later on Bing wallpaper app popup
                        if self.is_element_exists(
                            browser, By.ID, 'b_notificationContainer_bop'
                        ):
                            browser.find_element(
                                By.ID, 'bnp_hfly_cta2'
                            ).click()
                            time.sleep(2)
                        self.wait_until_clickable(browser, By.ID, answer, 25)
                        browser.find_element(By.ID, answer).click()
                        time.sleep(self.calculate_sleep(6))
                        if not self.wait_until_question_refresh(browser):
                            return
                    time.sleep(self.calculate_sleep(6))
                elif numberOfOptions == 4:
                    correctOption = browser.execute_script(
                        'return _w.rewardsQuizRenderInfo.correctAnswer'
                    )
                    for i in range(4):
                        if (
                            browser.find_element(
                                By.ID, 'rqAnswerOption' + str(i)
                            ).get_attribute('data-option')
                            == correctOption
                        ):
                            # Click on later on Bing wallpaper app popup
                            if self.is_element_exists(
                                browser, By.ID, 'b_notificationContainer_bop'
                            ):
                                browser.find_element(
                                    By.ID, 'bnp_hfly_cta2'
                                ).click()
                                time.sleep(2)
                            self.wait_until_clickable(
                                browser, By.ID, f'rqAnswerOption{str(i)}', 25
                            )
                            browser.find_element(
                                By.ID, 'rqAnswerOption' + str(i)
                            ).click()
                            time.sleep(self.calculate_sleep(6))
                            if not self.wait_until_question_refresh(browser):
                                return
                            break
                    time.sleep(self.calculate_sleep(6))
                points = self.get_points_from_bing(browser, account, False)
                account.points_counter = points
                self.home_page.update_points_counter(points)
            time.sleep(self.calculate_sleep(6))
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        def complete_daily_set_variable_activity(_activity: dict):
            time.sleep(2)
            card = self.locate_rewards_card(browser, _activity)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(10))
            # Accept cookie popup
            if self.is_element_exists(browser, By.ID, 'bnp_container'):
                browser.find_element(By.ID, 'bnp_btn_accept').click()
                time.sleep(2)
            try:
                browser.find_element(
                    By.XPATH, '//*[@id="rqStartQuiz"]'
                ).click()
                self.wait_until_visible(
                    browser,
                    By.XPATH,
                    '//*[@id="currentQuestionContainer"]/div/div[1]',
                    3,
                )
            except (NoSuchElementException, TimeoutException):
                try:
                    counter = str(
                        browser.find_element(
                            By.XPATH, '//*[@id="QuestionPane0"]/div[2]'
                        ).get_attribute('innerHTML')
                    )[:-1][1:]
                    numberOfQuestions = max(
                        [int(s) for s in counter.split() if s.isdigit()]
                    )
                    for question in range(numberOfQuestions):
                        # Click on later on Bing wallpaper app popup
                        if self.is_element_exists(
                            browser, By.ID, 'b_notificationContainer_bop'
                        ):
                            browser.find_element(
                                By.ID, 'bnp_hfly_cta2'
                            ).click()
                            time.sleep(2)

                        browser.execute_script(
                            f'document.evaluate("//*[@id=\'QuestionPane{str(question)}\']/div[1]/div[2]/a[{str(random.randint(1, 3))}]/div", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click()'
                        )
                        time.sleep(8)
                        self.home_page.update_points_counter(
                            self.get_points_from_bing(browser, account, False)
                        )
                    time.sleep(5)
                    browser.close()
                    time.sleep(2)
                    browser.switch_to.window(
                        window_name=browser.window_handles[0]
                    )
                    time.sleep(2)
                    return
                except NoSuchElementException:
                    time.sleep(self.calculate_sleep(random.randint(5, 9)))
                    browser.close()
                    time.sleep(2)
                    browser.switch_to.window(
                        window_name=browser.window_handles[0]
                    )
                    time.sleep(2)
                    return
            time.sleep(3)
            correctAnswer = browser.execute_script(
                'return _w.rewardsQuizRenderInfo.correctAnswer'
            )
            if (
                browser.find_element(By.ID, 'rqAnswerOption0').get_attribute(
                    'data-option'
                )
                == correctAnswer
            ):
                browser.find_element(By.ID, 'rqAnswerOption0').click()
            else:
                browser.find_element(By.ID, 'rqAnswerOption1').click()
            time.sleep(10)
            points = self.get_points_from_bing(browser, account, False)
            account.points_counter = points
            self.home_page.update_points_counter(points)
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        def complete_daily_set_this_or_that(_activity: dict):
            time.sleep(2)
            card = self.locate_rewards_card(browser, _activity)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(15))
            # Accept cookie popup
            if self.is_element_exists(browser, By.ID, 'bnp_container'):
                browser.find_element(By.ID, 'bnp_btn_accept').click()
                time.sleep(2)
            if not self.wait_until_quiz_loads(browser):
                self.reset_tabs(browser)
                return
            browser.find_element(By.XPATH, '//*[@id="rqStartQuiz"]').click()
            self.wait_until_visible(
                browser,
                By.XPATH,
                '//*[@id="currentQuestionContainer"]/div/div[1]',
                10,
            )
            time.sleep(5)
            for _ in range(10):
                # Click on later on Bing wallpaper app popup
                if self.is_element_exists(
                    browser, By.ID, 'b_notificationContainer_bop'
                ):
                    browser.find_element(By.ID, 'bnp_hfly_cta2').click()
                    time.sleep(2)

                answerEncodeKey = browser.execute_script('return _G.IG')
                self.wait_until_visible(browser, By.ID, 'rqAnswerOption0', 25)
                answer1 = browser.find_element(By.ID, 'rqAnswerOption0')
                answer1Title = answer1.get_attribute('data-option')
                answer1Code = self.get_answer_code(
                    answerEncodeKey, answer1Title
                )

                answer2 = browser.find_element(By.ID, 'rqAnswerOption1')
                answer2Title = answer2.get_attribute('data-option')
                answer2Code = self.get_answer_code(
                    answerEncodeKey, answer2Title
                )

                correctAnswerCode = browser.execute_script(
                    'return _w.rewardsQuizRenderInfo.correctAnswer'
                )

                self.wait_until_clickable(
                    browser, By.ID, 'rqAnswerOption0', 25
                )
                if answer1Code == correctAnswerCode:
                    answer1.click()
                    time.sleep(self.calculate_sleep(15))
                elif answer2Code == correctAnswerCode:
                    answer2.click()
                    time.sleep(self.calculate_sleep(15))
                points = self.get_points_from_bing(browser, account, False)
                account.points_counter = points
                self.home_page.update_points_counter(points)

            time.sleep(5)
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        self.home_page.update_section('Daily Set')
        d = self.get_dashboard_data(browser)
        todayDate = datetime.today().strftime('%m/%d/%Y')
        todayPack = []
        for date, data in d['dailySetPromotions'].items():
            if date == todayDate:
                todayPack = data
        for activity in todayPack:
            try:
                if activity['complete'] == False:
                    cardNumber = int(activity['offerId'][-1:])
                    if activity['promotionType'] == 'urlreward':
                        self.home_page.update_detail(
                            f'Search of card {str(cardNumber)}'
                        )
                        complete_daily_set_search(activity)
                    if activity['promotionType'] == 'quiz':
                        if (
                            activity['pointProgressMax'] == 50
                            and activity['pointProgress'] == 0
                        ):
                            self.home_page.update_detail(
                                f'This or That of card {str(cardNumber)}'
                            )
                            complete_daily_set_this_or_that(activity)
                        elif (
                            activity['pointProgressMax'] == 40
                            or activity['pointProgressMax'] == 30
                        ) and activity['pointProgress'] == 0:
                            self.home_page.update_detail(
                                f'Quiz of card {str(cardNumber)}'
                            )
                            complete_daily_set_quiz(activity)
                        elif (
                            activity['pointProgressMax'] == 10
                            and activity['pointProgress'] == 0
                        ):
                            searchUrl = urllib.parse.unquote(
                                urllib.parse.parse_qs(
                                    urllib.parse.urlparse(
                                        activity['destinationUrl']
                                    ).query
                                )['ru'][0]
                            )
                            searchUrlQueries = urllib.parse.parse_qs(
                                urllib.parse.urlparse(searchUrl).query
                            )
                            filters = {}
                            for filter in searchUrlQueries['filters'][0].split(
                                ' '
                            ):
                                filter = filter.split(':', 1)
                                filters[filter[0]] = filter[1]
                            if 'PollScenarioId' in filters:
                                self.home_page.update_detail(
                                    f'Poll of card {str(cardNumber)}'
                                )
                                complete_daily_set_survey(activity)
                            else:
                                self.home_page.update_detail(
                                    f'Quiz of card {str(cardNumber)}'
                                )
                                complete_daily_set_variable_activity(activity)
            except Exception as e:
                if self.page.client_storage.get('MRFarmer.save_errors'):
                    self.save_errors(e)
                self.reset_tabs(browser)
        account.update_value_in_log('Daily', True)
        self.update_accounts()

    def complete_punch_cards(self, browser: WebDriver, account: Account):
        """Complete punch cards"""

        def complete_punch_card(url: str, childPromotions: dict):
            self.go_to_url(browser, url=url)
            for child in childPromotions:
                if child['complete'] == False:
                    if child['promotionType'] == 'urlreward':
                        browser.execute_script(
                            "document.getElementsByClassName('offer-cta')[0].click()"
                        )
                        time.sleep(1)
                        browser.switch_to.window(
                            window_name=browser.window_handles[1]
                        )
                        time.sleep(random.randint(13, 17))
                        browser.close()
                        time.sleep(2)
                        browser.switch_to.window(
                            window_name=browser.window_handles[0]
                        )
                        time.sleep(2)
                    if (
                        child['promotionType'] == 'quiz'
                        and child['pointProgressMax'] >= 50
                    ):
                        browser.find_element(
                            By.XPATH,
                            '//*[@id="rewards-dashboard-punchcard-details"]/div[2]/div[2]/div[7]/div[3]/div[1]/a',
                        ).click()
                        time.sleep(1)
                        browser.switch_to.window(
                            window_name=browser.window_handles[1]
                        )
                        time.sleep(self.calculate_sleep(15))
                        try:
                            self.wait_until_visible(
                                browser, By.XPATH, '//*[@id="rqStartQuiz"]'
                            )
                            self.wait_until_clickable(
                                browser, By.XPATH, '//*[@id="rqStartQuiz"]'
                            )
                            browser.find_element(
                                By.XPATH, '//*[@id="rqStartQuiz"]'
                            ).click()
                        except:
                            pass
                        time.sleep(self.calculate_sleep(6))
                        self.wait_until_visible(
                            browser,
                            By.XPATH,
                            '//*[@id="currentQuestionContainer"]',
                            10,
                        )
                        numberOfQuestions = browser.execute_script(
                            'return _w.rewardsQuizRenderInfo.maxQuestions'
                        )
                        AnswerdQuestions = browser.execute_script(
                            'return _w.rewardsQuizRenderInfo.CorrectlyAnsweredQuestionCount'
                        )
                        numberOfQuestions -= AnswerdQuestions
                        for question in range(numberOfQuestions):
                            answer = browser.execute_script(
                                'return _w.rewardsQuizRenderInfo.correctAnswer'
                            )
                            self.wait_until_clickable(
                                browser,
                                By.XPATH,
                                f'//input[@value="{answer}"]',
                            )
                            browser.find_element(
                                By.XPATH, f'//input[@value="{answer}"]'
                            ).click()
                            time.sleep(self.calculate_sleep(15))
                        time.sleep(5)
                        browser.close()
                        time.sleep(2)
                        browser.switch_to.window(
                            window_name=browser.window_handles[0]
                        )
                        time.sleep(2)
                        browser.refresh()
                        break
                    elif (
                        child['promotionType'] == 'quiz'
                        and child['pointProgressMax'] < 50
                    ):
                        browser.execute_script(
                            "document.getElementsByClassName('offer-cta')[0].click()"
                        )
                        time.sleep(1)
                        browser.switch_to.window(
                            window_name=browser.window_handles[1]
                        )
                        time.sleep(self.calculate_sleep(8))
                        self.wait_until_visible(
                            browser,
                            By.XPATH,
                            '//*[@id="QuestionPane0"]/div[2]',
                            15,
                        )
                        counter = str(
                            browser.find_element(
                                By.XPATH, '//*[@id="QuestionPane0"]/div[2]'
                            ).get_attribute('innerHTML')
                        )[:-1][1:]
                        numberOfQuestions = max(
                            [int(s) for s in counter.split() if s.isdigit()]
                        )
                        for question in range(numberOfQuestions):
                            browser.execute_script(
                                'document.evaluate("//*[@id=\'QuestionPane'
                                + str(question)
                                + "']/div[1]/div[2]/a["
                                + str(random.randint(1, 3))
                                + ']/div", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click()'
                            )
                            time.sleep(10)
                        time.sleep(5)
                        browser.close()
                        time.sleep(2)
                        browser.switch_to.window(
                            window_name=browser.window_handles[0]
                        )
                        time.sleep(2)
                        browser.refresh()
                        break

        punchCards = self.get_dashboard_data(browser)['punchCards']
        self.home_page.update_section('Punch cards')
        self.home_page.update_detail('-')
        for punchCard in punchCards:
            try:
                if (
                    punchCard['parentPromotion'] != None
                    and punchCard['childPromotions'] != None
                    and punchCard['parentPromotion']['complete'] == False
                    and punchCard['parentPromotion']['pointProgressMax'] != 0
                ):
                    url = punchCard['parentPromotion']['attributes'][
                        'destination'
                    ]
                    complete_punch_card(url, punchCard['childPromotions'])
            except Exception as e:
                if self.page.client_storage.get('MRFarmer.save_errors'):
                    self.save_errors(e)
                self.reset_tabs(browser)
        time.sleep(2)
        self.go_to_url(browser, self.base_url)
        time.sleep(2)
        account.update_value_in_log('Punch cards', True)
        self.update_accounts()

    def complete_more_promotions(self, browser: WebDriver, account: Account):
        """Complete more activites"""

        def complete_more_promotion_search(_promotion: dict):
            card = self.locate_rewards_card(browser, _promotion)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(random.randint(13, 17)))
            points = self.get_points_from_bing(browser, account, False)
            account.points_counter = points
            self.home_page.update_points_counter(points)
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        def complete_more_promotion_quiz(_promotion: dict):
            card = self.locate_rewards_card(browser, _promotion)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(8))
            if not self.wait_until_quiz_loads(browser):
                self.reset_tabs(browser)
                return
            CurrentQuestionNumber = browser.execute_script(
                'return _w.rewardsQuizRenderInfo.currentQuestionNumber'
            )
            if CurrentQuestionNumber == 1 and self.is_element_exists(
                browser, By.XPATH, '//*[@id="rqStartQuiz"]'
            ):
                self.wait_until_clickable(
                    browser, By.XPATH, '//*[@id="rqStartQuiz"]', 25
                )
                time.sleep(2)
                browser.find_element(
                    By.XPATH, '//*[@id="rqStartQuiz"]'
                ).click()
            self.wait_until_visible(
                browser,
                By.XPATH,
                '//*[@id="currentQuestionContainer"]/div/div[1]',
                25,
            )
            time.sleep(3)
            numberOfQuestions = browser.execute_script(
                'return _w.rewardsQuizRenderInfo.maxQuestions'
            )
            Questions = numberOfQuestions - CurrentQuestionNumber + 1
            numberOfOptions = browser.execute_script(
                'return _w.rewardsQuizRenderInfo.numberOfOptions'
            )
            for _ in range(Questions):
                if numberOfOptions == 8:
                    answers = []
                    for i in range(8):
                        if (
                            browser.find_element(
                                By.ID, 'rqAnswerOption' + str(i)
                            )
                            .get_attribute('iscorrectoption')
                            .lower()
                            == 'true'
                        ):
                            answers.append('rqAnswerOption' + str(i))
                    for answer in answers:
                        self.wait_until_visible(browser, By.ID, answer, 30)
                        browser.find_element(By.ID, answer).click()
                        time.sleep(self.calculate_sleep(7))
                        if not self.wait_until_question_refresh(browser):
                            return
                    time.sleep(5)
                elif numberOfOptions == 4:
                    correctOption = browser.execute_script(
                        'return _w.rewardsQuizRenderInfo.correctAnswer'
                    )
                    for i in range(4):
                        if (
                            browser.find_element(
                                By.ID, 'rqAnswerOption' + str(i)
                            ).get_attribute('data-option')
                            == correctOption
                        ):
                            self.wait_until_visible(
                                browser, By.ID, 'rqAnswerOption' + str(i), 30
                            )
                            browser.find_element(
                                By.ID, 'rqAnswerOption' + str(i)
                            ).click()
                            time.sleep(self.calculate_sleep(6))
                            if not self.wait_until_question_refresh(browser):
                                return
                            break
                    time.sleep(5)
                self.home_page.update_points_counter(
                    self.get_points_from_bing(browser, account, False)
                )
            time.sleep(self.calculate_sleep(6))
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        def complete_more_promotion_ABC(_promotion: dict):
            card = self.locate_rewards_card(browser, _promotion)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(8))
            self.wait_until_visible(
                browser, By.XPATH, '//*[@id="QuestionPane0"]/div[2]', 25
            )
            counter = str(
                browser.find_element(
                    By.XPATH, '//*[@id="QuestionPane0"]/div[2]'
                ).get_attribute('innerHTML')
            )[:-1][1:]
            numberOfQuestions = max(
                [int(s) for s in counter.split() if s.isdigit()]
            )
            for question in range(numberOfQuestions):
                browser.execute_script(
                    f'document.evaluate("//*[@id=\'QuestionPane{str(question)}\']/div[1]/div[2]/a[{str(random.randint(1, 3))}]/div", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click()'
                )
                time.sleep(self.calculate_sleep(8) + 3)
            time.sleep(5)
            self.home_page.update_points_counter(
                self.get_points_from_bing(browser, account, False)
            )
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        def complete_more_promotion_this_or_that(_promotion: dict):
            card = self.locate_rewards_card(browser, _promotion)
            card.click()
            time.sleep(1)
            browser.switch_to.window(window_name=browser.window_handles[1])
            time.sleep(self.calculate_sleep(8))
            if not self.wait_until_quiz_loads(browser):
                self.reset_tabs(browser)
                return
            CrrentQuestionNumber = browser.execute_script(
                'return _w.rewardsQuizRenderInfo.currentQuestionNumber'
            )
            NumberOfQuestionsLeft = 10 - CrrentQuestionNumber + 1
            if CrrentQuestionNumber == 1 and self.is_element_exists(
                browser, By.XPATH, '//*[@id="rqStartQuiz"]'
            ):
                self.wait_until_clickable(
                    browser, By.XPATH, '//*[@id="rqStartQuiz"]', 25
                )
                browser.find_element(
                    By.XPATH, '//*[@id="rqStartQuiz"]'
                ).click()
            self.wait_until_visible(
                browser,
                By.XPATH,
                '//*[@id="currentQuestionContainer"]/div/div[1]',
                10,
            )
            time.sleep(3)
            for _ in range(NumberOfQuestionsLeft):
                answerEncodeKey = browser.execute_script('return _G.IG')
                self.wait_until_visible(browser, By.ID, 'rqAnswerOption0', 25)
                answer1 = browser.find_element(By.ID, 'rqAnswerOption0')
                answer1Title = answer1.get_attribute('data-option')
                answer1Code = self.get_answer_code(
                    answerEncodeKey, answer1Title
                )

                answer2 = browser.find_element(By.ID, 'rqAnswerOption1')
                answer2Title = answer2.get_attribute('data-option')
                answer2Code = self.get_answer_code(
                    answerEncodeKey, answer2Title
                )

                correctAnswerCode = browser.execute_script(
                    'return _w.rewardsQuizRenderInfo.correctAnswer'
                )

                self.wait_until_clickable(
                    browser, By.ID, 'rqAnswerOption0', 25
                )
                if answer1Code == correctAnswerCode:
                    answer1.click()
                    time.sleep(self.calculate_sleep(random.uniform(8, 10)))
                elif answer2Code == correctAnswerCode:
                    answer2.click()
                    time.sleep(self.calculate_sleep(random.uniform(8, 10)))
                points = self.get_points_from_bing(browser, account, False)
                account.points_counter = points
                self.home_page.update_points_counter(points)

            time.sleep(5)
            browser.close()
            time.sleep(2)
            browser.switch_to.window(window_name=browser.window_handles[0])
            time.sleep(2)

        def complete_promotional_items():
            try:
                self.home_page.update_detail('Promotional items')
                item = self.get_dashboard_data(browser)['promotionalItem']
                if (
                    (
                        item['pointProgressMax'] == 100
                        or item['pointProgressMax'] == 200
                    )
                    and item['complete'] == False
                    and item['destinationUrl'] == self.base_url
                ):
                    browser.find_element(
                        By.XPATH, '//*[@id="promo-item"]/section/div/div/div/a'
                    ).click()
                    time.sleep(1)
                    browser.switch_to.window(
                        window_name=browser.window_handles[1]
                    )
                    time.sleep(8)
                    points = self.get_points_from_bing(browser, account, False)
                    account.points_counter = points
                    self.home_page.update_points_counter(points)
                    browser.close()
                    time.sleep(2)
                    browser.switch_to.window(
                        window_name=browser.window_handles[0]
                    )
                    time.sleep(2)
            except:
                pass

        self.home_page.update_section('More activities')
        morePromotions = self.get_dashboard_data(browser)['morePromotions']
        i = 0
        for promotion in morePromotions:
            try:
                i += 1
                if (
                    promotion['complete'] == False
                    and promotion['pointProgressMax'] != 0
                ):
                    if promotion['promotionType'] == 'urlreward':
                        self.home_page.update_detail('Search card')
                        complete_more_promotion_search(promotion)
                    elif promotion['promotionType'] == 'quiz':
                        if promotion['pointProgressMax'] == 10:
                            self.home_page.update_detail('ABC card')
                            complete_more_promotion_ABC(promotion)
                        elif (
                            promotion['pointProgressMax'] == 30
                            or promotion['pointProgressMax'] == 40
                        ):
                            self.home_page.update_detail('Quiz card')
                            complete_more_promotion_quiz(promotion)
                        elif promotion['pointProgressMax'] == 50:
                            self.home_page.update_detail('This or that card')
                            complete_more_promotion_this_or_that(promotion)
                    else:
                        if (
                            promotion['pointProgressMax'] == 100
                            or promotion['pointProgressMax'] == 200
                        ):
                            self.home_page.update_detail('Search card')
                            complete_more_promotion_search(promotion)
                if (
                    promotion['complete'] == False
                    and promotion['pointProgressMax'] == 100
                    and promotion['promotionType'] == ''
                    and promotion['destinationUrl'] == self.base_url
                ):
                    self.home_page.update_detail('Search card')
                    complete_more_promotion_search(promotion)
            except Exception as e:
                if self.page.client_storage.get('MRFarmer.save_errors'):
                    self.save_errors(e)
                self.reset_tabs(browser)

        complete_promotional_items()
        self.home_page.update_section('-')
        self.home_page.update_detail('-')
        account.update_value_in_log('More promotions', True)
        self.update_accounts()

    def complete_msn_shopping_game_quiz(
        self, browser: WebDriver, account: Account
    ):
        def expand_shadow_element(
            element, index: int = None
        ) -> Union[List[WebElement], WebElement]:
            """Returns childrens of shadow element, if index provided it returns the element at that index"""
            if index is not None:
                shadow_root = WebDriverWait(browser, 45).until(
                    EC.visibility_of(
                        browser.execute_script(
                            'return arguments[0].shadowRoot.children', element
                        )[index]
                    )
                )
            else:
                # wait to visible one element then get the list
                WebDriverWait(browser, 45).until(
                    EC.visibility_of(
                        browser.execute_script(
                            'return arguments[0].shadowRoot.children', element
                        )[0]
                    )
                )
                shadow_root = browser.execute_script(
                    'return arguments[0].shadowRoot.children', element
                )
            return shadow_root

        def get_children(element) -> List[WebElement]:
            children = browser.execute_script(
                'return arguments[0].children', element
            )
            return children

        def get_sign_in_button() -> WebElement:
            """check wheather user is signed in or not and return the button to sign in"""
            script_to_user_pref_container = 'document.getElementsByTagName("shopping-page-base")[0]\
                .shadowRoot.children[0].children[1].children[0]\
                .shadowRoot.children[0].shadowRoot.children[0]\
                .getElementsByClassName("user-pref-container")[0]'
            WebDriverWait(browser, 60).until(
                EC.visibility_of(
                    browser.execute_script(
                        f'return {script_to_user_pref_container}'
                    )
                )
            )
            button = WebDriverWait(browser, 60).until(
                EC.visibility_of(
                    browser.execute_script(
                        f'return {script_to_user_pref_container}.\
                        children[0].children[0].shadowRoot.children[0].\
                        getElementsByClassName("me-control")[0]'
                    )
                )
            )
            return button

        def sign_in():
            self.home_page.update_detail('Signing in')
            sign_in_button = get_sign_in_button()
            sign_in_button.click()
            time.sleep(5)
            self.wait_until_visible(browser, By.ID, 'newSessionLink', 10)
            browser.find_element(By.ID, 'newSessionLink').click()
            self.answer_to_security_info_update(browser)
            self.home_page.update_detail('Waiting for elements')
            self.wait_until_visible(
                browser, By.TAG_NAME, 'shopping-page-base', 60
            )
            expand_shadow_element(
                browser.find_element(By.TAG_NAME, 'shopping-page-base'), 0
            )
            self.home_page.update_detail('Checking signed in state')
            get_sign_in_button()
            time.sleep(self.calculate_sleep(10))

        def get_gaming_card() -> Union[WebElement, Literal[False]]:
            shopping_page_base_childs = expand_shadow_element(
                browser.find_element(By.TAG_NAME, 'shopping-page-base'), 0
            )
            shopping_homepage = shopping_page_base_childs.find_element(
                By.TAG_NAME, 'shopping-homepage'
            )
            msft_feed_layout = expand_shadow_element(
                shopping_homepage, 0
            ).find_element(By.TAG_NAME, 'msft-feed-layout')
            cards = expand_shadow_element(msft_feed_layout)
            for card in cards:
                if card.get_attribute('gamestate') == 'active':
                    browser.execute_script(
                        'arguments[0].scrollIntoView();', card
                    )
                    return card
                elif card.get_attribute('gamestate') == 'idle':
                    browser.execute_script(
                        'arguments[0].scrollIntoView();', card
                    )
                    raise GamingCardIsNotActive
            else:
                return False

        def click_correct_answer():
            options_container = expand_shadow_element(gaming_card, 1)
            options_elements = get_children(get_children(options_container)[1])
            # click on the correct answer in options_elements
            correct_answer = options_elements[
                int(gaming_card.get_attribute('_correctAnswerIndex'))
            ]
            # click to show the select button
            correct_answer.click()
            time.sleep(1)
            # click 'select' button
            select_button = correct_answer.find_element(
                By.CLASS_NAME, 'shopping-select-overlay-button'
            )
            WebDriverWait(browser, 5).until(
                EC.element_to_be_clickable(select_button)
            )
            select_button.click()

        def click_play_again():
            time.sleep(random.randint(4, 6))
            options_container = expand_shadow_element(gaming_card)[1]
            get_children(options_container)[0].find_element(
                By.TAG_NAME, 'button'
            ).click()

        try:
            tries = 0
            while tries <= 4:
                tries += 1
                self.home_page.update_section(
                    f'MSN shopping game - try ({tries})'
                )
                self.go_to_url(browser, 'https://www.msn.com/en-us/shopping')
                self.home_page.update_detail('Waiting for elements')
                self.wait_until_visible(
                    browser, By.TAG_NAME, 'shopping-page-base', 60
                )
                time.sleep(15)
                self.home_page.update_detail('Waiting for sign in state')
                try:
                    sign_in_button = get_sign_in_button()
                except:
                    if tries == 4:
                        raise ElementNotVisibleException(
                            'Sign in button did not show up'
                        )
                else:
                    break
            self.home_page.update_section(f'MSN shopping game')
            time.sleep(self.calculate_sleep(5))
            if 'Sign in' in sign_in_button.text:
                sign_in()
            self.home_page.update_detail('Locating gaming card')
            gaming_card = get_gaming_card()
            scrolls = 0
            while not gaming_card and scrolls <= 5:
                scrolls += 1
                self.home_page.update_detail(
                    f'Locating gaming card - scrolling ({scrolls}/5)'
                )
                browser.execute_script('window.scrollBy(0, 300);')
                time.sleep(10)
                gaming_card = get_gaming_card()
                if gaming_card:
                    break
                if scrolls == 5 and not gaming_card:
                    raise GamingCardNotFound('Gaming card not found')
            self.home_page.update_detail('Gaming card found')
            time.sleep(self.calculate_sleep(random.randint(7, 10)))
            for question in range(10):
                try:
                    self.home_page.update_detail(
                        f'Answering questions ({question + 1}/10)'
                    )
                    click_correct_answer()
                    click_play_again()
                    time.sleep(random.randint(5, 7))
                except (NoSuchElementException, JavascriptException):
                    break
        except GamingCardNotFound:
            self.home_page.update_detail('Gaming card not found')
        except GamingCardIsNotActive:
            self.home_page.update_detail('Already completed')
            time.sleep(self.calculate_sleep(10))
        except Exception as e:
            if self.page.client_storage.get('MRFarmer.save_errors'):
                self.save_errors(e)
            self.home_page.update_detail('Failed to complete')
        else:
            self.home_page.update_detail('Completed')
        finally:
            self.go_to_url(browser, self.base_url)
            account.update_value_in_log('MSN shopping game', True)
            self.update_accounts()
            self.home_page.update_section('-')
            self.home_page.update_detail('-')
            self.wait_until_visible(browser, By.ID, 'app-host', 30)
            account.points_counter = self.get_account_points(browser)
            self.home_page.update_points_counter(account.points_counter)

    def get_remaining_searches(self, browser: WebDriver):
        dashboard = self.get_dashboard_data(browser)
        searchPoints = 1
        counters = dashboard['userStatus']['counters']
        if not 'pcSearch' in counters:
            return 0, 0
        progressDesktop = (
            counters['pcSearch'][0]['pointProgress']
            + counters['pcSearch'][1]['pointProgress']
        )
        targetDesktop = (
            counters['pcSearch'][0]['pointProgressMax']
            + counters['pcSearch'][1]['pointProgressMax']
        )
        if targetDesktop == 33:
            # Level 1 EU
            searchPoints = 3
        elif targetDesktop == 55:
            # Level 1 US
            searchPoints = 5
        elif targetDesktop == 102:
            # Level 2 EU
            searchPoints = 3
        elif targetDesktop >= 170:
            # Level 2 US
            searchPoints = 5
        remainingDesktop = int(
            (targetDesktop - progressDesktop) / searchPoints
        )
        remainingMobile = 0
        if dashboard['userStatus']['levelInfo']['activeLevel'] != 'Level1':
            progressMobile = counters['mobileSearch'][0]['pointProgress']
            targetMobile = counters['mobileSearch'][0]['pointProgressMax']
            remainingMobile = int(
                (targetMobile - progressMobile) / searchPoints
            )
        return remainingDesktop, remainingMobile

    def get_points_from_bing(
        self, browser: WebDriver, account: Account, isMobile: bool = False
    ):
        try:
            if not isMobile:
                try:
                    points = int(
                        browser.find_element(By.ID, 'id_rc').get_attribute(
                            'innerHTML'
                        )
                    )
                except ValueError:
                    points = int(
                        browser.find_element(By.ID, 'id_rc')
                        .get_attribute('innerHTML')
                        .replace(',', '')
                    )
            else:
                try:
                    browser.find_element(By.ID, 'mHamburger').click()
                except UnexpectedAlertPresentException:
                    try:
                        browser.switch_to.alert.accept()
                        time.sleep(1)
                        browser.find_element(By.ID, 'mHamburger').click()
                    except NoAlertPresentException:
                        pass
                time.sleep(1)
                points = int(
                    browser.find_element(By.ID, 'fly_id_rc').get_attribute(
                        'innerHTML'
                    )
                )
        except:
            points = account.points_counter
        finally:
            if points < account.points_counter:
                points = account.points_counter
        return points

    def disable_stop_button(self, state: bool):
        self.home_page.stop_button.disabled = state
        self.page.update()

    def save_errors(self, e: Exception):
        tb = e.__traceback__
        tb_str = traceback.format_tb(tb)
        error = '\n'.join(tb_str).strip() + f'\n{e}'
        with open(resource_path('errors.txt', True), 'a') as f:
            f.write(
                f'\n-------------------{datetime.now()}-------------------\r\n'
            )
            f.write(f'{error}\n')

    def perform_run(self):
        """Check whether timer is set to run it at time else run immediately"""
        if self.page.client_storage.get('MRFarmer.timer_switch'):
            requested_time = self.page.client_storage.get('MRFarmer.timer')
            self.home_page.update_section(f'Waiting for {requested_time}')
            self.home_page.update_overall_infos()
            while datetime.now().strftime('%H:%M') != requested_time:
                if not self.parent.is_farmer_running:
                    return None
                time.sleep(1)
            else:
                self.get_or_create_logs()
                return self.run()
        self.get_or_create_logs()
        return self.run()

    def run(self):
        for account in self.accounts:
            delta_date = (
                date.today()
                - datetime.strptime(account.last_check, '%Y-%m-%d').date()
            ).days
            while self.parent.get_farming_status():
                try:
                    self.current_account = account
                    self.account_index = self.accounts.index(account)
                    if (
                        account.username in self.finished_accounts
                        or account.username in self.suspended_accounts
                    ):
                        break
                    if account.last_check != str(date.today()):
                        account.last_check = str(date.today())
                        self.update_accounts()
                    self.home_page.update_current_account(account.username)
                    self.home_page.update_overall_infos()
                    if account.is_pc_need():
                        browser = self.browser_setup(account, False)
                        self.browser = browser
                        self.disable_stop_button(False)
                        self.login(browser, account, False)
                        self.home_page.update_detail('Logged in')
                        self.go_to_url(browser, self.base_url)
                        self.wait_until_visible(browser, By.ID, 'app-host', 30)

                        if self.page.client_storage.get(
                            'MRFarmer.daily_quests'
                        ) and not account.get_log_value('Daily'):
                            self.complete_daily_set(browser, account)

                        if self.page.client_storage.get(
                            'MRFarmer.punch_cards'
                        ) and not account.get_log_value('Punch cards'):
                            self.complete_punch_cards(browser, account)

                        if self.page.client_storage.get(
                            'MRFarmer.more_activities'
                        ) and not account.get_log_value('More promotions'):
                            self.complete_more_promotions(browser, account)

                        if self.page.client_storage.get(
                            'MRFarmer.msn_shopping_game'
                        ) and not account.get_log_value('MSN shopping game'):
                            self.complete_msn_shopping_game_quiz(
                                browser, account
                            )

                        if self.page.client_storage.get(
                            'MRFarmer.pc_search'
                        ) and not account.get_log_value('PC searches'):
                            (
                                account.pc_remaining_searches,
                                account.mobile_remaining_searches,
                            ) = self.get_remaining_searches(browser)
                            if account.pc_remaining_searches > 0:
                                self.bing_searches(browser, account, False)
                            account.update_value_in_log('PC searches', True)
                            self.update_accounts()

                        self.disable_stop_button(True)
                        browser.quit()
                        self.browser = None
                        self.home_page.update_detail('-')
                        self.home_page.update_section('-')

                    if account.is_mobile_need():
                        browser = self.browser_setup(account, True)
                        self.browser = browser
                        self.disable_stop_button(False)
                        self.login(browser, account, True)
                        if account.mobile_remaining_searches > 0:
                            self.bing_searches(browser, account, True)
                        account.update_value_in_log('Mobile searches', True)
                        self.update_accounts()
                        self.disable_stop_button(True)
                        browser.quit()

                    self.home_page.update_detail('-')
                    self.home_page.update_section('-')
                    self.home_page.update_points_counter(0)

                    self.finished_accounts.append(account.username)
                    account.finish()

                    self.accounts_list[account.index] = account.get_dict()
                    self.update_accounts()
                    self.accounts_page.sync_accounts()

                    self.home_page.update_points_counter(0)
                    self.home_page.update_overall_infos()
                    self.home_page.update_proxy('-')
                    break

                except ProxyIsDeadException:
                    browser.quit()
                    self.browser = None
                    account.status = accountStatus.PROXY_DEAD
                    self.failed_accounts.append(account.username)
                    account.clean_log()
                    self.update_accounts()
                    self.accounts_page.sync_accounts()
                    self.accounts_list[account.index] = account.get_dict()
                    self.home_page.update_overall_infos()
                    self.home_page.update_proxy('-')
                    break

                except AccountLockedException:
                    browser.quit()
                    self.browser = None
                    account.status = accountStatus.LOCKED
                    self.locked_accounts.append(account.status)
                    self.update_accounts()
                    self.accounts_page.sync_accounts()
                    account.clean_log()
                    self.accounts_list[account.index] = account.get_dict()
                    self.home_page.update_overall_infos()
                    self.home_page.update_proxy('-')
                    break

                except AccountSuspendedException:
                    browser.quit()
                    self.browser = None
                    self.suspended_accounts.append(account.username)
                    account.status = accountStatus.SUSPENDED
                    account.earned_points = 'N/A'
                    account.points = 'N/A'
                    account.clean_log()
                    self.accounts_list[account.index] = account.get_dict()
                    self.accounts_page.sync_accounts()
                    self.home_page.update_overall_infos()
                    self.home_page.update_proxy('-')
                    break

                except UnusualActivityException:
                    browser.quit()
                    self.browser = None
                    account.status = accountStatus.UNUSUAL_ACTIVITY
                    self.failed_accounts.append(account.username)
                    self.update_accounts()
                    self.accounts_page.sync_accounts()
                    account.clean_log()
                    self.accounts_list[account.index] = account.get_dict()
                    self.home_page.finished()
                    self.home_page.update_proxy('-')
                    return None

                except RegionException:
                    browser.quit()
                    self.home_page.finished()
                    self.home_page.update_section(
                        'Not available in your region'
                    )
                    return None

                except GetSearchWordsException:
                    browser.quit()
                    self.browser = None
                    account.status = accountStatus.SEARCH_WORDS_ERROR
                    self.failed_accounts.append(account.username)
                    self.update_accounts()
                    self.accounts_page.sync_accounts()
                    account.clean_log()
                    self.accounts_list[account.index] = account.get_dict()
                    self.home_page.update_proxy('-')
                    break

                except LoginFailedException as e:
                    browser.quit()
                    self.browser = None
                    if e.isMobile:
                        account.status = accountStatus.MOBILE_LOGIN_FAILED
                    else:
                        account.status = accountStatus.PC_LOGIN_FAILED
                    self.failed_accounts.append(account.username)
                    if account.starting_points != -1:
                        account.earned_points = (
                            account.points_counter - account.starting_points
                        )
                        account.points = account.points_counter
                    self.update_accounts()
                    self.accounts_page.sync_accounts()
                    account.clean_log()
                    self.accounts_list[account.index] = account.get_dict()
                    if self.page.client_storage.get('MRFarmer.save_errors'):
                        self.save_errors(e)
                    self.home_page.update_proxy('-')
                    break

                except UnhandledException:
                    browser.quit()
                    self.browser = None
                    account.status = accountStatus.ERROR
                    if account.points_counter != -1:
                        account.points = account.points_counter
                        account.earned_points = (
                            account.points_counter - account.starting_points
                        )
                    self.failed_accounts.append(account.username)
                    self.update_accounts()
                    self.accounts_page.sync_accounts()
                    account.clean_log()
                    self.accounts_list[account.index] = account.get_dict()
                    self.home_page.update_proxy('-')
                    break

                except (
                    InvalidSessionIdException,
                    MaxRetryError,
                    NewConnectionError,
                ):
                    try:
                        browser.quit()
                    except:
                        pass
                    self.browser = None
                    if not self.parent.is_farmer_running:
                        self.home_page.finished()
                        return None
                    internet = self.check_internet_connection()
                    if internet:
                        pass
                    else:
                        self.home_page.finished()
                        return None

                except SessionNotCreatedException:
                    self.browser = None
                    self.home_page.update_section('Webdriver error')
                    self.home_page.update_detail('Webdriver has outdated')
                    self.parent.display_error(
                        'Webdriver error',
                        'Webdriver has outdated. Please update your Webdriver.',
                    )
                    self.home_page.finished()
                    return None

                except (Exception, FunctionTimedOut) as e:
                    if 'executable needs to be in PATH' in str(e):
                        self.parent.display_error('Webdriver error', str(e))
                        self.home_page.finished()
                        return None
                    try:
                        browser.quit()
                    except:
                        pass
                    self.starting_points = None
                    self.browser = None
                    if self.page.client_storage.get('MRFarmer.save_errors'):
                        self.save_errors(e)
                    internet = self.check_internet_connection()
                    if internet:
                        pass
                    else:
                        self.home_page.finished()
                        return None
            else:
                return
        else:
            self.update_accounts()
            self.home_page.update_overall_infos()
            if self.page.client_storage.get(
                'MRFarmer.send_to_telegram'
            ) or self.page.client_storage.get('MRFarmer.send_to_discord'):
                message = self.create_message()
                self.send_report_to_messenger(message)
            if self.page.client_storage.get('MRFarmer.shutdown'):
                os.system('shutdown /s /t 10')
            self.home_page.finished()
