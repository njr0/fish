import cPickle as pickle
from fishbase import get_user_file

ALIAS_TAG = u'.fish/alias'
CACHE_FILE = {u'unix': u'.fishcache.%s',
              u'windows': u'c:\\fish\\credentials-%s.txt'}


class CacheError(Exception):
    pass


class Cache:
    def __init__(self, username):
        self.username = username
        self.objects = {}
        if username:
            self.cacheFile = get_user_file(CACHE_FILE, username)
            self.read()

    def read(self):
        try:
            f = open(self.cacheFile, 'rb')
            try:
                self.objects = pickle.load(f)
                f.close()
            except:
                raise CacheError('Cache %s appears corrupt' % self.cacheFile)
        except IOError:  # No cache
            pass


    def __unicode__(self):
        out = [u'Cache:']
        for about in self.objects:
            out.append(u'  fluiddb/about="%s":\n    %s' % (about,
                                                unicode(self.objects[about])))
        return u'\n\n'.join(out)

    def write(self):
        f = open(self.cacheFile, 'wb')
        pickle.dump(self.objects, f)
        f.close()

    def add(self, o, write=True):
        objects = o if type(o) in (list, tuple) else [o]
        for o in objects:
            self.objects[o.about] = o
        if write:
            self.write()

    def sync(self, db):
        alias_tag = u'%s/%s' % (self.username, ALIAS_TAG)
        objects = db.get_values_by_query(u'has %s' % alias_tag,
                                         [u'fluiddb/about', alias_tag])
        if objects:
            self.objects = {}
            for o in objects:
                self.objects[o.about] = o
            self.write()
        else:
            db.warning('Nothing to sync from Fluidinfo')

    def aliases(self, name=None):
        alias_tag = u'%s/%s' % (self.username, ALIAS_TAG)
        if name:
            return [self.objects[about] for about in self.objects
                    if alias_tag in self.objects[about].tags and about == name]
        else:
            return [self.objects[about] for about in self.objects
                    if alias_tag in self.objects[about].tags]

    def get_alias(self, name):
        try:
            alias_tag = u'%s/%s' % (self.username, ALIAS_TAG)
            return self.objects[name].tags[alias_tag]
        except KeyError:
            return None

#    def unalias(self, name):
#        alias_tag = u'%s/%s' % (self.username, ALIAS_TAG)
#        if not name in self.objects:
#            return 1
#        del self.objects[name].tags[alias_tag]
        


