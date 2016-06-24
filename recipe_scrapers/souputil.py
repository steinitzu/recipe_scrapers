def get_recipe_soup(soup):
    return soup.find(itemtype='http://schema.org/Recipe')


def insert_author(soup, author_name, force=False):
    """
    Inserts an itemprop='author' tag if it's missing.
    If force=True, overrides previous author tag with
    given author_name.
    """
    rsoup = get_recipe_soup(soup)
    oldtag = rsoup.find(itemprop='author')
    if oldtag:
        if force:
            oldtag.string = author_name
        else:
            pass
        return soup
    nt = soup.new_tag('div', itemprop='author')
    nt.string = author_name
    rsoup.insert(3, nt)
    return soup
