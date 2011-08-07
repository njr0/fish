# -*- coding: utf-8 -*-
#
# fdblib.py
#
# Copyright (c) Nicholas J. Radcliffe 2009-2011 and other authors specified
#               in the AUTHOR
# Licence terms in LICENCE.

__version__ = u'4.06'
VERSION = __version__

import codecs
import cPickle as pickle
import os
import re
import sys
import types
import urllib
from functools import wraps
from httplib2 import Http
import cline

if sys.version_info < (2, 6):
    try:
        import simplejson as json
    except ImportError:
        from django.utils import simplejson as json
else:
    import json


DADGAD_ID = u'ca0f03b5-3c0d-4c00-aa62-bdb07f29599c'
PARIS_ID = u'17ecdfbc-c148-41d3-b898-0b5396ebe6cc'
UNICODE = True
DEFAULT_UNIX_STYLE_PATHS = True
FISHUSER = 'FISHUSER'
ALIAS_TAG = u'.fish/alias'
toStr = unicode if UNICODE else str
DEFAULT_DEBUG = True


class CacheError(Exception):
    pass


class ProblemReadingCredentialsFileError(Exception):
    pass


class BadCredentialsError(Exception):
    pass


class CredentialsFileNotFoundError(Exception):
    pass


class NotHandledYetError(Exception):
    pass


class TagPathError(Exception):
    pass


class UnexpectedGetValueError(Exception):
    pass


class CannotWriteUserError(Exception):
    pass


class FailedToCreateNamespaceError(Exception):
    pass


class ObjectNotFoundError(Exception):
    pass


class EmptyNamespaceError(Exception):
    pass


class BadStatusError(Exception):
    pass


class NonUnicodeStringError(Exception):
    pass


class STATUS:
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST= 400
    UNAUTHORIZED = 401
    PRECONDITION_FAILED = 402
    NOT_FOUND = 404
    PRECONDITION_FAILED = 412
    INTERNAL_SERVER_ERROR = 500


FLUIDDB_PATH = u'http://fluiddb.fluidinfo.com'
SANDBOX_PATH = u'http://sandbox.fluidinfo.com'
UNIX_CREDENTIALS_FILE = u'.fluidDBcredentials'
UNIX_USER_CREDENTIALS_FILE = u'.fluidDBcredentials.%s'

CRED_FILE_VAR = 'FISH_CREDENTIALS_FILE'
WIN_CRED_FILE = 'c:\\fish\\credentials.txt'

CACHE_FILE = {u'unix': u'.fishcache.%s',
              u'windows': u'c:\\fish\\credentials-%s.txt'}

HTTP_TIMEOUT = 300.123456       # unlikey the user will choose this
PRIMITIVE_CONTENT_TYPE = u'application/vnd.fluiddb.value+json'

INTEGER_RE = re.compile(ur'^[+\-]{0,1}[0-9]+$')
DECIMAL_RE = re.compile(ur'^[+\-]{0,1}[0-9]+[\.\,]{0,1}[0-9]*$')
DECIMAL_RE2 = re.compile(ur'^[+\-]{0,1}[\.\,]{1}[0-9]+$')

IDS_MAIN = {u'DADGAD': u'1fb8e9cb-70b9-4bd0-a7e7-880247384abd'}
IDS_SAND = {u'DADGAD': DADGAD_ID}

#DEFAULT_ENCODING = 'UTF-8'
DEFAULT_ENCODING = sys.getfilesystemencoding()


class SaveOut:
    def __init__(self):
        self.buffer = []

    def write(self, msg):
        self.buffer.append(msg)

    def clear(self):
        self.buffer = []

class UnicodeOut:
    def __init__(self, std):
        self.std = std

    def write(self, msg):
        self.std.write((msg.encode('UTF-8') if type(msg) == unicode else msg))
            

def human_status(c, extra=None, trans=None):
    extras = u'; [%s]' % extra if extra else ''
    translation = u' %s' % trans[c] if trans and c in trans else ''
        
    if c in STATUS.__dict__.values():
        for k in STATUS.__dict__:
            if STATUS.__dict__[k] == c:
                return u'Error Status %d (%s%s)' % (c, k, translation) + extras
    return u'Error Status %d%s' % (c, translation) + extras


class AbstractTag:
    def __init__(self, name):
        self.name = name

    def __unicode__(self):
        return self.name


class ConcreteTag:
    def __init__(self, name, value=None, about=None, id=None):
        self.name = name
        self.value = value
        self.about = about
        self.id = id

    def __unicode__(self):
        return u'%s=%s' % (self.name, repr(self.value))


class TagValue:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def __unicode__(self):
        return (u'Tag "%s", value "%s" of type %s'
                     % (self.name, toStr(self.value), toStr(type(self.value))))


class Namespace:
    def __init__(self, name):
        self.name = name

    def __unicode__(self):
        return self.name

    def toJSON(self):
        return {'item': 'namespace', 'name': self.name}

    toUnicode = __unicode__


