import time
from random import randint

import requests
import requests_cache
from bs4 import BeautifulSoup
from requests import HTTPError
from requests.compat import urlencode, urljoin

from .recipes import get_recipe, NoRecipeException, InsufficientDataException


class Request(object):

    base_url = None

    def __init__(self):
        requests_cache.install_cache()

    def get_html(self, url):
        """
        Return the html for a web url.
        Raises HTTPError('404') if page is not found.
        """
        # Give 5 seconds between requests
        if requests_cache.get_cache().has_url(url):
            pass
        else:
            time.sleep(randint(5,20))
        r = requests.get(url)
        if r.status_code == 404:
            raise HTTPError('404')
        return r.text

    def get_soup(self, url, **kwargs):
        html = self.get_html(url, **kwargs)
        return BeautifulSoup(html, 'html.parser')

    def _flat_crawl(self):
        for link in self.get_links(self.base_url):
            try:
                yield get_recipe(self.get_soup(link), link)
            except (NoRecipeException, InsufficientDataException):
                continue

    def _pagination_crawl(self):
        page = 1
        while True:
            url = self.page_url(page)
            try:
                pagelinks = self.get_links(url)
            except HTTPError:
                break
            for link in pagelinks:
                try:
                    yield get_recipe(self.get_soup(link), link)
                except (NoRecipeException, InsufficientDataException):
                    continue
            page += 1


class MinimalistBakerCrawler(Request):

    base_url = 'http://minimalistbaker.com/recipes'

    def page_url(self, page_no):
        return self.base_url + '/page/{}'.format(page_no)

    def get_links(self, url):
        """
        Return all recipe links on page.
        """
        links = []
        soup = self.get_soup(url)

        recipe_divs = soup.findAll('div', {'class': 'entry-content'})
        for div in recipe_divs:
            url = div.find_all('a')[0].get('href')
            links.append(url)
        return links

    def crawl(self):
        return self._pagination_crawl()


class CookieAndKateCrawler(Request):

    base_url = 'http://cookieandkate.com/recipes/'

    def get_links(self, url):
        links = []
        soup = self.get_soup(url)
        recipe_divs = soup.findAll('div', {'class': 'lcp_catlist_item'})
        for div in recipe_divs:
            url = div.find_all('a')[0].get('href')
            links.append(url)
        return links

    def crawl(self):
        return self._flat_crawl()


class NaturallyEllaCrawler(Request):

    base_url = 'http://naturallyella.com/recipes/?'

    def page_url(self, page_no):
        return self.base_url+urlencode((('sf_paged', page_no),))

    def get_links(self, url):
        links = []
        soup = self.get_soup(url)
        recipe_divs = soup.find_all('div', {'class': 'fm_recipe'})
        for div in recipe_divs:
            url = div.find_all('a')[0].get('href')
            links.append(url)
        return links

    def crawl(self):
        return self._pagination_crawl()


class SweetPotatoSoulCrawler(Request):

    base_url = 'http://sweetpotatosoul.com/recipes'

    def get_links(self, url):
        links = []
        soup = self.get_soup(url)
        recipe_divs = soup.find_all('div', {'class': 'recipe'})
        for div in recipe_divs:
            # TODO: category could be div.get('class')[1]
            url = div.find_all('a')[0].get('href')
            links.append(url)
        return links

    def crawl(self):
        return self._flat_crawl()


class PinchOfYumCrawler(Request):
    base_url = 'http://pinchofyum.com/recipes?'

    def page_url(self, page_no):
        return self.base_url+urlencode((('fwp_paged', page_no),))

    def crawl(self):
        return self._pagination_crawl()

    def get_links(self, url):
        links = []
        soup = self.get_soup(url)
        recipe_divs = soup.findAll('article')
        for div in recipe_divs:
            url = div.find_all('a')[0].get('href')
            links.append(url)
        return links


class BonappetitCrawler(Request):

    base_url = 'http://bonappetit.com/recipes'
    cat_base_url = 'http://bonappetit.com/recipes'
    categories = ('quick-recipes', 'family-meals',
                  'desserts', 'chicken', 'vegetarian',
                  'holidays-recipes')

    def get_links(self, url):
        links = []
        soup = self.get_soup(url)
        recipe_divs = soup.find_all('div', {'class': 'article-thumb-container'})
        for div in recipe_divs:
            url = div.find_all('a')[0].get('href')
            links.append(url)
        return links

    def page_url(self, page_no):
        return self.cat_base_url + '/page/{}'.format(page_no)

    def crawl(self):
        for category in self.categories:
            print 'category:', category
            self.cat_base_url = self.base_url + '/{}'.format(category)
            return self._pagination_crawl()






def minimalistbakertest():
    # Perfect
    m = MinimalistBakerCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'


def cookieandkatetest():
    # Perfect
    m = CookieAndKateCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'


def naturallyellatest():
    # Missing categories
    m = NaturallyEllaCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'


def sweetpotatosoultest():
    # Missing categories
    m = SweetPotatoSoulCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'







def pinchofyumtest():
    # Ehhh
    m = PinchOfYumCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'


def bonappetittest():
    # Messed up
    m = BonappetitCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'
