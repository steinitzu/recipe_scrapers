from . import log

from sqlalchemy import exists

class SQLAlchemyExporter(object):
    """
    A class for exporting recipes to an sql alchemy database.
    Pass in the db instance, recipe model and ingredients model
    and use add_recipe to add Recipe objects to the database.
    """

    def __init__(self, db, recipe_model, ingredients_model, upload_image):
        self.db = db
        self.recipe_model = recipe_model
        self.ingredients_model = ingredients_model
        self.upload_image = upload_image

    def row_exists(self, model_class, field, value):
        return self.db.session.query(exists().where(
            getattr(model_class, field) == value)).scalar()

    def add_recipe(self, recipe):
        print log.info('Adding recipe {} to db'.format(recipe.url))
        try:
            image = self.upload_image(recipe.image_file)
        except IOError:
            log.error(
                "Couldn't load image for recipe:{}".format(recipe.url))
            image = None
        if self.row_exists(self.recipe_model, 'url', recipe.url):
            return
        rmodel = self.recipe_model()
        for attrib in ('url',
                       'name',
                       'author',
                       'recipe_yield',
                       'recipe_category',
                       'recipe_cuisine',
                       'cook_time',
                       'prep_time',
                       'total_time'):
            setattr(rmodel, attrib,
                    getattr(recipe, attrib))
        rmodel.ingredients = [
            self.ingredients_model(name=ingr) for
            ingr in recipe.ingredients]
        rmodel.image = image
        self.db.session.merge(rmodel)
        self.db.session.commit()

def scrape_and_export(exporter, crawlers=[]):
    for crawler in crawlers:
        for recipe in crawler.crawl():
            exporter.add_recipe(recipe)
