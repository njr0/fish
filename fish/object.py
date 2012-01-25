class O:
    """
        This class is used to represent objects locally.
        Missing tags are normally set to O.
        The tags are stored in self.tags and there is usually
        either self.about or self.id set.
    """
    def __init__(self, tags=None, about=None, id=None):
        self.about = about
        self.id = id
        self.tags = tags if tags else {}
        self.types = {}
        for t in self.tags:
            self.types[t] = type(self.tags[t])

    def __str__(self):
        keys = self.tags.keys()
        keys.sort()
        return u'\n'.join([u'  %s=%s' % (key, toStr(self.tags[key]
                           if not self.tags[key] is O
                                else u'(not present)'))
                                for key in keys])

    def __unicode__(self):
        keys = self.tags.keys()
        keys.sort()
        return u'\n'.join([formatted_tag_value(key, self.tags[key])
                           for key in keys
                           if not key.startswith('_')])

    def typedval(self, t):
        return (self.tags[t], self.types[t])

    def u(self, key):
        return self.tags[key]

    def toJSON(self):
        return {'item': 'object', 'tags': self.tags}

    def get(self, tag, retNone=True):
        try:
            return self.tags[tag]
        except KeyError:
            if retNone:
                return None
            else:
                raise


