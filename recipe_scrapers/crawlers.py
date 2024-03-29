import time
from random import randint
import urllib2
import re

from isodate import ISO8601Error
import requests
import requests_cache
from bs4 import BeautifulSoup
from requests import HTTPError
from requests.exceptions import InvalidSchema
from requests.compat import urlencode

from .recipes import NoRecipeException, InsufficientDataException, Recipe
from . import souputil

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
        soup = BeautifulSoup(html, 'lxml')
        soup.url = url
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
        self.get_links_args = ()
        self.get_links_kwargs = {}
        self.get_cats_args = ()
        self.get_cats_kwargs = {}
        self.init()

    def init(self):
        """
        Override in subclass, called at end of __init__.
        Use to instantiate instance variables, etc.
        """
        pass

    def page_url(self, page_no):
        return self.recipe_index_url + '/page/{}'.format(page_no)

    def has_recipe(self, soup):
        # TODO: Depricated, use souputil.get_recipe_soup
        r = soup.find(itemtype='http://schema.org/Recipe')
        return True if r else False

    def recipe_soup(self, soup):
        # TODO: Depricated, use souputil.get_recipe_soup
        return soup.find(itemtype='http://schema.org/Recipe')

    def get_recipe(self, soup):
        recipe = Recipe()
        recipe.url = url = soup.url
        # TODO: use souputil.get_recipe_soup
        rsoup = soup.find(itemtype='http://schema.org/Recipe')

        recipe.name = rsoup.find(itemprop='name').text

        recipe.author = rsoup.find(itemprop='author').text

        recipe.image = rsoup.find(itemprop='image')['src']

        recipe.ingredients = [i.text for i in rsoup.find_all(
            itemprprop='ingredients')]

        # Nullable attributes
        try:
            recipe.recipe_yield = rsoup.find(itemprop='recipeYield').text
        except AttributeError:
            log.warning('Recipe at {} is missing recipeYield field'.format(
                recipe.url))

        try:
            recipe.recipe_category = rsoup.find(itemprop='recipeCategory').text
        except AttributeError:
            log.warning(
                'No category found for recipe:{}'.format(url))

        try:
            recipe.recipe_cuisine = rsoup.find(itemprop='recipeCuisine').text
        except AttributeError:
            log.warning(
                'No cuisine property found for recipe:{}'.format(url))

        def set_time(itemprop, attribute, recipe, rsoup):
            t = rsoup.find(itemprop=itemprop)
            if not t:
                log.warning('No {} property on recipe {}'.format(
                    itemprop, recipe.url))
                return
            thetime = t['datetime']
            setattr(recipe, attribute, thetime)

        try:
            set_time('cookTime', 'cook_time', recipe, rsoup)
        except ISO8601Error as e:
            log.error('Recipe {}: {}'.format(url, e.message))
        try:
            set_time('prepTime', 'prep_time', recipe, rsoup)
        except ISO8601Error as e:
            log.error('Recipe {}: {}'.format(url, e.message))
        try:
            set_time('totalTime', 'total_time', recipe, rsoup)
        except ISO8601Error as e:
            log.error('Recipe {}: {}'.format(url, e.message))

        return recipe


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

    def get_soup(self, url, **kwargs):
        html = self.get_html(url, **kwargs)
        soup = BeautifulSoup(html, 'lxml')
        soup.url = url
        recipe = soup.find(itemtype='http://schema.org/Recipe')
        if recipe:
            return self.fix_soup(soup)
        else:
            return soup

    def fix_soup(self, soup):
        """
        Modify the soup if needed before passing it
        on to get recipe.
        """
        return soup

    def _base_crawl(self, url):
        log.info('Get links kwargs:{}'.format(
            self.get_links_kwargs))
        links = self.get_links(
            url,
            *self.get_links_args,
            **self.get_links_kwargs)
        for link in links:
            # We yield something for every link.
            # This is so that pagination crawlers don't stop
            # prematurely in case we run into a single page
            # filled with only duplicate or non-recipe links.
            # In case of duplicate or non-recipe, return None
            # instead of a Recipe object.
            if self.exists(link):
                log.info('Ignoring existing recipe:"{}"'.format(link))
                recipe = None
                #continue
            soup = self.get_soup(link)
            if self.has_recipe(soup):
                recipe = self.get_recipe(soup)
                try:
                    recipe.image_file = self.get_file(recipe.image)
                except (HTTPError, InvalidSchema) as e:
                    log.error(e.message)
                    recipe.image_file = None
            else:
                log.error('No recipe at:{}'.format(link))
                recipe = None

            # try:

            #     recipe = self.get_recipe(soup)
            #     #recipe = get_recipe(self.get_soup(link), link)
            # except (NoRecipeException, InsufficientDataException) as e:
            #     log.error(e.message)
            #     recipe = None
            #     #continue
            # else:
            #     try:
            #         recipe.image_file = self.get_file(recipe.image)
            #     except (HTTPError, InvalidSchema) as e:
            #         log.error(e.message)
            #         recipe.image_file = None
            yield recipe

    def _pagination_crawl(self):
        page = 1
        links_in_page = 0
        while True:
            url = self.page_url(page)
            try:
                for r in self._base_crawl(url):
                    links_in_page += 1
                    if not r:
                        # Recipe could be None
                        # if _base_crawl found existing recipe
                        # or a non-recipe link
                        continue
                    yield r
            except HTTPError:
                log.warning(
                    'Got 404, ending pagination crawl. {}'.format(url))
                break
            if links_in_page:
                page += 1
                links_in_page = 0
            else:
                log.warning(
                    'No links found, ending pagination crawl. {}'.format(url))
                break

    def _flat_crawl(self):
        for r in self._base_crawl(self.recipe_index_url):
            if r:
                # Check in case we get a None from _base_crawl
                yield r

    def _category_crawl(self, paginate=True):
        categories = self.get_categories()
        crawlmethod = self._pagination_crawl if paginate else self._flat_crawl
        for cat in categories:
            self.recipe_index_url = cat.strip('/')
            for r in crawlmethod():
                yield r


