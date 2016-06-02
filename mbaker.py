import time

import isodate
import requests
import requests_cache
from bs4 import BeautifulSoup
from requests import HTTPError
from datetime import timedelta



class NoRecipeException(Exception):
    pass


class Recipe(object):
    url = None
    name = None
    image = None
    author = None
    recipe_yield = None
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
            raise TypeError('Value {} is of unsupported type for a timedelta')

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


class MBaker(object):

    def __init__(self):
        self.base_url = 'http://minimalistbaker.com/recipes/'
        requests_cache.install_cache()

    # Todo: requests stuff should be outside class
    def get_html(self, url):
        """
        Return the html for a web url.
        Raises HTTPError('404') if page is not found.
        """
        # Give 5 seconds between requests
        if requests_cache.get_cache().has_url(url):
            pass
        else:
            time.sleep(5)
        r = requests.get(url)
        if r.status_code == 404:
            raise HTTPError('404')
        return r.text

    def get_soup(self, url):
        html = self.get_html(url)
        return BeautifulSoup(html, 'html.parser')

    def get_recipe(self, url):
        """
        Given a webpage, finds a hrecipe by
        searching for a container with the:
        itemtype='http://schema.org/Recipe
        """
        bigsoup = self.get_soup(url)
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
        recipe.recipe_yield = soup.find_all(
            attrs={'itemprop': 'recipeYield'})[0].text

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

        return recipe


    def get_entry_data(self, page_url):
        """
        Given an url for a page of recipe listings.
        e.g. http://base_url/recipes/page/12
        Yields dicts for recipes: {'url': url, 'img': url, 'title': 'title'}
        """
        soup = self.get_soup(page_url)
        recipe_divs = soup.findAll('div', {'class': 'entry-content'})
        for div in recipe_divs:
            a = div.find_next('a')
            title = a.get('title')
            url = a.get('href')
            img = a.find_next('img').get('src')
            yield {'url': url,
                   'image': img,
                   'title': title}

    def scrape_entry_pages(self, start_page=1):
        """
        Keeps scraping pages until runs into a 404.
        """
        page = start_page
        while True:
            url = self.base_url + 'page/{}'.format(page)
            try:
                for d in self.get_entry_data(url):
                    yield d
            except HTTPError:
                break
            page += 1


class Crawler(object):

    def __init__(self):
        pass




def test():
    m = MBaker()
    mg = m.get_recipe
    return (mg('http://minimalistbaker.com/vegan-sloppy-joes/'),
            mg('http://www.epicurious.com/recipes/food/views/slow-roasted-char-with-fennel-salad'),
            mg('http://pinchofyum.com/green-goddess-quinoa-summer-salad'),
            mg('http://www.bonappetit.com/recipe/crispy-potato-salad-chiles-celery-peanuts'),
        )


def big_test():
    m = MBaker()
    for page in m.scrape_entry_pages():
        print m.scrape_recipe(page)


def test_soup():
    m = MBaker()
    return m.get_soup('http://minimalistbaker.com/vegan-sloppy-joes/')


def cache_all():
    m = MBaker()
    return m.scrape_entry_pages()

if __name__ == '__main__':
    print test()
