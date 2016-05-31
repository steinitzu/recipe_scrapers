import time

from bs4 import BeautifulSoup
import requests
from requests import HTTPError
import requests_cache
import isodate


class MBaker(object):

    def __init__(self):
        self.base_url = 'http://minimalistbaker.com/recipes/'
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

    def get_soup(self, url):
        html = self.get_html(url)
        return BeautifulSoup(html, 'html.parser')

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

    def scrape_recipe(self, entry_data):
        soup = self.get_soup(entry_data['url'])
        d = {}
        d.update(entry_data)

        total_time = soup.find_all(attrs={'itemprop': 'totalTime'})
        if total_time:
            d['total_time'] = isodate.parse_duration(
                total_time[0].get('datetime'))
            print d['total_time']

        cook_time = soup.find_all(attrs={'itemprop': 'cookTime'})
        if cook_time:
            d['cook_time'] = isodate.parse_duration(
                cook_time[0].get('datetime'))

        prep_time = soup.find_all(attrs={'itemprop': 'prepTime'})
        if prep_time:
            d['prep_time'] = isodate.parse_duration(
                prep_time[0].get('datetime'))

        d['recipe_yield'] = soup.find_all(
            attrs={'itemprop': 'recipeYield'})[0].text

        d['recipe_category'] = soup.find_all(
            attrs={'itemprop': 'recipeCategory'})[0].text

        ingredients = [i.text for i in
                       soup.find_all(attrs={'itemprop': 'ingredients'})]
        d['ingredients'] = ingredients

        return d


def test():
    m = MBaker()
    return m.scrape_recipe('http://minimalistbaker.com/vegan-sloppy-joes/')

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
