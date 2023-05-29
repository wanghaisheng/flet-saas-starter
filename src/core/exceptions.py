from typing import Optional


class AccountSuspendedException(Exception):
    """Exception raised when an account gets suspended."""


class AccountLockedException(Exception):
    """Exception raised when an account gets locked."""


class RegionException(Exception):
    """Exception raised when Microsoft Rewards not available in a region."""


class UnusualActivityException(Exception):
    """Exception raised when Microsoft returns unusual activity detected"""


class UnhandledException(Exception):
    """Exception raised when Microsoft returns unhandled error"""


class GetSearchWordsException(Exception):
    """Exception raised when Microsoft returns error while getting search words"""


class GamingCardNotFound(Exception):
    """Exception raised when Microsoft returns error while locating gaming card failed"""


class GamingCardIsNotActive(Exception):
    """Exception raised when the gaming card is not active"""


class ProxyIsDeadException(Exception):
    """Exception raised when proxy is dead"""


class LoginFailedException(Exception):
    """Exception raised when login failed"""

    def __init__(
        self,
        msg: Optional[str] = None,
        account_name: str = None,
        isMobile: bool = False,
    ) -> None:
        self.msg = msg
        self.account_name = account_name
        self.isMobile = isMobile

    def __str__(self):
        exception_msg = f'Message: {self.msg}\nisMobile: {self.isMobile}\n'
        if self.account_name is not None:
            exception_msg += f'Account: {self.account_name}'
        return exception_msg
