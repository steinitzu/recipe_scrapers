import sys
import os

thisdir = os.path.dirname(os.path.realpath(__file__))
myjamdir = os.path.realpath(
    os.path.join(thisdir, '..', 'myjam'))
sys.path.insert(0, myjamdir)

from myjam import db
from myjam.models import Recipe, Ingredient
from recipe_scrapers.export import SQLAlchemyExporter, scrape_and_export
from recipe_scrapers.crawlers import (MinimalistBakerCrawler,
                                      CookieAndKateCrawler,
                                      NaturallyEllaCrawler,
                                      SweetPotatoSoulCrawler)
from recipe_scrapers import log, logging


def main():
    if log.level == logging.DEBUG:
        db.drop_all()
        db.create_all()
    exporter = SQLAlchemyExporter(db, Recipe, Ingredient)
    scrape_and_export(exporter, [MinimalistBakerCrawler(),
                                 CookieAndKateCrawler(),
                                 NaturallyEllaCrawler(),
                                 SweetPotatoSoulCrawler()])

if __name__ == '__main__':
    main()
