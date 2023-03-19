from random import randint
import time

from bs4 import BeautifulSoup
import requests

from .base import Parse
from models import Comp, CompEnum, CompBattery
from .regex import Regex, PtrnEnum


class AeromotusParser(Parse):
    def __init__(self) -> None:
        """Инициализирует экземпляр класса AeromotusParser

        Args:
            
        Returns:

        """
        super().__init__(url="https://aeromotus.ru/", idx=0)
        self.fabric = {
            # КОМПОНЕНТ -> МЕТОД ПАРСИНГА ХАРАКТЕРИСТИК КОМПОНЕНТА
            CompEnum.BATTERY: self.parse_battery,
        }
        self.key_words = {
            # КОМПОНЕНТ -> КЛЮЧЕВЫЕ СЛОВА В НАЗВАНИИ КАРТОЧЕК
            CompEnum.BATTERY: ["аккумулятор", "батарея"]
        }
        self.request_fabric = {
            # КОМПОНЕНТ -> URL && ПАРАМЕТРЫ ЗАПРОСА
            CompEnum.BATTERY: (
                self.url,
                {
                    "s": "аккумулятор",
                    "post_type": "product",
                },
            ),
            CompEnum.UAVCOPTERTYPE: (self.url + "product-tag/bpla", {}),
        }

    def run(self, comp: CompEnum) -> dict[str, Comp]:
        """Запускает Поиск

        Args:
            comp: Экземпляр класса CompEnum

        Returns:
            Словарь [url удовлетворяющего товара, экземляр класса Comp после парсинга]
        """
        result = {}
        response = requests.get(*self.request_fabric[comp])
        time.sleep(randint(1, 4))

        soup = BeautifulSoup(response.text, "html.parser")

        # Получение количества страниц по запросу
        nav = soup.find("nav", class_="electro-advanced-pagination")
        pages = int(nav.text.split()[-1][:-1]) if nav.text else 0

        # Итерация по страницам
        for page in range(1, pages + 1):
            response = requests.get(
                self.request_fabric[comp][0] + f"page/{page}/",
                self.request_fabric[comp][1],
            )
            time.sleep(randint(1, 4))

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

        for li in soup.find_all("li", class_="product"):
            # Получение заголовков карточек
            h2 = li.find("h2", class_="woocommerce-loop-product__title")
            # Итерация по ключевым словам
            for name_key_word in key_words:
                for word in h2.string.lower().split():
                    # Точное соответсвие слова в названии
                    if name_key_word == word:
                        a = li.find("a", class_="woocommerce-LoopProduct-link")
                        url_list.append(a.get("href"))
                        break
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
        img = soup.find("img", class_="wp-post-image")
        image = img.get("src")
        p = soup.find("p", class_="price")
        price = p.get_text().split('\\')[0]
        h1 = soup.find("h1", class_="product_title")
        name = h1.string

        # Получение разделов "Описание" и "Характеристики"
        text_list = []
        div_description = soup.find("div", id="tab-description")
        if div_description:
            text_list.append(div_description.get_text(" ", strip=True))
        div_specification = soup.find("div", id="tab-specification")
        if div_specification:
            text_list.append(div_specification.get_text(" ", strip=True))

        regex = Regex(text_list)

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
            current_discharge=regex.find_by(PtrnEnum.CURRENT_DISCHARGE),
            capasity=regex.find_by(PtrnEnum.CAPASITY),
            shape=regex.find_by(PtrnEnum.SHAPE),
            voltage=regex.find_by(PtrnEnum.VOLTAGE),
        )
