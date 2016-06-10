import time
from random import randint

import requests
import requests_cache
from bs4 import BeautifulSoup
from requests import HTTPError
from requests.exceptions import InvalidSchema
from requests.compat import urlencode, urljoin

from .recipes import get_recipe, NoRecipeException, InsufficientDataException
from . import log

class EmptyPageError(Exception):
    pass


class Request(object):

    base_url = None

    def __init__(self):
        requests_cache.install_cache()

    def get_html(self, url):
        """
        Return the html for a web url.
        Raises HTTPError('404') if page is not found.
        """
        log.info('Fetching page: {}'.format(url))
        # Give 5 seconds between requests
        if requests_cache.get_cache().has_url(url):
            pass
        else:
            time.sleep(randint(5,20))
        r = requests.get(url)
        if r.status_code == 404:
            raise HTTPError('404')
        return r.text

    def get_file(self, url):
        log.info('Getting file:{}'.format(url))
        if requests_cache.get_cache().has_url(url):
            pass
        else:
            time.sleep(randint(3, 5))
        r = requests.get(url.strip(), stream=True)
        if r.status_code == 404:
            raise HTTPError('404')
        return r.content

    def get_soup(self, url, **kwargs):
        html = self.get_html(url, **kwargs)
        return BeautifulSoup(html, 'lxml')

    def _base_crawl(self, url):
        links = self.get_links(url)
        if not links:
            log.warning(
                'Page is empty, ending crawl. {}'.format(url))
            # Hack to stop while loop in pagination crawl
            raise HTTPError('Empty page')
        for link in links:
            try:
                recipe = get_recipe(self.get_soup(link), link)
            except (NoRecipeException, InsufficientDataException) as e:
                log.error(e.message)
                continue
            try:
                recipe.image_file = self.get_file(recipe.image)
            except (HTTPError, InvalidSchema) as e:
                log.error(e.message)
                recipe.image_file = None
            yield recipe

    def _flat_crawl(self):
        return self._base_crawl(self.base_url)
        # for link in self.get_links(self.base_url):
        #     try:
        #         yield get_recipe(self.get_soup(link), link)
        #     except (NoRecipeException, InsufficientDataException) as e:
        #         log.error(e.message)
        #         continue

    def _pagination_crawl(self):
        page = 1
        while True:
            url = self.page_url(page)
            try:
                for r in self._base_crawl(url):
                    yield r
            except HTTPError:
                break
            page += 1



            # try:
            #     pagelinks = self.get_links(url)
            # except HTTPError:
            #     break
            # if not pagelinks:
            #     log.warning(
            #         'Page is empty, ending crawl. {}'.format(url))
            #     break
            # for link in pagelinks:
            #     try:
            #         yield get_recipe(self.get_soup(link), link)
            #     except (NoRecipeException, InsufficientDataException) as e:
            #         log.error(e.message)
            #         continue
            # page += 1


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


class SeasonsAndSupperCrawler(Request):

    base_url = 'http://www.seasonsandsuppers.ca/recipe-index-category/'

    def get_links(self, url):
        links = []
        soup = self.get_soup(url)

        for cat in soup.find_all(class_='lcp_catlist'):
            for li in cat.find_all('li'):
                links.append(li.find('a').get('href'))
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
