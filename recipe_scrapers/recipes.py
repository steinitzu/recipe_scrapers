import re

import isodate
from . import log
from datetime import timedelta
from isodate.isoerror import ISO8601Error


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
    recipe_cuisine = None
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
    soup = bigsoup.find(itemtype='http://schema.org/Recipe')
    if not soup:
        raise NoRecipeException(
            'No recipe found at: {}'.format(url))

    recipe = Recipe()
    recipe.url = url

    recipe.name = soup.find(itemprop='name').text

    try:
        img = soup.find_all(attrs={'itemprop': 'image'})[0]
    except IndexError:
        article = bigsoup.find('article', class_='post')
        img = article.find('img', class_=re.compile(r'wp-image-\w+'))

    for tag in ('src', 'srcset', 'content', 'href'):
        if tag in img.attrs:
            recipe.image = img.get(tag)
            break

    attrs = [(soup, {'itemprop': 'author'}),
             (bigsoup, {'property': re.compile('^(.*)author$')}),
             #(bigsoup, {'class': re.compile('^(.*)author$')}),
             (bigsoup, {'property': re.compile('^(.*)site_name$')}),
         ]

    auth = None
    for s, a in attrs:
        auth = s.find(attrs=a)
        if auth:
            author = auth.text
            if not author:
                author = auth.get('content')
                if not author:
                    continue
            recipe.author = author
            log.info('Used {} to find author'.format(a))
            break
    if not recipe.author:
        raise Exception(
            'No author found for recipe: {}'.format(url))

    try:
        recipe.recipe_yield = soup.find_all(
            attrs={'itemprop': 'recipeYield'})[0].text
    except IndexError:
        log.warning('Recipe at {} is missing recipeYield field'.format(url))

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

    time_setter('cookTime', 'cook_time', recipe, soup)
    time_setter('prepTime', 'prep_time', recipe, soup)
    time_setter('totalTime', 'total_time', recipe, soup)

    for ingtag in soup.find_all(attrs={'itemprop': 'ingredients'}):
        recipe.ingredients.append(ingtag.text)

    #log.info('Result: {}'.format(recipe.__dict__))

    return recipe


def time_setter(itemprop, attribute, recipe, soup):
    t = soup.find(attrs={'itemprop': itemprop})
    if not t:
        log.warning('No {} itemprop on recipe {}'.format(
            itemprop, recipe.url))
        return

    # SkinnyTaste has timestamp in 'content' attribute
    thetime = t.get('datetime', t.get('content'))
    if not thetime:
        thetime = t.find(class_='value-title').get('title')
    setattr(recipe, attribute, thetime)
    # try:
    #     setattr(recipe, attribute, t.get('datetime'))
    # except ISO8601Error:
    #     t = t.find_all(attrs={'class': 'value-title'})
    #     setattr(recipe, attribute, t[0].get('title'))
