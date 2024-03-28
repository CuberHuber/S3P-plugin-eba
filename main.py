import datetime
from logging import config

import pytz
from selenium import webdriver

from eba import Eba
from src.spp.types import SPP_document

config.fileConfig('dev.logger.conf')


def driver():
    """
    Selenium web driver
    """
    options = webdriver.ChromeOptions()

    # Параметр для того, чтобы браузер не открывался.
    options.add_argument('headless')

    options.add_argument('window-size=1920x1080')
    options.add_argument("disable-gpu")

    return webdriver.Chrome(options)


parser = Eba(driver(), 4, None, isextracttext=True)
docs: list[SPP_document] = parser.content()


print(*docs, sep='\n\r\n')