class Cache:
    def __init__(self, username):
        self.username = username
        self.objects = {}
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
        objects = get_values_by_query(db, u'has %s' % alias_tag,
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


def quote_u_u(s):
    """Quote a unicode string s using %-encoding.

       If s is a list, each part is quoted then return, joined by slashes.

       Returns unicode.
    """
    if type(s) in (list, tuple):
        u8parts = (part.encode('UTF-8') for part in s)
        return u'/'.join(urllib.quote(p, safe='').decode('UTF-8')
                         for p in u8parts)
    else:
        return urllib.quote(s.encode('UTF-8')).decode('UTF-8')
    

def quote_u_8(s):
    """Quote a unicode string s using %-encoding.

       If s is a list, each part is quoted then return, joined by slashes.

       Returns UTF-8.
    """
    if type(s) in (list, tuple):
        u8parts = (part.encode('UTF-8') for part in s)
        return '/'.join(urllib.quote(p, safe='') for p in u8parts)
                        
    else:
        return urllib.quote(s.encode('UTF-8'))


def to_utf8(thing):
    """Returns version of thing with all unicode strings converted to UTF8"""
    if type(thing) == dict:
        return hash8(thing)
    elif type(thing) in (list, tuple):
        return [v.encode('UTF-8') if type(v) == unicode else to_utf8(v)
                for v in thing]
    elif type(thing) == unicode:
        return thing.encode('UTF-8')
    else:
        return thing

    
def hash8(hash):
    """Returns version of hash with all unicode strings converted to UTF-8"""
    h8 = {}
    for key in hash:
        h8[to_utf8(key)] = to_utf8(hash[key])
    return h8


def urlencode_hash_u_8(hash):
    """Applies urllib.urlencode to a hash that may contain unicode values."""
    return urllib.urlencode(hash8(hash), True)



def id(about, host):
    # this might turn into a cache that gets dumped to file and
    # supports more than two fixed hosts in time.
    cache = IDS_MAIN if host == FLUIDDB_PATH else IDS_SAND
    return cache[about]


def by_about(f):
    @wraps(f)
    def wrapper(self, about, *args, **kwargs):
        o = self.create_object(about=about)
        if type(o) in (int, long):   # error code
            return o, None
        return f(self, o.id, *args, **kwargs)
    return wrapper


def _get_http(timeout):
    try:
        http = Http(timeout=timeout)
    except TypeError:
        # The user's version of http2lib is old. Omit the timeout.
        http = Http()
    return http


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
        return (self.tags[t], self._types[t])

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


class Credentials:
    """
    Simple store for user credentials.
    Can be initialized with username and password
    or by pointing to a file (filename) with the username
    on the first line and the password on the second line.
    If neither password nor filename is given,
    the default credentials file will be used, if available.
    """
    def __init__(self, username=None, password=None, id=None, filename=None):
        self.unixStyle = DEFAULT_UNIX_STYLE_PATHS
        if username and password:
            self.username = username
            self.password = password
        else:
            e = os.environ
            if FISHUSER in e:
                filename = get_credentials_file(username=e[FISHUSER])
            if filename == None:
                filename = get_credentials_file(username=username)
            if os.path.exists(filename):
                try:
                    if os.name == 'posix':
                        f = codecs.open(filename, 'UTF-8')
                    else:
                        f = open(filename)
                    lines = f.readlines()
                    self.username = lines[0].strip().decode('UTF-8')
                    self.password = lines[1].strip().decode('UTF-8')
                    if len(lines) >= 3:
                        unixLine = lines[2].strip().lower()
                        if unixLine.startswith('unix-style-paths'):
                            if unixLine.endswith('true'):
                                self.unixStyle = True
                            elif unixLine.endswith('false'):
                                self.unixStyle = False
                            else:
                                raise ProblemReadingCredentialsFileError(
                                      u'Bad unix-style-paths statement in %s'
                                      % toStr(filename))
                    f.close()
                except:
                    raise ProblemReadingCredentialsFileError(u'Failed to read'
                            ' credentials from %s.' % toStr(filename))
            else:
                raise CredentialsFileNotFoundError(u'\nCouldn\'t find or '
                          'read credentials from the expected location:\n%s'
                           % toStr(filename))

        self.id = id


def format_param(v):
    return quote_u_8(v) if type(v) == unicode else str(v)


def formatted_tag_value(tag, value, terse=False, prefix=u'  '):
    lhs = '' if terse else '%s%s = ' % (prefix, tag)
    if value == None:
        return u'%s%s' % (u'' if terse else prefix, tag)
    elif type(value) in types.StringTypes:
        return u'%s"%s"' % (lhs, value)
    elif type(value) in (list, tuple):
        vals = value[:]
        vals.sort()
        return u'%s{%s}' % (lhs,
                             u', '.join(u'"%s"' % unicode(v) for v in vals))
    else:
        return u'%s%s' % (lhs, toStr(value))


class Fluidinfo:
    """
    Connection to Fluidinfo that remembers credentials and provides
    methods for some of the common operations.

    Although currently unused, the unixStylePaths parameter
    can be used to choose whether to use unix-style paths for tags,
    namespaces etc.

    saveOutput may be:
       False (just print)
       True (save text)
       'json' (save json dictionary)
       'python' (save python objects)
    """

    def __init__(self, credentials=None, host=None, debug=DEFAULT_DEBUG,
                 encoding=DEFAULT_ENCODING, unixStylePaths=None,
                 saveOutput=False):
        if credentials == None:
            credentials = Credentials()
        self.credentials = credentials
        if unixStylePaths == None:
            self.unixStyle = credentials.unixStyle
        else:
            assert unixStylePaths in (True, False)
            self.unixStyle = unixStylePaths
        if host is None:
            host = choose_host()
        self.host = host
        self.debug = debug
        self.encoding = encoding
        self.saveOutput = saveOutput
        assert saveOutput in (True, False, u'python', u'json')
        self.buffer = []
        self.timeout = choose_http_timeout()
        if not host.startswith(u'http'):
            self.host = u'http://%s' % host
        # the following based on fluiddb.py
        userpass = u'%s:%s' % (credentials.username, credentials.password)
        encoded = unicode(userpass.encode('UTF-8').encode('base64').strip())
        auth = u'Basic %s' % encoded
        self.headers = {
            u'Authorization': auth
        }
        self.cache = Cache(self.credentials.username)

    def Print(self, s, allowSave=True, allowPrint=True):
        if self.saveOutput:
            if  allowSave:
                self.buffer.append(s)
        elif allowPrint:
            if type(s) in types.StringTypes:
                print s.encode('UTF-8') if type(s) == unicode else s
            else:
                print s.toUnicode().encode('UTF-8')

    def warning(self, msg):
        self.Print(u'%s\n' % msg)

    def nothing_to_do():
        self.Print(self, u'Nothing to do.')
        raise Exception, msg

    def _get_url(self, host, path, hash, kw):
        """returns URL as unicode
        """
        url = host.encode('UTF-8') + quote_u_8(path)
        if hash:
            url = '%s?%s' % (url, urlencode_hash_u_8(hash))
        elif kw:
            kwds = '&'.join('%s=%s' % (k.encode('UTF-8'),
                                       format_param(kw[k])) for k in kw)

            url = '%s?%s' % (url, kwds)
        return url.decode('UTF-8')

    def set_connection_from_global(self):
        """
        Sets the host on the basis of the global variable flags,
        if that exists.   Used to enable the tests to run against
        alternate hosts.
        """
        self.host = choose_host()
        self.debug = choose_debug_mode()
        self.timeout = choose_http_timeout()

    def set_debug_timeout(self, v):
        if self.timeout == HTTP_TIMEOUT:
            self.timeout = float(v)

    def call(self, method, path, body=None, hash=None, **kw):
        """
        Calls Fluidinfo with the attributes given.
        This function was lifted nearly verbatim from fluiddb.py,
        by Sanghyeon Seo, with additions by Nicholas Tollervey.

        Returns: a 2-tuple consisting of the status and result
        """
        headers = self.headers.copy()
        if body:
            headers[u'content-type'] = u'application/json'

        k2 = {}
        for k in kw:
            k2[k] = (kw[k].decode('UTF-8')
                     if type(kw[k]) == types.StringType else kw[k])
        kw = k2
        url = self._get_url(self.host, path, hash, kw)

        if self.debug:
            self.Print(u'\nmethod: %r\nurl: %r\nbody: %s\nheaders:' %
                       (method, url, body))
            for k in headers:
                if not k == u'Authorization':
                    self.Print(u'  %s=%s' % (k, headers[k]))
        body8 = body.encode('UTF-8') if type(body) == unicode else body
        try:
            response, content, result, status = self.request(url, method,
                                                         body8, headers)
        except:
            raise Exception(url)

            
        return status, result

    def request(self, url, method, body8, headers):
        http = _get_http(self.timeout)
        response, content = http.request(url, method, body8, headers)
        status = response.status
        if response[u'content-type'].startswith(u'application/json'):
            result = json.loads(content)
        else:
            result = content
        if self.debug or status == STATUS.INTERNAL_SERVER_ERROR:
            self.Print(u'status: %d; content: %s' % (status, toStr(result)))
            if status >= 400:
                for header in response:
                    if header.lower().startswith(u'x-fluiddb-'):
                        self.Print(u'\t%s=%s'
                                   % (header.decode('UTF-8'),
                                      response[header].decode('UTF-8')))
        return (response, content, result, status)
        

    def _get_tag_value(self, path):
        headers = self.headers.copy()
        url = self._get_url(self.host, path, hash=None, kw=None)
        if self.debug:
            self.Print(u'\nShow URL: %s' % url)
        response, content, result, status = self.request(url, u'GET',
                                                         None, headers)
        content_type = response[u'content-type']
        if content_type == PRIMITIVE_CONTENT_TYPE:
            result = json.loads(content)
            content_type = None
        else:
            result = content
        return status, (result, content_type)

    def _set_tag_value(self, path, value, value_type=None):
        headers = self.headers.copy()
        if value_type is None:
            value = json.dumps(value)
            value_type = PRIMITIVE_CONTENT_TYPE
        headers[u'content-type'] = value_type
        url = self._get_url(self.host, path, hash=None, kw=None)
        http = _get_http(self.timeout)
        if self.debug:
            self.Print(u'\nTag URL: %s' % url)
            self.Print(u'Value: %s' % value)
        response, content, result, status = self.request(url, u'PUT',
                                                value.encode('UTF-8'),
                                                headers)
        return status, content

    def create_object(self, about=None):
        """
        Creates an object with the about tag given.
        If the object already exists, returns the object instead.

        Returns: the object returned if successful, wrapped up in
        an (O) object whose class variables correspond to the
        values returned by Fluidinfo, in particular, o.id and o.URL.
        If there's a failure, the return value is an integer error code.
        """
        if about:
            body = json.dumps({u'about': about})
        else:
            body = None
        (status, o) = self.call(u'POST', u'/objects', body)
        return (O({u'URI': o[u'URI']}, id=o[u'id']) if status == STATUS.CREATED
                                                    else status)

    def create_namespace(self, path, description=u'',
                         createParentIfNeeded=True, verbose=False):
        """
        Creates the namespace specified by path using the description
        given.

        If the parent namespace does not exist, by default it is created
        with a blank description; however, this behaviour can be
        overridden by setting createParentIfNeeded to False, in which
        case NOT_FOUND will be returned in this case.

        Any trailing slash is deleted.

        The path, as usual in FDB, is considered absolute if it starts
        with a slash, and relative to the user's namespace otherwise.

        Returns ID of namespace object if created successfully.
        If not, but the request is well formed, the error code returned
        by Fluidinfo is returned.

        If the request is ill-formed (doesn't look like a valid namespace),
        an exception is raised.
        """
        fullPath = self.abs_tag_path(path)    # now it starts with /user
        parts = fullPath.split(u'/')[1:]      # remove '' before leading '/'
        if parts[-1] == u'':
            parts = parts      # ignore a trailing slash, if there was one
        if len(parts) < 2:     # minimum is 'user' and 'namespace'
            raise EmptyNamespaceError(u'Attempt to create user namespace %s'
                                           % fullPath)
        parent = u'/'.join(parts[:-1])
        containingNS = u'/namespaces/%s' % parent
        subNS = parts[-1]
        body = json.dumps({u'name': subNS,
                           u'description': description or u''})
        status, result = self.call(u'POST', containingNS, body)
        if status == STATUS.CREATED:
            id = result[u'id']
            if verbose:
                self.Print(u'Created namespace /%s/%s with ID %s' % (parent,
                                                                    subNS, id))
            return id
        elif status == STATUS.NOT_FOUND:    # parent namespace doesn't exist
            if not createParentIfNeeded:
                return status
            if len(parts) > 2:
                self.create_namespace(u'/' + parent, verbose=verbose)
                return self.create_namespace(path, description,
                                              verbose=verbose)  # try again
            else:
                user = parts[-1]
                raise CannotWriteUserError(u'User %s not found or namespace '
                                           u'/%s not writable' % (user, user))
        else:
            if verbose:
                self.Print(u'Failed to create namespace %s (%d)' % (fullPath,
                                                                    status))
            return status

    def delete_namespace(self, path, recurse=False, force=False,
                         verbose=False):
        """Deletes the namespace specified by path.

           The path, as usual in FDB, is considered absolute if it starts
           with a slash, and relative to the user's namespace otherwise.

           recurse and force are not yet implemented.
        """
        absPath = self.abs_tag_path(path)
        fullPath = u'/namespaces' + absPath
        if fullPath.endswith(u'/'):
            fullPath = fullPath[:-1]
        status, result = self.call('DELETE', fullPath)
        if verbose:
            if status == STATUS.NO_CONTENT:
                self.Print(u'Removed namespace %s' % absPath)
            else:
                self.Print(u'Failed to remove namespace %s (%d)'
                           % (absPath, status))
        return 0 if status == STATUS.NO_CONTENT else status

    def describe_namespace(self, path):
        """Returns an object describing the namespace specified by the path.

           The path, as usual in FDB, is considered absolute if it starts
           with a slash, and relative to the user's namespace otherwise.

           The object contains attributes tagNames, namespaceNames and
           path.

           If the call is unsuccessful, an error code is returned instead.
        """
        absPath = self.abs_tag_path(path)
        fullPath = u'/namespaces' + absPath
        if fullPath.endswith(u'/'):
            fullPath = fullPath[:-1]
        status, result = self.call(u'GET', fullPath, returnDescription=True,
                                   returnTags=True, returnNamespaces=True)
        return O(result) if status == STATUS.OK else status

    def create_abstract_tag(self, tag, description=None, indexed=True,
                            inPref=False):
        """Creates an (abstract) tag with the name (full path) given.
           The tag is not applied to any object.
           If the tag's name (tag) contains slashes, namespaces are created
           as needed.

           Doesn't handle tags with subnamespaces yet.

           Returns (O) object corresponding to the tag if successful,
           otherwise an integer error code.
        """
        absTag = self.abs_tag_path(tag, inPref=inPref)
        (user, subnamespace, tagname) = self.tag_path_split(absTag)
        if subnamespace:
            fullnamespace = u'/tags/%s/%s' % (user, subnamespace)
        else:
            fullnamespace = u'/tags/%s' % user
        hash = {u'indexed': indexed, u'description': description or '',
                u'name': tagname}
        fields = json.dumps(hash)
        (status, o) = self.call(u'POST', fullnamespace, fields)
        if status == STATUS.NOT_FOUND:
            namespace = u'/%s/%s' % (user, subnamespace)
            id = self.create_namespace(namespace)
            if type(id) in types.StringTypes:  # is an ID
                (status, o) = self.call(u'POST', fullnamespace, fields)
            else:
                raise FailedToCreateNamespaceError(u'FDB could not create'
                        u' the required namespace %s' % namespace)
        return O(o, id=o[u'id']) if status == STATUS.CREATED else status

    def delete_abstract_tag(self, tag):
        """Deletes an abstract tag, removing all of its concrete
           instances from objects.   Use with care.
           So db.delete_abstract_tag('njr/rating') removes
           the njr/rating from ALL OBJECTS IN FLUIDDB.

           Returns 0 if successful; otherwise returns an integer error code.
        """
        fullTag = self.full_tag_path(tag)
        (status, o) = self.call('DELETE', fullTag)
        return 0 if status == STATUS.NO_CONTENT else status

    def path_parts(self, byAbout, spec, tag=None, inPref=False):
        path = u'about' if byAbout else u'objects'
        base = [u'', path, spec]
        if tag:
            return base + self.abs_tag_path(tag, inPref=inPref).split(u'/')[1:]
        else:
            return base

    def tag_object(self, spec, tag, byAbout, value=None, value_type=None,
                   createAbstractTagIfNeeded=True, inPref=False):
                         
        """Tags the object with the given id with the tag
           given, and the value given, if present.
           If the (abstract) tag with corresponding to the
           tag given doesn't exist, it is created unless
           createAbstractTagIfNeeded is set to False.
        """
        objTagParts = self.path_parts(byAbout, spec, tag, inPref)
        (status, o) = self._set_tag_value(objTagParts, value, value_type)
        if status == STATUS.NOT_FOUND and createAbstractTagIfNeeded:
            o = self.create_abstract_tag(tag, inPref=inPref)
            if type(o) in (int, long):       # error code
                return o
            else:
                return self.tag_object(spec, tag, byAbout, value, value_type,
                                       False, inPref=inPref)
        else:
            return 0 if status == STATUS.NO_CONTENT else status

    def tag_object_by_id(self, id, tag, value=None, value_type=None,
                         createAbstractTagIfNeeded=True, inPref=False):
        return self.tag_object(id, tag, False, value, value_type,
                               createAbstractTagIfNeeded, inPref)

    def tag_object_by_about(self, about, tag, value=None, value_type=None,
                            createAbstractTagIfNeeded=True, inPref=False):
        return self.tag_object(about, tag, True, value, value_type,
                               createAbstractTagIfNeeded, inPref)

    def untag_object(self, spec, tag, byAbout, missingConstitutesSuccess=True,
                     inPref=False):
        """Removes the tag from the object f present.
           If the tag, or the object, doesn't exist,
           the default is that this is considered successful,
           but missingConstitutesSuccess can be set to False
           to override this behaviour.

           spec is the id or about tag for the object, and with
           with byAbout being true if it is an about tag.

           Returns 0 for success, non-zero error code otherwise.
        """
        objTagParts = self.path_parts(byAbout, spec, tag, inPref)
        (status, o) = self.call('DELETE', objTagParts)
        ok = (status == STATUS.NO_CONTENT
              or status == STATUS.NOT_FOUND and missingConstitutesSuccess)
        return 0 if ok else status

    def untag_object_by_id(self, id, tag, missingConstitutesSuccess=True,
                           inPref=False):
        return self.untag_object(id, tag, False, True, inPref)

    def untag_object_by_about(self, about, tag, missingConstitutesSuccess=True,
                              inPref=False):
        return self.untag_object(about, tag, True, True, inPref)


    def get_tag_value(self, spec, tag, byAbout, inPref=False, getMime=False):
        """Gets the value of a tag on an object identified by the
           object's ID or about value..

           spec is the id or about tag for the object, and with
           with byAbout being true if it is an about tag.

           Returns  returns a 2-tuple, in which the first component
           is the status, and the second is either the tag value,
           if the return stats is STATUS.OK, or None otherwise.
        """
        objTagParts = self.path_parts(byAbout, spec, tag, inPref)
        status, (value, value_type) = self._get_tag_value(objTagParts)
        if getMime:
            return status, (value if status == STATUS.OK else None, value_type)
        else:
            return status, (value if status == STATUS.OK else None)

    def get_tag_value_by_id(self, id, tag, inPref=False, getMime=False):
        return self.get_tag_value(id, tag, False, inPref)
    
    def get_tag_value_by_about(self, about, tag, inPref=False, getMime=False):
        return self.get_tag_value(about, tag, True, inPref)

    def get_tag_values_by_id(self, id, tags):
        return [self.get_tag_value_by_id(id, tag) for tag in tags]

    def get_tag_values_by_about(self, about, tags):
        return [self.get_tag_value_by_about(about, tag) for tag in tags]

    def get_object_tags(self, spec, byAbout):
        """Gets the tags on an tag identified by the object's ID.

           Returns list of tags.
        """
        objParts = self.path_parts(byAbout, spec)
        status, (value, value_type) = self._get_tag_value(objParts)
        if status == STATUS.OK:
            result = json.loads(value)
            return result[u'tagPaths']
        else:
            raise ObjectNotFoundError(u'Couldn\'t find object %s' % obj)

    def get_object_tags_by_id(self, id):
        return self.get_object_tags(id, False)

    def get_object_tags_by_about(self, about):
        return self.get_object_tags(about, True)

    def query(self, query):
        """Runs the query to get the IDs of objects satisfying the query.
           If the query is successful, the list of ids is returned, as a list;
           otherwise, an error code is returned.
        """
        (status, o) = self.call(u'GET', u'/objects', query=query)
        return status if status != STATUS.OK else o[u'ids']

    def abs_tag_path(self, tag, inPref=False, outPref=False):
        """
        Returns the absolute path for the tag nominated,
        usually in the form
            /namespace/.../shortTagName
        If the already tag starts with a '/', no action is taken;
        if it doesn't, the username from the current credentials
        is added.

        if /tags/ is present at the start of the path,
        /tags is stripped off (which might be a problem if there's
        a user called tags...

        Always returns unicode.

        Examples: (assuming the user credentials username is njr):
            abs_tag_path('rating') = u'/njr/rating'
            abs_tag_path('/njr/rating') = u'/njr/rating'
            abs_tag_path('/tags/njr/rating') = u'/njr/rating'

            abs_tag_path('foo/rating') = u'/njr/foo/rating'
            abs_tag_path('/njr/foo/rating') = u'/njr/foo/rating'
            abs_tag_path('/tags/njr/foo/rating') = u'/njr/foo/rating'

        The behaviour is modified if inPref or outPref is set to True.

        Setting inPref to True will change the way the input is handled
        if the self.unixStyle is False.   In this case, the input will
        be assume to be a Fluidinfo-style path already, i.e. it will
        be assumed to be a full path with no leading slash.

        Setting outPref to True will change the way the input is handled
        if the self.unixStyle is False.   In this case, the output will
        not have a leading slash.
        """
        inUnix = self.unixStyle if inPref else True
        outUnix = self.unixStyle if outPref else True
        outPrefix = u'/' if outUnix else u''
        if inUnix:
            if tag == u'/about':     # special case
                return u'%sfluiddb/about' % outPrefix
            if tag.startswith(u'/'):
                if tag.startswith(u'/tags/'):
                    return u'%s%s' % (outPrefix, tag[6:])
                else:
                    return u'%s%s' % (outPrefix, tag[1:])
            else:
                return u'%s%s/%s' % (outPrefix,
                                     self.credentials.username,
                                     tag)
        else:
            return u'%s%s' % (outPrefix, tag)

    def full_tag_path(self, tag):
        """Returns the absolute tag path (see above), prefixed with /tag.

           Examples: (assuming the user credentials username is njr):
                full_tag_path ('rating') = '/tags/njr/rating'
                full_tag_path ('/njr/rating') = '/tags/njr/rating'
                full_tag_path ('/tags/njr/rating') = '/tags/njr/rating'
                full_tag_path('foo/rating') = '/tags/njr/foo/rating'
                full_tag_path('/njr/foo/rating') = '/tags/njr/foo/rating'
                full_tag_path('/tags/njr/foo/rating') = '/tags/njr/foo/rating'
        """
        if tag.startswith(u'/tags/'):
            return tag
        else:
            return u'/tags%s' % self.abs_tag_path(tag)

    def tag_path_split(self, tag):
        """A bit like os.path.split, this splits any old kind of a Fluidinfo
           tag path into a user, a subnamespace (if there is one) and a tag.
           But unlike os.path.split, if no namespace is given,
           the one from the user credentials is returned.

           Any /tags/ prefix is discarded and the namespace is returned
           with no leading '/'.

           Examples: (assuming the user credentials username is njr):
                tag_path_split('rating') = (u'njr', u'', u'rating')
                tag_path_split('/njr/rating') = (u'njr', u'', u'rating')
                tag_path_split('/tags/njr/rating') = (u'njr', u'', u'rating')
                tag_path_split('foo/rating') = (u'njr', u'foo', u'rating')
                tag_path_split('/njr/foo/rating') = (u'njr', u'foo', u'rating')
                tag_path_split('/tags/njr/foo/rating') = (u'njr', u'foo',
                                                                  u'rating')
                tag_path_split('foo/bar/rating') = (u'njr', u'foo/bar',
                                                    u'rating')
                tag_path_split('/njr/foo/bar/rating') = (u'njr', u'foo/bar',
                                                                 u'rating')
                tag_path_split('/tags/njr/foo/bar/rating') = (u'njr',
                                                              u'foo/bar',
                                                              u'rating')

           Returns (user, subnamespace, tagname)
        """
        if tag in (u'', u'/'):
            raise TagPathError(u'%s is not a valid tag path' % tag)
        tag = self.abs_tag_path(tag)
        parts = tag.split(u'/')
        subnamespace = u''
        tagname = parts[-1]
        if len(parts) < 3:
            raise TagPathError(u'%s is not a valid tag path' % tag)
        user = parts[1]
        if len(parts) > 3:
            subnamespace = u'/'.join(parts[2:-1])
        return (user, subnamespace, tagname)

    def tag_exists(self, tag):
        (status, o) = self.call(u'GET', u'/tags' + self.abs_tag_path(tag))
        return status == 200
        
    def ns_exists(self, ns):
        (status, o) = self.call(u'GET', u'/namespaces' + self.abs_tag_path(ns))
        return status == 200

    def read_tags(self, about, o):
        return get_values_by_query(self, u'fluiddb/about = "%s"' % about,
                            [k for k in o.tags])

    def write_tags(self, about, o):
        values = {}
        for k in o.tags:
            if not k.startswith(u'_'):
                values[k] = o.tags[k]
        return tag_by_query(self, u'fluiddb/about = "%s"' % about, values)
                            


def object_uri(id):
    """Returns the full URI for the Fluidinfo object with the given id."""
    return u'%s/objects/%s' % (FLUIDDB_PATH, id)


def tag_uri(namespace, tag):
    """Returns the full URI for the Fluidinfo tag with the given id."""
    return u'%s/tags/%s/%s' % (FLUIDDB_PATH, namespace, tag)


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
    

def get_typed_tag_value(v):
    """Uses some simple rules to extract simple typed values from strings.
        Specifically:
           true and t (any case) return True (boolean)
           false and f (any case) return False (boolean)
           simple integers (possibly signed) are returned as ints
           simple floats (possibly signed) are returned as floats
                (supports '.' and ',' as floating-point separator,
                 subject to locale)
           Everything else is returned as a string, with matched
                enclosing quotes stripped.
    """
    if v.lower() in (u'true', u't'):
        return True
    elif v.lower() in (u'false', u'f'):
        return False
    elif re.match(INTEGER_RE, v):
        return int(v)
    elif re.match(DECIMAL_RE, v) or re.match(DECIMAL_RE2, v):
        try:
            r = float(v)
        except ValueError:
            return toStr(v)
        return r
    elif len(v) > 1 and v[0] == v[-1] and v[0] in (u'"\''):
        return v[1:-1]
    elif len(v) > 1 and v[0] == u'{' and v[-1] == '}':
         return cline.CScanSplit(v[1:-1], ' \t,', quotes='"\'').words
    else:
        return toStr(v)


def choose_host():
    if u'options' in globals():
        host = options.hostname
        if options.verbose:
            self.Print(u"Chosen %s as host" % host)
        return host
    else:
        return FLUIDDB_PATH


def choose_debug_mode():
    return options.debug if u'options' in globals() else False


def choose_http_timeout():
    return (options.timeout if u'options' in globals() else HTTP_TIMEOUT)


#
# VALUES API:
#
# Note: these calls are different from the rest of fish.py (at present)
# in that (1) they used full Fluidinfo paths with no leading slash,
# and (2) they use unicode throughout (3) tags must exist before being used.
# Things will be made more consistent over time.
#

def format_val(s):
    """
    Formats a value for json (unicode).
    """
    if type(s) == type('s'):
        raise NonUnicodeStringError
    elif type(s) == unicode:
        if s.startswith(u'"') and s.endsswith(u'"'):
            return s
        else:
            return u'"%s"' % s
    elif type(s) == bool:
        return unicode(s).lower()
    elif s is None:
        return u'null'
    else:
        return unicode(s)


def to_typed(v):
    """
    Turns json-formatted string into python value.
    Unicode.
    """
    L = v.lower()
    if v.startswith(u'"') and v.startswith(u'"') and len(v) >= 2:
        return v[1:-1]
    elif v.startswith(u"'") and v.startswith(u"'") and len(v) >= 2:
        return v[1:-1]
    elif L == u'true':
        return True
    elif L == u'false':
        return False
    elif re.match(INTEGER_RE, v):
        return int(v)
    elif re.match(DECIMAL_RE, v) or re.match(DECIMAL_RE2, v):
        try:
            r = float(v)
        except ValueError:
            return unicode(v)
        return r
    else:
        return unicode(v)


def tag_by_query(db, query, tagsToSet):
    """
    Sets one or more tags on objects that match a query.

    db         is an instantiated Fluidinfo instance.

    query      is a unicode string representing a valid Fluidinfo query.
               e.g. 'has njr/rating'

    tagsToSet  is a dictionary containing tag names (as keys)
               and values to be set.   (Use None to set a tag with no value.)

    Example:

        db = Fluidinfo()
        tag_by_query(db, u'has njr/rating', {'njr/rated': True})

    sets an njr/rated tag to True for every object having an njr/rating.

    NOTE: Unlike in much of the rest of fish.py, tags need to be full paths
    without a leading slash.

    NOTE: Tags must exist before being used.   (This will change.)

    NOTE: All strings must be (and will be) unicode.


    """
    strHash = u'{%s}' % u', '.join(u'"%s": {"value": %s}'
                                   % (tag, format_val(tagsToSet[tag]))
                                   for tag in tagsToSet)
    (v, r) = db.call(u'PUT', u'/values', strHash, {u'query': query})
    assert_status(v, STATUS.NO_CONTENT)


def untag_by_query(db, query, tags):
    """
    Deletes one or more tags on objects that match a query.

    db         is an instantiated Fluidinfo instance.

    query      is a unicode string representing a valid Fluidinfo query.
               e.g. 'has njr/rating'

    tags       a list tag names to delete.

    Example:

        db = Fluidinfo()
        untag_by_query(db, u'has njr/rating', ['njr/rating'])

    removes an njr/rating tag from every object that has one.

    NOTE: Unlike in much of the rest of fish.py, tags need to be full paths
    without a leading slash.   (This will change.)

    NOTE: All strings must be (and will be) unicode.


    """
    if not tags:
        return
    kw = {u'tag': tags, u'query': query}
    (v, r) = db.call(u'DELETE', u'/values', None, kw)
    assert_status(v, STATUS.NO_CONTENT)


def assert_status(v, s):
    if not v == s:
        raise BadStatusError(u'Bad status %d (expected %d)' % (v, s))


def get_values_by_query(db, query, tags):
    """
    Gets the values of a set of tags satisfying a given query.
    Returns them as a dictionary (hash) keyed on object ID.
    The values in the dictionary are simple objects with each tag
    value in the object's dictionary (__dict__).

    db         is an instantiated Fluidinfo instance.

    query      is a unicode string representing a valid Fluidinfo query.
               e.g. 'has njr/rating'

    tags       is a list (or tuple) containing the tags whose values are
               required.

    Example:

        db = Fluidinfo()
        tag_by_query(db, u'has njr/rating < 3', ('fluiddb/about',))

    NOTE: Unlike in much of the rest of fish.py, tags need to be full paths
    without a leading slash.

    NOTE: All strings must be (and will be) unicode.

    """
    maxTextSize = 1024
    (v, r) = db.call(u'GET', u'/values', None, {u'query': query,
                                                u'tag': tags})
    assert_status(v, STATUS.OK)
    H = r[u'results'][u'id']
    results = []
    for id in H:
        o = O()
        o.id = id
        for tag in tags:
            if tag in H[id]:
                try:
                    if tag == u'fluiddb/about':
                        o.about = H[id][tag][u'value']
                    else:
                        o.tags[tag] = H[id][tag][u'value']
                        o.types[tag] = None
                except KeyError:
                    size = H[id][tag][u'size']
                    mime = H[id][tag][u'value-type']
                    if (mime.startswith(u'text')
                            and size < maxTextSize):
                        o.tags[tag] = db.get_tag_value_by_about(id,
                                                            u'/%s' % tag)
                    else:
                        o.tags[tag] = (u'%s value of size %d bytes' % (mime,
                                                                     size))
                    o.types[tag] = mime
        results.append(o)
    return results      # hash of objects, keyed on ID, with attributes
                        # corresponding to tags, inc id.
        

def get_values_by_id(db, id, tags):
    """
    Gets the values of a set of tags satisfying a given query.
    Returns them as a dictionary (hash) keyed on object ID.
    The values in the dictionary are simple objects with each tag
    value in the object's dictionary (tags).

    db         is an instantiated Fluidinfo instance.

    query      is a unicode string representing a valid Fluidinfo query.
               e.g. 'has njr/rating'

    tags       is a list (or tuple) containing the tags whose values are
               required.

    Example:

        db = Fluidinfo()
        tag_by_query(db, u'has njr/rating < 3', ('fluiddb/about',))

    NOTE: Unlike in much of the rest of fish.py, tags need to be full paths
    without a leading slash.

    NOTE: All strings must be (and will be) unicode.

    """
    maxTextSize = 1024
    o = O()
    o.id = id
    for tag in tags:
        status, value, mime = db.get_tag_value_by_id(id, tag, getMime=True)
        assert_status(v, STATUS.OK)
        o.tags[tag] = value
        o.tags[tag] = None if mime == PRIMITIVE_CONTENT_TYPE else 0
        if (mime.startswith(u'text') and size < maxTextSize):
            o.tags[tag] = db.get_tag_value_by_about(id, u'/%s' % tag)
        else:
            o.tags[tag] = (u'%s value of size %d bytes' % (mime, size))
    return o
        

def path_style(options):
    if options.unixstylepaths:
        unixStyle = True
    elif options.fluidinfostylepaths:
        unixStyle = False
    else:
        unixStyle=None
    return unixStyle


def version():
    return __version__


def uprint(s):
    Print(s.encode('UTF-8') if type(s) == unicode else s)
