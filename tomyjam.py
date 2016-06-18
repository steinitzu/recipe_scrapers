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
                                      FoodHeavenMadeEasyCrawler)
from recipe_scrapers import log, logging


def main():
    if log.level == logging.DEBUG:
        db.drop_all()
        db.create_all()
    exporter = SQLAlchemyExporter(db, Recipe, Ingredient, upload_image)
    crawlers = [
        # MinimalistBakerCrawler(),
        # CookieAndKateCrawler(),
        # NaturallyEllaCrawler(),
        # SweetPotatoSoulCrawler(),
        # SeasonsAndSupperCrawler(),
        FoodHeavenMadeEasyCrawler(),
        ]
    scrape_and_export(exporter, crawlers)

def get_all_images():
    """
    todo: do
    make new column, image_id in recipe, foreign key to Image
    for every recipe:
        r = request.get(recipe.image, stream=True)
        dbimage = myjam.file_mgmt.upload_image(r.content)
        recipe.image = dbimage
    """






if __name__ == '__main__':
    main()
