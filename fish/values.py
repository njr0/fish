from fishlib import Fluidinfo, json

def tag_by_about_values(db, items, map=None):
    # takes items as a list, tuple or dictionary of objects
    objs = items.values if type(items) == dict else items
    body = {u'queries' : [ [u'fluiddb/about = "%s"' % o.about,
               dict((u'%s/%s' % (db.credentials.username,
                                k.replace('_', '/')),
                     {u'value': o.__dict__[k]})
                          for k in o.__dict__
                          if (k != u'about' and not k.startswith(u'_')))]
               for o in items]}
#    print json.dumps(body)
    o = db.call('PUT', '/values', json.dumps(body))
    return o
    


class O:
    def __init__(self, about, tags):
        self.about = about
        for k in tags:
            self.__dict__[k] = tags[k]


if __name__ == '__main__':
    db = Fluidinfo(u'book', debug=True)
    objs = [O(u'0', {u'rating': 3}), O(u'1', {u'rating': 3})]

    print tag_by_about_values(db, objs)

