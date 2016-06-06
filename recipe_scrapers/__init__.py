import logging

log = logging.getLogger('scrapers')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)
