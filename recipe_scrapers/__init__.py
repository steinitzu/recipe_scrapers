import logging

log = logging.getLogger('scrapers')
log.addHandler(logging.StreamHandler())
log.addHandler(logging.FileHandler('/tmp/rscraper.log'))
log.setLevel(logging.DEBUG)
