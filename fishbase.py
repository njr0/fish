import os
import types

UNIX_CREDENTIALS_FILE = u'.fluidDBcredentials'
UNIX_USER_CREDENTIALS_FILE = u'.fluidDBcredentials.%s'

CRED_FILE_VAR = 'FISH_CREDENTIALS_FILE'
WIN_CRED_FILE = 'c:\\fish\\credentials.txt'

toStr = unicode

def get_credentials_file(username=None):
    if os.name == 'posix':
        homeDir = os.path.expanduser('~')
        file = ((UNIX_USER_CREDENTIALS_FILE % username) if username
                else UNIX_CREDENTIALS_FILE)
        return os.path.join(homeDir, file)

    elif os.name:
        e = os.environ
        return e[CRED_FILE_VAR] if CRED_FILE_VAR in e else WIN_CRED_FILE
    else:
        return None


def get_user_file(file, username):
    if os.name == 'posix':
        return os.path.join(os.path.expanduser(u'~'), file['unix'] % username)
    elif os.name:
        return file[u'windows'] % username
    else:
        return None
    

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


def formatted_tag_value(tag, value, terse=False, prefix=u'  '):
    lhs = u'' if terse else u'%s%s = ' % (prefix, tag)
    if value == None:
        return u'%s%s' % (u'' if terse else prefix, tag)
    elif type(value) == unicode:
        return u'%s"%s"' % (lhs, value)
    elif type(value) == type(''):
        return '%s"%s"' % (lhs.encode('UTF-8'), value)
    elif type(value) in (list, tuple):
        vals = value[:]
        vals.sort()
        return u'%s{%s}' % (lhs,
                             u', '.join(u'"%s"' % unicode(v) for v in vals))
    else:
        return u'%s%s' % (lhs, toStr(value))


