#!/usr/bin/python3
import logging
import os

log = logging.getLogger('propertree')
format = ("%(asctime)s.%(msecs)03d %(process)d %(levelname)s %(name)s [-] "
          "%(message)s")

dbg = os.environ.get('PROPERTREE_DEBUG')
if dbg and dbg.lower() == 'true':
    log.setLevel(logging.DEBUG)
else:
    # Force min. info level since the debug logs are very verbose and not
    # likely useful unless specifically requested.
    log.setLevel(logging.INFO)

if log.level and not log.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(format))
    log.addHandler(handler)
