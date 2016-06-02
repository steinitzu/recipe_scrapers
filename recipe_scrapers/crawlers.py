import time

import requests
import requests_cache
from bs4 import BeautifulSoup
from requests import HTTPError
from requests.compat import urlencode, urljoin

from .recipes import get_recipe


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
            time.sleep(5)
        r = requests.get(url)
        if r.status_code == 404:
            raise HTTPError('404')
        return r.text

    def get_soup(self, url, **kwargs):
        html = self.get_html(url, **kwargs)
        return BeautifulSoup(html, 'html.parser')

    def _pagination_crawl(self):
        page = 1
        while True:
            url = self.page_url(page)
            try:
                pagelinks = self.get_links(url)
            except HTTPError:
                break
            for link in pagelinks:
                yield get_recipe(self.get_soup(link), link)
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
        for link in self.get_links(self.base_url):
            yield get_recipe(self.get_soup(link), link)


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


def minimalistbakertest():
    m = MinimalistBakerCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'


def cookieandkatetest():
    m = CookieAndKateCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'


def pinchofyumtest():
    m = PinchOfYumCrawler()
    for i in m.crawl():
        print i.__dict__
        print '\n'
