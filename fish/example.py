# example.py
# Example of using the fishlib API.
#
# Copyright (c) Nicholas J. Radcliffe 2009-2012.
# Licence terms in LICENCE.
#
from fish import fishlib

db = fishlib.Fluidinfo()    # assumes credentials are in the standard place
db.get_tag_value_by_about('DADGAD', '/fluiddb/about')
(status, value) = db.get_tag_value_by_about('DADGAD', '/fluiddb/about')
print value
assert db.tag_object_by_about('DADGAD', 'rating', 10) == 0
(status, value) = db.get_tag_value_by_about('DADGAD', 'rating')
print value
