import sys
import os

thisdir = os.path.dirname(os.path.realpath(__file__))
myjamdir = os.path.realpath(
    os.path.join(thisdir, '..', 'myjam'))
sys.path.insert(0, myjamdir)

import requests

from myjam import db
from myjam.models import Recipe, Ingredient
from myjam.file_mgmt import upload_image
from recipe_scrapers.export import SQLAlchemyExporter, scrape_and_export
from recipe_scrapers.crawlers import (MinimalistBakerCrawler,
                                      CookieAndKateCrawler,
                                      NaturallyEllaCrawler,
                                      SweetPotatoSoulCrawler,
                                      SeasonsAndSupperCrawler,
                                      FoodHeavenMadeEasyCrawler,
                                      LexisCleanKitchenCrawler,

                                      NaturallyEllaCrawler2,
                                      CookieAndKateCrawler2,
                                      LexisCleanKitchenCrawler2,
                                      MinimalistBakerCrawler2
)
from recipe_scrapers import log, logging


def main():
    if log.level == logging.DEBUG:
        db.drop_all()
        db.create_all()
    exporter = SQLAlchemyExporter(db, Recipe, Ingredient, upload_image)
    crawlers = [
        NaturallyEllaCrawler2(),
        CookieAndKateCrawler2(),
        LexisCleanKitchenCrawler2(),
        MinimalistBakerCrawler2()]
    # crawlers = [
    #     MinimalistBakerCrawler(),
    #     CookieAndKateCrawler(),
    #     NaturallyEllaCrawler(),
    #     SweetPotatoSoulCrawler(),
    #     SeasonsAndSupperCrawler(),
    #     FoodHeavenMadeEasyCrawler(),
    #     LexisCleanKitchenCrawler(),
    #     ]
    scrape_and_export(exporter, crawlers)


if __name__ == '__main__':
    main()
