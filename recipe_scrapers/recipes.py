from datetime import timedelta

import isodate

from . import log


class NoRecipeException(Exception):
    pass

class InsufficientDataException(Exception):
    pass


class Recipe(object):
    url = None
    name = None
    image = None
    author = None
    recipe_yield = None
    recipe_category = None
    _cook_time = None
    _prep_time = None
    _total_time = None
    ingredients = None

    def __init__(self):
        self.ingredients = []

    def _time_setter(self, attr, value):
        if isinstance(value, basestring):
            setattr(self, attr, isodate.parse_duration(value))
        elif isinstance(value, timedelta):
            setattr(self, attr, value)
        else:
            raise TypeError(
                'Value {} is of unsupported type for a timedelta'.format(value))

    @property
    def cook_time(self):
        return self._cook_time

    @cook_time.setter
    def cook_time(self, value):
        self._time_setter('_cook_time', value)

    @property
    def prep_time(self):
        return self._prep_time

    @prep_time.setter
    def prep_time(self, value):
        self._time_setter('_prep_time', value)

    @property
    def total_time(self):
        return self._total_time

    @total_time.setter
    def total_time(self, value):
        self._time_setter('_total_time', value)


def get_recipe(soup, url):
    """
    Given a BeautifulSoup object, finds a hrecipe by
    searching for a container with the:
    itemtype='http://schema.org/Recipe
    """
    log.info('Scraping {}'.format(url))
    bigsoup = soup
    recipes = bigsoup.find_all(
        attrs={'itemtype': 'http://schema.org/Recipe'})
    if not recipes:
        raise NoRecipeException(
            'No recipe found at: {}'.format(url))
    recipe = Recipe()
    soup = recipes[0]
    recipe.url = url

    img = soup.find_all(attrs={'itemprop': 'image'})[0]
    for tag in ('src', 'srcset', 'content', 'href'):
        if tag in img.attrs:
            recipe.image = img.get(tag)
            break

    recipe.name = soup.find_all(attrs={'itemprop': 'name'})[0].text
    try:
        recipe.author = soup.find_all(attrs={'itemprop': 'author'})[0].text
    except (AttributeError, IndexError):
        recipe.author = None
    try:
        recipe.recipe_yield = soup.find_all(
            attrs={'itemprop': 'recipeYield'})[0].text
    except IndexError:
        raise InsufficientDataException(
            'Recipe at {} is missing recipeYield field'.format(url))


    # TODO: Find another way to get category
    try:
        recipe.recipe_category = soup.find_all(
            attrs={'itemprop': 'recipeCategory'})[0].text
    except IndexError:
        log.warning(
            'No category found for recipe:{}'.format(url))

    try:
        recipe.recipe_cuisine = soup.find_all(
            attrs={'itemprop': 'recipeCuisine'})[0].text
    except IndexError:
        log.warning(
            'No cuisine property found for recipe:{}'.format(url))

    cook_time = soup.find_all(attrs={'itemprop': 'cookTime'})
    if cook_time:
        recipe.cook_time = cook_time[0].get('datetime')

    prep_time = soup.find_all(attrs={'itemprop': 'prepTime'})
    if prep_time:
        recipe.prep_time = prep_time[0].get('datetime')

    total_time = soup.find_all(attrs={'itemprop': 'totalTime'})
    if total_time:
        recipe.total_time = total_time[0].get('datetime')

    for ingtag in soup.find_all(attrs={'itemprop': 'ingredients'}):
        recipe.ingredients.append(ingtag.text)

    log.info('Result: {}'.format(recipe.__dict__))

    return recipe
