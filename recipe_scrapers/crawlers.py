import time
from random import randint
import urllib2

import requests
import requests_cache
from bs4 import BeautifulSoup
from requests import HTTPError
from requests.exceptions import InvalidSchema
from requests.compat import urlencode

from .recipes import get_recipe, NoRecipeException, InsufficientDataException
from . import log


urljoin = urllib2.urlparse.urljoin


class EmptyPageError(Exception):
    pass


class Request(object):

    base_url = None

    def __init__(self):
        requests_cache.install_cache()

    def get(self, url):
        if not url.startswith('http://'):
            url = urljoin(self.root_url, url)
        if requests_cache.get_cache().has_url(url):
            pass
        else:
            time.sleep(randint(3, 6))
        r = requests.get(url)
        log.info('Status code:{}'.format(r.status_code))
        if r.status_code == 404:
            raise HTTPError('404')
        return r

    def get_html(self, url):
        """
        Return the html for a web url.
        Raises HTTPError('404') if page is not found.
        """
        log.info('Fetching page: {}'.format(url))
        return self.get(url).text

    def get_file(self, url):
        # TODO: Make sure is absolute url
        log.info('Getting file:{}'.format(url))
        return self.get(url).content

    def get_soup(self, url, **kwargs):
        html = self.get_html(url, **kwargs)
        return BeautifulSoup(html, 'lxml')


def absolute_urls(func):
    def absolutify(*args, **kwargs):
        self = args[0]
        for url in func(*args, **kwargs):
            if url.startswith('http://'):
                yield url
            else:
                yield urljoin(self.root_url,
                              url.strip('/'))
    return absolutify


class BaseCrawler(Request):

    # Where recipes or cats are listed
    recipe_index_url = ''
    # root domain usually
    root_url = ''

    def __init__(self, exporter):
        Request.__init__(self)
        self.exporter = exporter
        self.init()

    def init(self):
        self.get_links_args = ()
        self.get_links_kwargs = {}
        self.get_cats_args = ()
        self.get_cats_kwargs = {}

    def page_url(self, page_no):
        return self.recipe_index_url + '/page/{}'.format(page_no)

    @absolute_urls
    def get_categories(self):
        for l in self.get_links(
                self.recipe_index_url,
                *self.get_cats_args,
                **self.get_cats_kwargs):
            yield l

    @absolute_urls
    def get_links(self, url, *args, **kwargs):
        """
        *args and **kwargs will be passed to beautifulsoup
        to find links in page.
        """
        log.info('getting links at:{}'.format(url))
        soup = self.get_soup(url)
        for div in soup.find_all(*args, **kwargs):
            link = div.find('a').get('href')
            log.info('link:{}'.format(link))
            yield link

    def export(self, recipe):
        self.exporter.add(recipe)

    def exists(self, url):
        return self.exporter.exists(url)

    def _base_crawl(self, url):
        log.info('Get links kwargs:{}'.format(
            self.get_links_kwargs))
        links = self.get_links(
            url,
            *self.get_links_args,
            **self.get_links_kwargs)
        for link in links:
            if self.exists(link):
                continue
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

    def _pagination_crawl(self):
        page = 1
        recipes_in_page = 0
        while True:
            url = self.page_url(page)
            try:
                for r in self._base_crawl(url):
                    recipes_in_page += 1
                    yield r
            except HTTPError:
                log.warning(
                    'Got 404, ending pagination crawl. {}'.format(url))
                break
            if recipes_in_page:
                page += 1
                recipes_in_page = 0
            else:
                log.warning(
                    'No links found, ending pagination crawl. {}'.format(url))
                break

    def _flat_crawl(self):
        return self._base_crawl(self.recipe_index_url)

    def _category_crawl(self, paginate=True):
        categories = self.get_categories()
        crawlmethod = self._pagination_crawl if paginate else self._flat_crawl
        for cat in categories:
            self.recipe_index_url = cat.strip('/')
            for r in crawlmethod():

                yield r


class MinimalistBakerCrawler(BaseCrawler):

    recipe_index_url = 'http://minimalistbaker.com/recipes'
    root_url = 'http://minimalistbaker.com'



    # def __init__(self, *args, **kwargs):
    #     BaseCrawler.__init__(self, *args, **kwargs)


    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class_': 'entry-content'}
        self.crawl = self._pagination_crawl


