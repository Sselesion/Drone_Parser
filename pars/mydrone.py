import time
from random import randint
from typing import Type

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

from models import *

from .base import Parse
from .regex import PtrnEnum, Regex


class MyDroneParser(Parse):
    def __init__(self) -> None:
        """Инициализирует экземпляр класса AeromotusParser"""
        super().__init__(url="https://mydrone.ru/", idx=3)

        self.request_fabric = {
            # КОМПОНЕНТ -> URL && ПАРАМЕТРЫ ЗАПРОСА
            CompEnum.BATTERY: (
                self.url + "kupit/dji/akkumulyatory/?items_per_page=96",
                {},
            ),
            CompEnum.MICROCONTROLLER: (),
            CompEnum.ELECTRICMOTOR: (
                self.url + "kupit/fpv/komponenty/motory/?items_per_page=96",
                {},
            ),
            CompEnum.MOTORCONTROLLER: (),
            CompEnum.FLIGHTCONTROLLER: (
                self.url
                + "kupit/fpv/komponenty/poletnye-kontrollery/?items_per_page=96",
                {},
            ),
            CompEnum.LIDAR: (
                self.url
                + "kupit/spec.-resheniya/geodezicheskaya-semka/?items_per_page=96",
                {},
            ),
            CompEnum.MICROFLIGHTCONTROLLER: (),
            CompEnum.RANGEFINDER: (),
            CompEnum.SATELLITECOMMMODULE: (),
            CompEnum.LEASHINGPLATFORM: (),
            CompEnum.THERMALCAMERA: (),
            CompEnum.UAVCOPTERTYPE: (
                self.url + "kupit/kvadrokopter/dji/?items_per_page=96",
                {},
            ),
            CompEnum.VIDEOTRANSMITTER: (
                self.url + "kupit/fpv/komponenty/peredacha-video/?items_per_page=96",
                {},
            ),
            CompEnum.PAYLOAD: (),
            CompEnum.CONTROLPANEL: (
                self.url + "kupit/fpv/apparatura/?items_per_page=96",
                {},
            ),
        }

    def run(self, comp: CompEnum) -> dict[str, Comp]:
        """Запускает Поиск

        Args:
            comp: Экземпляр класса CompEnum

        Returns:
            Словарь [url удовлетворяющего товара, экземляр класса Comp после парсинга]
        """
        result = {}
        request = self.request_fabric[comp]
        if request:
            response = requests.get(*request)
            time.sleep(randint(1, 4))

            soup = BeautifulSoup(response.text, "html.parser")

            # Итерация по url карточек, которые прошли проверку на соответсвие
            for card_url in self.detect_cards(response.text, self.key_words[comp]):
                result.update({card_url: self.parse_card(card_url, comp).dict()})
        return result

    def detect_cards(self, html_text: str, key_words: list) -> list[str]:
        """Определение подходящих карточек по ключевым словам в названии

        Args:
            html_text: Текст HTML-страницы
            key_words: Ключевые слова

        Returns:
            Список подходящих url адресов карточек
        """
        url_list = []
        soup = BeautifulSoup(html_text, "html.parser")

        for a in soup.find_all("a", class_="product-title"):
            # Получение ссылок товаров
            url_list.append(a.get("href"))

        return url_list

    def parse_card(self, url: str, comp: CompEnum) -> Comp:
        """Парсинг характеристик карточки

        Args:
            url: URL адрес карточки
            comp: экземпляр перечесления CompEnum. Служит для вызова определенной функции parse

        Returns:
            Объект типа Comp
        """
        response = requests.get(url)
        time.sleep(randint(1, 4))
        soup = BeautifulSoup(response.text, "html.parser")

        # Получение изображения, цены, названия товара
        div = soup.find("div", class_="owl-item")
        # print(div.text)
        img = soup.find("img")
        image = img.get("src")
        print(image)
        p = soup.find("span", class_="ty-price-num")
        price = p.get_text()
        h1 = soup.find("h1", class_="ut2-pb__title")
        name = h1.string

        # Получение разделов "Описание" и "Характеристики"
        text_list = []
        div_description = soup.find("div", id="tabs_content")
        if div_description:
            text_list.append(div_description.get_text(" ", strip=True))

        regex = Regex(text_list)
        print(">>>", regex.raw_text)

        return self.fabric[comp](url, image, price, name, regex)

    def parse_battery(
        self, url: str, image: str, price: str, name: str, regex: Regex
    ) -> CompBattery:
        """Парсинг характеристики "Батарея" с использованием регулярных выражений

        Args:
            url: URL адрес карточки
            image: URL адрес фотографии
            price: Цена
            name: Название
            regex: Экземпляр класса Regex. Который служит для поиска с помощью регулярных выражений

        Returns:
            Объект типа CompCompBattery
        """
        return CompBattery(
            url=url,
            image=image,
            price=price,
            name=name,
            current_discharge=regex.find_by(PtrnEnum.CURRENT_DISCHARGE(0)),
            capasity=regex.find_by(PtrnEnum.CAPASITY(0)),
            shape=regex.find_by(PtrnEnum.SHAPE(0)),
            voltage=regex.find_by(PtrnEnum.VOLTAGE(0)),
        )
