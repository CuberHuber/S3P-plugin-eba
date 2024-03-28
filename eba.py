"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import logging
import time
import urllib.request
from io import StringIO, BytesIO

import dateparser
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from src.spp.types import SPP_document


class Eba:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'eba'
    HOST = "https://www.abe-eba.eu/publications/"
    _content_document: list[SPP_document]

    def __init__(self, webdriver, max_count_documents: int = None, last_document: SPP_document = None, webdriverwait: int = 20, isextracttext: bool = False, *args, **kwargs):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []
        self._driver = webdriver
        self._max_count_documents = max_count_documents
        self._last_document = last_document
        self._wait = WebDriverWait(self._driver, timeout=webdriverwait)
        self._isextracttext = isextracttext

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        try:
            self._parse()
        except Exception as e:
            self.logger.debug(f'Parsing stopped with error: {e}')
        else:
            self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self, abstract=None):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        self._initial_access_source(self.HOST)
        self._wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, '.publication')))

        publications = self._driver.find_elements(By.XPATH, '//article[contains(@class, \'publication\')]')
        for el in publications:
            try:
                links = el.find_element(By.CLASS_NAME, 'media-body').find_elements(By.TAG_NAME, 'a')
                try:
                    _abstract = el.find_element(By.TAG_NAME, 'h3').find_element(By.TAG_NAME, 'small').text
                except:
                    _abstract = ''
                _title = el.find_element(By.TAG_NAME, 'h3').text.replace(_abstract, '')
                _published = dateparser.parse(el.find_element(By.TAG_NAME, 'h6').text)
            except Exception as e:
                raise NoSuchElementException(
                    'Страница не открывается или ошибка получения обязательных полей') from e
            else:
                _links = []
                for link in links:
                    _url = link.get_attribute('href')
                    _links.append({'name': link.text, 'link': _url})
                    if _url.endswith('.pdf'):
                        document = SPP_document(
                            None,
                            title=_title,
                            abstract=abstract if abstract else None,
                            text=None,
                            web_link=_url,
                            local_link=None,
                            other_data={'links': _links},
                            pub_date=_published,
                            load_date=None,
                        )
                        if self._isextracttext:
                            try:
                                _text = self.extract_text_from_pdf_url(_url)
                            except Exception as e:
                                error = ValueError(
                                    'Текст не получилось извлечь из документа ' + _url)
                                self.logger.debug(error)
                            else:
                                document.text = _text

                        self.find_document(document)
        # ---
        # ========================================
        ...

    def _initial_access_source(self, url: str, delay: int = 2):
        self._driver.get(url)
        self.logger.debug('Entered on web page ' + url)
        time.sleep(delay)
        self._agree_cookie_pass()

    def _agree_cookie_pass(self):
        """
        Метод прожимает кнопку agree на модальном окне
        """
        cookie_agree_xpath = '//*[@id="onetrust-accept-btn-handler"]'

        try:
            cookie_button = self._driver.find_element(By.XPATH, cookie_agree_xpath)
            if WebDriverWait(self._driver, 5).until(ec.element_to_be_clickable(cookie_button)):
                cookie_button.click()
                self.logger.debug(F"Parser pass cookie modal on page: {self._driver.current_url}")
        except NoSuchElementException as e:
            self.logger.debug(f'modal agree not found on page: {self._driver.current_url}')

    @staticmethod
    def _find_document_text_for_logger(doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"

    def find_document(self, _doc: SPP_document):
        """
        Метод для обработки найденного документа источника
        """
        if self._last_document and self._last_document.hash == _doc.hash:
            raise Exception(f"Find already existing document ({self._last_document})")

        if self._max_count_documents and len(self._content_document) >= self._max_count_documents:
            raise Exception(f"Max count articles reached ({self._max_count_documents})")

        self._content_document.append(_doc)
        self.logger.info(self._find_document_text_for_logger(_doc))

    def extract_text_from_pdf_url(self, url, user_agent=None):
        resource_manager = PDFResourceManager()
        fake_file_handle = StringIO()
        converter = TextConverter(resource_manager, fake_file_handle)

        if user_agent == None:
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'

        headers = {'User-Agent': user_agent}
        request = urllib.request.Request(url, data=None, headers=headers)

        response = urllib.request.urlopen(request).read()
        fb = BytesIO(response)

        page_interpreter = PDFPageInterpreter(resource_manager, converter)

        for page in PDFPage.get_pages(fb,
                                      caching=True,
                                      check_extractable=True):
            page_interpreter.process_page(page)

        text = fake_file_handle.getvalue()

        # close open handles
        fb.close()
        converter.close()
        fake_file_handle.close()

        if text:
            # If document has instances of \xa0 replace them with spaces.
            # NOTE: \xa0 is non-breaking space in Latin1 (ISO 8859-1) & chr(160)
            text = text.replace(u'\xa0', u' ')

            return text