class CookieAndKateCrawler(BaseCrawler):

    root_url = 'http://cookieandkate.com'
    recipe_index_url = 'http://cookieandkate.com/recipes'

    # def __init__(self, *args, **kwargs):
    #     BaseCrawler.__init__(self, *args, **kwargs)


    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class': 'lcp_catlist_item'}
        self.crawl = self._flat_crawl


class NaturallyEllaCrawler(BaseCrawler):

    root_url = 'http://naturallyella.com'
    recipe_index_url = 'http://naturallyella.com/recipes/?'

    # def __init__(self, *args, **kwargs):
    #     BaseCrawler.__init__(self, *args, **kwargs)
    #     self.crawl = self._pagination_crawl

    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class_': 'fm_recipe'}
        self.crawl = self._pagination_crawl

    def page_url(self, page_no):
        return self.recipe_index_url+urlencode((('sf_paged', page_no),))


class LexisCleanKitchenCrawler(BaseCrawler):
    # TODO: Use this as a base for category crawler

    recipe_index_url = 'http://lexiscleankitchen.com/recipes'
    root_url = 'http://lexiscleankitchen.com'

    def init(self):
        self.get_links_args = ()
        self.get_links_kwargs = {'class_': 'post_title'}
        self.get_cats_args = ('div', )
        self.get_cats_kwargs = {'class_': 'recipe_more'}

    # def get_categories(self):
    #     return ['http://lexiscleankitchen.com/category/smoothies-2/']

    def crawl(self):
        for r in self._category_crawl(paginate=True):
            yield r


class SweetPotatoSoulCrawler(BaseCrawler):
    recipe_index_url = 'http://sweetpotatosoul.com/recipes'
    root_url = 'http://sweetpotatosoul.com/recipes'

    # def __init__(self, *args, **kwargs):
    #     BaseCrawler.__init__(self, *args, **kwargs)

    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class_': 'recipe'}
        self.crawl = self._flat_crawl


class SeasonsAndSupperCrawler(BaseCrawler):

    recipe_index_url = 'http://www.seasonsandsuppers.ca/recipe-index-category'
    recipe_index_url = 'http://www.seasonsandsuppers.ca'

    # def __init__(self, *args, **kwargs):
    #     BaseCrawler.__init__(self, *args, **kwargs)
    #     self.crawl = self._flat_crawl

    def init(self):
        self.crawl = self._flat_crawl

    def get_links(self, url, *args, **kwargs):
        soup = self.get_soup(url)
        for cat in soup.find_all(class_='lcp_catlist'):
            for li in cat.find_all('li'):
                yield li.find('a').get('href')
# class SeasonsAndSupperCrawler(Request):

#     base_url = 'http://www.seasonsandsuppers.ca/recipe-index-category/'

#     def get_links(self, url):
#         links = []
#         soup = self.get_soup(url)

#         for cat in soup.find_all(class_='lcp_catlist'):
#             for li in cat.find_all('li'):
#                 links.append(li.find('a').get('href'))
#         return links

#     def crawl(self):
#         return self._flat_crawl()


class FoodHeavenMadeEasyCrawler(BaseCrawler):

    recipe_index_url = 'http://www.foodheavenmadeeasy.com/recipes'
    root_url = 'http://www.foodheavenmadeeasy.com'

    # def __init__(self, *args, **kwargs):
    #     BaseCrawler.__init__(self, *args, **kwargs)
    #     self.crawl = self._flat_crawl

    def init(self):
        self.get_links_kwargs = {'class_': 'cat-list'}
        self.crawl = self._flat_crawl



# class FoodHeavenMadeEasyCrawler(Request):

#     base_url = 'http://www.foodheavenmadeeasy.com/recipes/'

#     def get_links(self, url):
#         links = []
#         soup = self.get_soup(url)
#         for cat in soup.find_all(class_='cat-list'):
#             links.append(cat.find('a').get('href'))
#         return links

#     def crawl(self):
#         return self._flat_crawl()





# Bad crawlers below

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
