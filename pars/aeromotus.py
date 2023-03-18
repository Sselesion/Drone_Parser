from random import randint
import time

from bs4 import BeautifulSoup
import requests

from .base import Parse
from models import Comp, CompEnum, CompBattery
from .regex import Regex, PtrnEnum


class AeromotusParser(Parse):
    def __init__(self) -> None:
        super().__init__(url="https://aeromotus.ru/", idx=0)
        self.fabric = {
            CompEnum.BATTERY: self.parse_battery,
        }
        self.key_words = {
            CompEnum.BATTERY: "аккумулятор",
        }
        self.name_key_words = {CompEnum.BATTERY: ["аккумулятор", "батарея"]}

    def run(self, comp: CompEnum):
        result = {}
        response = requests.get(
            self.url,
            params={
                "s": self.key_words[comp],
                "post_type": "product",
            },
        )
        time.sleep(randint(1, 4))

        soup = BeautifulSoup(response.text, "html.parser")
        nav = soup.find("nav", class_="electro-advanced-pagination")
        pages = int(nav.text.split()[-1][:-1]) if nav.text else 0
        for page in range(1, pages + 1):
            response = requests.get(
                self.url + f"page/{page}/",
                params={
                    "s": self.key_words[comp],
                    "post_type": "product",
                },
            )
            time.sleep(randint(1, 4))

            for card_url in self.detect_cards(response.text, self.name_key_words[comp]):
                result.update({card_url: self.parse_card(card_url, comp)})
        return result

    def detect_cards(self, html_text: str, name_key_words: list) -> list[str]:
        url_list = []
        soup = BeautifulSoup(html_text, "html.parser")
        for li in soup.find_all("li", class_="product"):
            h2 = li.find("h2", class_="woocommerce-loop-product__title")
            for name_key_word in name_key_words:
                for word in h2.string.lower().split():
                    if name_key_word == word:
                        a = li.find("a", class_="woocommerce-LoopProduct-link")
                        url_list.append(a.get("href"))
                        break
        return url_list

    def parse_card(self, url: str, comp: CompEnum) -> Comp:
        response = requests.get(url)
        time.sleep(randint(1, 4))
        soup = BeautifulSoup(response.text, "html.parser")

        img = soup.find("img", class_="wp-post-image")
        image = img.get("src")
        p = soup.find("p", class_="price")
        price = p.get_text()
        h1 = soup.find("h1", class_="product_title")
        name = h1.string

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