class MinimalistBakerCrawler(BaseCrawler):

    # Standard schema recipes
    # cookTime/prepTime/totalTime datetime attributes
    # itemprop="image"
    # itemprop="name"
    # itemprop="author"
    # itemprop="ingredients"

    recipe_index_url = 'http://minimalistbaker.com/recipes'
    root_url = 'http://minimalistbaker.com'

    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class_': 'entry-content'}
        self.crawl = self._pagination_crawl


class CookieAndKateCrawler(BaseCrawler):

    root_url = 'http://cookieandkate.com'
    recipe_index_url = 'http://cookieandkate.com/recipes'

    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class': 'lcp_catlist_item'}
        self.crawl = self._flat_crawl

    def fix_soup(self, soup):
        # TODO: set img src to img href for itemprop='image'
        rsoup = self.recipe_soup(soup)
        if not rsoup:
            return soup
        img = rsoup.find(itemprop='image')
        img['src'] = img['href']
        return souputil.insert_author(soup, 'Cookie and Kate')


class NaturallyEllaCrawler(BaseCrawler):

    root_url = 'http://naturallyella.com'
    recipe_index_url = 'http://naturallyella.com/recipes/?'

    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class_': 'fm_recipe'}
        self.crawl = self._pagination_crawl

    def page_url(self, page_no):
        return self.recipe_index_url+urlencode((('sf_paged', page_no),))


class LexisCleanKitchenCrawler(BaseCrawler):

    recipe_index_url = 'http://lexiscleankitchen.com/recipes'
    root_url = 'http://lexiscleankitchen.com'

    def init(self):
        self.get_links_args = ()
        self.get_links_kwargs = {'class_': 'post_title'}
        self.get_cats_args = ('div', )
        self.get_cats_kwargs = {'class_': 'recipe_more'}

    def crawl(self):
        for r in self._category_crawl(paginate=True):
            yield r


class SweetPotatoSoulCrawler(BaseCrawler):
    recipe_index_url = 'http://sweetpotatosoul.com/recipes'
    root_url = 'http://sweetpotatosoul.com/recipes'

    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class_': 'recipe'}
        self.crawl = self._flat_crawl


class SeasonsAndSupperCrawler(BaseCrawler):

    recipe_index_url = 'http://www.seasonsandsuppers.ca/recipe-index-category'
    root_url = 'http://www.seasonsandsuppers.ca'

    def init(self):
        self.crawl = self._flat_crawl

    @absolute_urls
    def get_links(self, url, *args, **kwargs):
        soup = self.get_soup(url)
        for cat in soup.find_all(class_='lcp_catlist'):
            for li in cat.find_all('li'):
                yield li.find('a').get('href')


class FoodHeavenMadeEasyCrawler(BaseCrawler):

    recipe_index_url = 'http://www.foodheavenmadeeasy.com/recipes'
    root_url = 'http://www.foodheavenmadeeasy.com'

    def init(self):
        self.get_links_kwargs = {'class_': 'cat-list'}
        self.crawl = self._flat_crawl

    def fix_soup(self, soup):
        recipe = soup.find(itemtype='http://schema.org/Recipe')
        # This site doesn't use itemprop="image" for the
        # recipe image.
        # Taking the image from the wp-image-#### tag
        # and adding it as itemprop="image" under recipe schema
        img = soup.find(class_=re.compile(r'wp-image-\w+'))
        img['itemprop'] = 'image'
        recipe.append(img)
        return soup


class SkinnyTasteCrawler(BaseCrawler):
    # Only newest recipes are schema.org compliant

    root_url = 'http://www.skinnytaste.com'
    recipe_index_url = 'http://www.skinnytaste.com/recipes'

    def init(self):
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class_': 'archive-post'}
        self.crawl = self._pagination_crawl

    def fix_soup(self, soup):
        if not self.has_recipe(soup):
            return soup
        rsoup = soup.find(itemtype='http://schema.org/Recipe')
        if rsoup.find(itemprop='author'):
            return soup
        nt = soup.new_tag('div', itemprop='author')
        nt.string = 'Skinnytaste'
        rsoup.insert(3, nt)

        for attr in ('totalTime', 'cookTime', 'prepTime'):
            tag = rsoup.find(itemprop=attr)
            if not tag:
                continue
            tag['datetime'] = tag['content']
        return soup


class DamnDeliciousCrawler(BaseCrawler):
    root_url = 'http://damndelicious.net'
    recipe_index_url = 'http://damndelicious.net/recipe-index'

    def init(self):
        self.get_cats_args = ('div', )
        self.get_cats_kwargs = {'class_': 'archive-post'}
        self.get_links_args = ('div', )
        self.get_links_kwargs = {'class_': 'archive-post'}
        self.crawl = self._category_crawl



def get_crawlers():
    d = {}
    for klass in BaseCrawler.__subclasses__():
        d[klass.__name__.split('Crawler')[0]] = klass
    return d


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
