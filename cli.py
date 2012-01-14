# -*- coding: utf-8 -*-
#
# cli.py
#
# Copyright (c) Nicholas J. Radcliffe 2009-2012 and other authors specified
#               in the AUTHOR
# Licence terms in LICENCE.

import os
import re
import shutil
import sys
import time
import types
import traceback
from optparse import OptionParser, OptionGroup
from itertools import chain, imap
from fishbase import get_credentials_file, Dummy
from fishlib import (
    Fluidinfo,
    O,
    Credentials,
    get_typed_tag_value,
    get_typed_tag_value_from_file,
    path_style,
    toStr,
    formatted_tag_value,
    version,
    DEFAULT_ENCODING,
    STATUS,
    DADGAD_ID,
    PARIS_ID,
    HTTP_TIMEOUT,
    SANDBOX_PATH,
    FLUIDDB_PATH,
    INTEGER_RE,
    INTEGER_RANGE_RE,
    UUID_RE,
    json,
    TagValue,
    Namespace,
)
from cache import ALIAS_TAG
import ls
import flags
import cline
try:
    import abouttag.amazon
    import abouttag.generic
    import abouttag.nacolike
except ImportError:
    pass


ARGLESS_COMMANDS = ['count', 'tags', 'ls', 'pwd', 'pwn', 'whoami', 'quit',
                    'exit', 'alias', 'showcache', 'sync', 'init']

AT_ERROR = (u'You need the abouttag library to use the abouttag command.\n'
            u'This is available from http://github.com/njr0/abouttag.')

USAGE = u'''

For help with a specific command, type help followed by the command name.
For a list of commands, type commands.

 Tag objects:
   tag -a 'Paris' /alice/visited /alice/rating=10
   tag -i %s /bert/visited /bert/rating=10
   tag -q 'fluiddb/about = "Paris"' /alice/visited /alice/rating=10
   [On windows: tag -q "about = "Paris""" /alice/visited /alice/rating=10

 Untag objects:
   untag -a 'Paris' /bert/visited /alice/rating
   untag -i %s
   untag -q 'fluiddb/about = "Paris"' /alice/visited /alice/rating

 Fetch objects and show tags
   show -a 'Paris' /bert/visited /bert/rating
   show -i %s /alice/visited /alice/rating
   show -q 'fluiddb/about = "Paris"' /alice/visited /alice/rating

 Count objects matching query:
   count -q 'has fluiddb/users/username'

 Get tags on objects and their values:
   tags -a 'Paris'
   tags -i %s

 Tag and Namespace management:
   ls [flags]          list the contents of a namespace or list a tag
   perms spec paths    change the permissions on tags or namespaces
   rm [flags] paths    remove one or more namespaces or tags
   touch [flags] path  create an (abstract) tag (normally unnecessary)
   mkns [flags] path   create a namespace (normally unnecessary)
   pwd / pwn           prints root namespace of authenticated user

About Tag Construction
   abouttag kind spec  construct an about tag for object of kind specified
   amazon 'url'        show the about tag for a book on ana Amazon US/UK page
   normalize parts     Normalize the parts specified, joining with colons

 Miscellaneous:
   whoami              prints username for authenticated user
   su fiuser           set Fish to use user credentials for fiuser
   help [command]      show this help, or help for the nominated comamnd.
   commands            show a list of available commands
   quit / exit         leave Fish

 Run Tests:
   test                runs all tests
   testcli             tests command line interface only
   testdb              tests core Fluidinfo interface only
   testutil            runs tests not requiring Fluidinfo access


''' % (PARIS_ID, PARIS_ID, PARIS_ID, PARIS_ID)

USAGE_FI = USAGE.replace('/about', 'fluiddb/about').replace('/alice',
                         'alice').replace('/bert', 'bert')
USAGE_FISH = USAGE.replace('/alice/','')



class ModeError(Exception):
    pass


class TooFewArgsForHTTPError(Exception):
    pass


class UnrecognizedHTTPMethodError(Exception):
    pass


class CommandError(Exception):
    pass


def error_code(n):
    code = STATUS.__dict__
    for key in code:
        if n == code[key]:
            return unicode('%d (%s)' % (n, key.replace('_', ' ')))
    return unicode(n)


def execute_tag_command(objs, db, tags, options, action):
    if options.force and db.webapp:
        raise CommandError(u'No file system available for the web.')
    tags = form_tag_value_pairs(tags, options)
    for obj in objs:
        description = describe_by_mode(obj)
        for tag in tags:
            if obj.about:
                o = db.tag_object_by_about(obj.about, tag.name, tag.value,
                                           value_type=tag.mime,
                                           inPref=True)
            else:
                o = db.tag_object_by_id(obj.id, tag.name, tag.value,
                                        value_type=tag.mime,
                                        inPref=True)
            if o == 0:
                if options.verbose or options.anon:
                    db.Print(u'Tagged object %s with %s'
                             % (description,
                                formatted_tag_value(tag.name, tag.value,
                                                    prefix=u'')))
            else:
                db.warning(u'Failed to tag object %s with %s'
                        % (description, tag.name))
                db.warning(u'Error code %s' % error_code(o))

    return o  # 0 if OK


def execute_untag_command(objs, db, tags, options, action):
    for obj in objs:
        description = describe_by_mode(obj)
        for tag in tags:
            if obj.about:
                o = db.untag_object_by_about(obj.about, tag, inPref=True)
            else:
                o = db.untag_object_by_id(obj.id, tag, inPref=True)
            if o == 0:
                if options.verbose:
                    db.Print('Removed tag %s from object %s\n'
                             % (tag, description))
            else:
                db.warning(u'Failed to remove tag %s from object %s'
                        % (tag, description))
                db.warning(u'Error code %s' % error_code(o))


def sort_tags(tags):
    tags.sort()
    for t in ['fluiddb/about', '/about', '/fluiddb/about']:
        try:
            i = tags.index(t)
            if i > 0:
                del tags[i]
                tags = [t] + tags
        except ValueError:
            pass
    return tags


def execute_show_command(objs, db, tags, options, action):
    actions = {
        u'id': db.get_tag_value_by_id,
        u'about': db.get_tag_value_by_about,
    }
    terse = (action == u'get')
    for obj in objs:
        description = describe_by_mode(obj)
        if not terse:
            db.Print(u'Object %s:' % description)
#            tags = sort_tags(tags)
        for tag in tags:
            fulltag = db.abs_tag_path(tag, inPref=True)
            outtag = db.abs_tag_path(tag, inPref=True, outPref=True)
            if tag == u'/id':
                t = None
                if obj.about:
                    o = db.query(u'fluiddb/about = "%s"' % obj.about)
                    if type(o) == types.IntType:  # error
                        status, v = o, None
                    else:
                        status, v = STATUS.OK, o[0]
                else:
                    status, v = STATUS.OK, obj.id
            else:
                if obj.about:
                    status, (v, t) = db.get_tag_value_by_about(obj.about, tag,
                                                               inPref=True,
                                                               getMime=True)
                else:
                    status, (v, t)  = db.get_tag_value_by_id(obj.id, tag,
                                                             inPref=True,
                                                             getMime=True)

            saveForNow = True   # while getting ready to move to objects
            if status == STATUS.OK:
                db.Print(formatted_tag_value(outtag, v, terse, mime=t),
                         allowSave=saveForNow)
                obj.tags[outtag] = v
            elif status == STATUS.NOT_FOUND:
                db.Print(u'  %s' % cli_bracket(u'tag %s not present' % outtag),
                         allowSave=saveForNow)
                obj.tags[outtag] = O     # Object class; signifies missing
            else:
                db.Print(cli_bracket(u'error code %s attempting to read tag %s'
                                     % (error_code(status), outtag)),
                                        allowSave=saveForNowe)
#            db.Print(obj, allowPrint=False)


def execute_tags_command(objs, db, options):
    for obj in objs:
        description = describe_by_mode(obj)
        db.Print(u'Object %s:' % description)
        if obj.about:
            tags = db.get_object_tags_by_about(obj.about)
        else:
            tags = db.get_object_tags_by_id(obj.id)
        tags = sort_tags(tags)
        for tag in tags:
            fulltag = u'/%s' % tag
            outtag = u'/%s' % tag if db.unixStyle else tag
            if obj.about:
                status, (v, t) = db.get_tag_value_by_about(obj.about, fulltag,
                                                           getMime=True)
            else:
                status, (v, t) = db.get_tag_value_by_id(obj.id, fulltag,
                                                        getMime=True)

            if status == STATUS.OK:
                db.Print(formatted_tag_value(outtag, v, mime=t))
            elif status == STATUS.NOT_FOUND:
                db.Print(u'  %s' % cli_bracket(u'tag %s not present' % outtag))
            else:
                db.Print(cli_bracket(u'error code %s attempting to read tag %s'
                                     % (error_code(status), uttag)))


def execute_whoami_command(db):
    db.Print(Namespace(unicode(db.credentials.username)))


def execute_touch_command(db, args, options):
    for tag in args:
        fullpath = db.abs_tag_path(tag, inPref=True)
        if not db.tag_exists(fullpath):
            id = db.create_abstract_tag(fullpath,
                                        description=options.description)
                

def execute_mkns_command(db, args, options):
    for ns in args:
        fullpath = db.abs_tag_path(ns, inPref=True)
        if not db.ns_exists(fullpath):
            id = db.create_namespace(fullpath,
                                     description=options.description,
                                     verbose=options.verbose)


def execute_su_command(db, args):
    source =  get_credentials_file(username=args[0])
    dest = get_credentials_file()
    shutil.copyfile(source, dest)
    db = Fluidinfo(Credentials(filename=dest))
    username = db.credentials.username
    file = args[0].decode(DEFAULT_ENCODING)
    extra = u'' if args[0] == username else (u' (file %s)' % file)
    db.Print(u'Credentials set to user %s%s.' % (username, extra))


def check_abouttag_available():
    try:
        abouttag.amazon
    except:
        raise CommandError(AT_ERROR)


def execute_amazon_command(db, args):
    check_abouttag_available()
    print args[0]
    db.Print(abouttag.amazon.get_about_tag_for_item(args[0]))


def execute_abouttag_command(db, args):
    check_abouttag_available()
    db.Print(abouttag.generic.abouttag(*args))


def execute_normalize_command(db, args):
    check_abouttag_available()
    db.Print(':'.join(abouttag.nacolike.normalize(a, preserveAlpha=True)
             for a in args))


def FloatDateTime():
    """Returns datetime stamp in Miro's REV_DATETIME format as a float,
       e.g. 20110731.123456"""
    return float(time.strftime('%Y%m%d.%H%M%S', time.localtime()))


def execute_listseq_command(db, args, options):
    tag = db.abs_tag_path(args[0])[1:]
    fi = abouttag.fluiddb.FluidDB()
    nextTag = u'%s-next' % tag
    dateTag = u'%s-date' % tag
    numberTag = u'%s-number' % tag
    userAbout = fi.user(db.credentials.username)
    n = first = last = 0
    query = u'has %s' % tag

    if len(args) > 1:
        s = args[1]

        if re.match(INTEGER_RE, s):
            nItems = get_next_seq_number(db, nextTag, userAbout)
            n = int(s)
            if n < nItems:
                query += u' and %s > %d' % (numberTag, nItems - n - 1)
        m = re.match(INTEGER_RANGE_RE, s)
        if m:
            first, last = int(m.group(1)), int(m.group(2))
            query += u' and %s > %d and %s < %d' % (numberTag, first - 1,
                                                   numberTag, last + 1)

    keywords = args[2:] if (n or last) else args[1:]
    query = u' and '.join([query] + [u'%s matches "%s"'
                                     % (tag, word) for word in keywords])

    if options.verbose:
        db.Print(query)
    results = db.get_values_by_query(query, [tag, dateTag, numberTag])
    z = [(o.tags[numberTag], o) for o in results if numberTag in o.tags]
                                    
    z.sort()
    if options.long:
        for (n, o) in z:
            db.Print(u'Fluidinfo object with about="%s"' % o.get(numberTag))
            db.Print(unicode(o) + u'\n')
    else:
        for (i, o) in z:
            db.Print(u'%s: %s\n%s\n' % (format_number(o.get(numberTag)),
                                        o.get(tag),
                                        format_date(o.get(dateTag))))


class SequenceTags:
    def __init__(self, db, baseTag, zeroIfMissing=False):
        fi = abouttag.fluiddb.FluidDB()
        self.uTag = db.abs_tag_path(baseTag)
        self.fiTag = self.uTag[1:]
        self.nextTag = u'%s-next' % self.fiTag
        self.dateTag = u'%s-date' % self.fiTag
        self.numberTag = u'%s-number' % self.fiTag
        self.userAbout = fi.user(db.credentials.username)
        self.next = get_next_seq_number(db, self.nextTag, self.userAbout,
                                        noneIfNone=zeroIfMissing) or 0


def execute_mkseq_command(db, args, options):
    if len(args) > 3:
        raise(u'Form: mkseq sequence-name [plural-form [base-tag]]')
    name = args[0]
    plural = args[1] if len(args) > 1 else '%ss' % args[0]
    seq = SequenceTags(db, args[2] if len(args) > 2 else args[0],
                       zeroIfMissing=True)
    db.tag_object_by_about(seq.userAbout, u'/%s' % seq.nextTag, seq.next)
    create_alias(db, name, u'seq %s' % seq.uTag, options)
    create_alias(db, plural, u'listseq %s' % seq.uTag, options)
    if options.verbose:
        db.Print(u'Aliases created.\n'
                 u'  Use %s to add to the sequence.\n'
                 u'  Use %s to list items in the sequence.'
                 % (name, plural))
    db.Print(u'Next %s number: %d' % (name, seq.next))


def format_date(d):
    if d is None or not type(d) in (int, long, float):
        return u'(no date)'
    s = u'%.0f' % d
    if len(s) == 8:
        return u'%s-%s-%s' % (s[:4], s[4:6], s[6:])
    else:
        return s


def format_number(n):
    if n is None or not type(n) in (int, long, float):
        return u''
    return u'%d' % n


def get_next_seq_number(db, nextTag, userAbout, noneIfNone=False):
    s, n = db.get_tag_value_by_about(userAbout, u'/' + nextTag, inPref=True)
    if s != STATUS.OK:
        if s == STATUS.NOT_FOUND:
            if noneIfNone:
                return None
            else:
                raise CommandError(u'No previous item.\n  Use mkseq command '
                                   u'to create a sequence.')
                           
        else:
            #nasty error
            db.warning(u'Failed to read last item number from %s'
                        % (nextTag))
            db.error(u'Error code %s' % error_code(o))
    return n


def execute_seq_command(db, args, options):
    if len(args) != 2:
        raise CommandError('Usage: seq basetag value')

    tag = db.abs_tag_path(args[0])[1:]
    fi = abouttag.fluiddb.FluidDB()
    nextTag = u'%s-next' % tag
    dateTag = u'%s-date' % tag
    numberTag = u'%s-number' % tag
    userAbout = fi.user(db.credentials.username)

    content = args[1]
    n = get_next_seq_number(db, nextTag, userAbout)

    ds = FloatDateTime()
    o = O({tag: content, dateTag: ds, numberTag: n})
    itemAbout = unicode(n)
    db.write_tags(itemAbout, o)
    status = db.tag_object_by_about(userAbout, u'/' + nextTag, n + 1)
    assert status == 0
    o = db.read_tags(itemAbout, o)[0]
    db.Print(u'%s: %s\n%s\n' % (format_number(o.get(numberTag)),
                                o.get(tag),
                                format_date(o.get(dateTag))))


def execute_unalias_command(db, args, options):
    abstag = db.abs_tag_path(ALIAS_TAG)
    options.unixstylepaths=True
    if len(args) < 1:
        raise CommandError(u'Form unalias alias [alias2...]')
    for a in args:
        db.untag_object_by_about(args[0], abstag, inPref=False)
        db.cache.sync(db)        


def execute_alias_command(db, args, options):
    abstag = db.abs_tag_path(ALIAS_TAG, inPref=True, outPref=False)
    if len(args) < 2:
        aliases = db.cache.aliases(args[0] if len(args) == 1 else None)
        z = [(a.about, a) for a in aliases]
        z.sort()
        for (about, a) in z:
            db.Print(u'%s:' % unicode(a.about))
            db.Print(unicode(a) + u'\n')
    elif len(args) == 1:
        for o in db.cache.aliases(args[0]):
            db.Print(unicode(o) + u'\n')
    else:
        create_alias(db, args[0], u' '.join(args[1:]), options)


def create_alias(db, name, definition, options):
    abstag = db.abs_tag_path(ALIAS_TAG)
    options.unixstylepaths=True
    o = O({abstag[1:]: definition}, about=name)
    e = execute_tag_command([o], db, [u"%s='%s'" % (abstag, definition)],
                            options, u'tag')
    if e != 0:
        db.warning(u'Failed to create alias %s' % name)
        db.warning(u'Error code %s' % error_code(e))
        return
    db.cache.add(o)


def execute_showcache_command(db, args, options):
    db.Print(unicode(db.cache))


def execute_sync_command(db, args, options):
    db.cache.sync(db)


def execute_search_command(db, args, options):
    abouts, info, n = db.search(words=args, maxResults=options.pagesize,
                                page=options.page)
    db.Print(info)
    db.Print(u'\n'.join(u'%d: %s' % (n + i, a) for i, a in enumerate(abouts)))


def execute_init_command(db, args, options):
    path = u'.fish'
    fullpath = db.abs_tag_path(path, inPref=False)
    if not db.tag_exists(fullpath):
        db.create_namespace(fullpath, description='For use by Fish')
    options.unixstylepaths=True
    ls.execute_perms_command(db, [], [u'private', path], options,
                             credentials=None)


def describe_by_mode(o):
    """o is an object, which must have either about or id set
    """
    if o.about:
        return describe_by_about(o.about)
    elif o.id:
        return describe_by_id(o.id)
    raise ModeError(u'Bad Mode')


def describe_by_about(about):
    return u'with about="%s"' % about


def describe_by_id(id):
    return id


def form_tag_value_pairs(tags, options=None):
    fromFile = options and options.force    # overload -f
    pairs = []
    value = None
    for tag in tags:
        eqPos = tag.find('=')
        if eqPos == -1:
            if fromFile:
                if value is None:
                    value = Dummy()
                    value.value = sys.stdin.read()
                    value.mime = options.mime or 'text/plain'
            pairs.append(TagValue(tag, value))
        else:
            t = tag[:eqPos]
            if fromFile:
                v = get_typed_tag_value_from_file(tag[eqPos + 1:], options)
            else:
                v = get_typed_tag_value(tag[eqPos + 1:])
            pairs.append(TagValue(t, v))
    return pairs


#def fail(msg):
#    warning(msg)
#    raise Exception, msg


def cli_bracket(s):
    return u'(%s)' % s


def get_ids_or_fail(query, db, quiet=False):
    ids = db.query(query)
    if type(ids) in (int, long):
        if ids == STATUS.NOT_FOUND:
            return []
        else:
            raise CommandError(ids, 'Probably a bad query specification')
    else:
        if not quiet:
            db.Print(u'%s matched' % plural(len(ids), u'object'))
        return ids


def plural(n, s, pl=None, str=False, justTheWord=False):
    """Returns a string like '23 fields' or '1 field' where the
        number is n, the stem is s and the plural is either stem + 's'
        or stem + pl (if provided)."""
    smallints = [u'zero', u'one', u'two', u'three', u'four', u'five',
                 u'six', u'seven', u'eight', u'nine', u'ten']

    if pl == None:
        pl = u's'
    if str and n < 10 and n >= 0:
        strNum = smallints[n]
    else:
        strNum = int(n)
    if n == 1:
        if justTheWord:
            return s
        else:
            return (u'%s %s' % (strNum, s))
    else:
        if justTheWord:
            return u'%s%s' % (s, pl)
        else:
            return (u'%s %s%s' % (strNum, s, pl))


def parse_args(args=None):
    if args is None:
        args = [a.decode(DEFAULT_ENCODING) for a in sys.argv[1:]]
        if Credentials().unixStyle:
            usage = USAGE_FI if '-F' in args else USAGE_FISH
        else:
            usage = USAGE_FISH if '-U' in args else USAGE_FI
    else:
        usage = USAGE_FISH
    parser = OptionParser(usage=usage)
    general = OptionGroup(parser, 'General options')
    general.add_option('-a', '--about', action='append', default=[],
            help='used to specify objects by about tag')
    general.add_option('-i', '--id', action='append', default=[],
            help='used to specify objects by ID')
    general.add_option('-@', '--anon', action='store_true', default=False,
            help='use a (new) anonymous object fot tagging')
    general.add_option('-q', '--query', action='append', default=[],
            help='used to specify objects with a Fluidinfo query')
    general.add_option('-v', '--verbose', action='store_true', default=False,
            help='encourages Fish to report what it\'s doing (verbose mode)')
    general.add_option('-D', '--debug', action='store_true', default=False,
            help='enables debug mode (more output)')
    general.add_option('-T', '--timeout', type='float', default=HTTP_TIMEOUT,
            metavar='n', help='sets the HTTP timeout to n seconds')
    general.add_option('-U', '--unixstylepaths', action='store_true',
                       default=False,
            help='Forces unix-style paths for tags and namespaces.')
    general.add_option('-u', '--user', action='append', default=[],
            help='used to specify a different user (credentials file)')
    general.add_option('-F', '--fluidinfostylepaths', action='store_true',
                       default=False,
            help='Forces Fluidinfo--style paths for tags and namespaces.')
    general.add_option('-V', '--version', action='store_true',
                       default=False,
            help='Report version number.')
    general.add_option('-R', '--Recurse', action='store_true',
                       default=False,
            help='recursive (for ls).')
    general.add_option('-r', '--recurse', action='store_true',
                       default=False,
            help='recursive (for rm).')
    general.add_option('-f', '--force', action='store_true',
                       default=False,
            help='force (override pettifogging objections) or read from file.')
    general.add_option('-l', '--long', action='store_true',
                       default=False,
            help='long listing (for ls).')
    general.add_option('-L', '--longer', action='store_true',
                       default=False,
            help='longer listing (for ls).')
    general.add_option('-G', '--longest', action='store_true',
                       default=False,
            help='longest listing (for ls).')
    general.add_option('-g', '--group', action='store_true',
                       default=False,
            help='long listing with groups (for ls).')
    general.add_option('-d', '--namespace', action='store_true',
                       default=False,
            help='don\'t list namespace; just name of namespace.')
    general.add_option('-p', '--page', type='int', default=1,
                       help='page number.')
    general.add_option('-N', '--pagesize', type='int', default=100,
                       help='page size.')
    general.add_option('-n', '--ns', action='store_true',
                       default=False,
            help='don\'t list namespace; just name of namespace.')
    general.add_option('-m', '--description', action='store_true',
                       default=False,
            help='set description ("metadata") for tag/namespace.')
    general.add_option('-M', '--mime', action='append',
                       default=[],
            help='Specify MIME-type for value from file')
    general.add_option('-2', '--hightestverbosity', action='store_true',
                       default=False,
            help='don\'t list namespace; just name of namespace.')
    general.add_option('-X', '--extravals', action='append', default=[],
            help='extra values for a command.')
    general.add_option('-O', '--outform', action='append', default=[],
            help='Output format for results (json, python, text)')
    parser.add_option_group(general)

    other = OptionGroup(parser, 'Other flags')
    other.add_option('-s', '--sandbox', action='store_const',
                     dest='hostname', const=SANDBOX_PATH,
            help='use the sandbox at http://sandbox.fluidinfo.com')
    other.add_option('--hostname', default=FLUIDDB_PATH, dest='hostname',
            help=('use the specified host (which should start http:// or '
                   'https://; http:// will be added if it doesn\'t) default '
                   'is %default'))
    parser.add_option_group(other)

    options, args = parser.parse_args(args)
    if options.Recurse:
        options.recurse = options.Recurse

    if args == []:
        action = 'version' if options.version else 'help'
    else:
        action, args = args[0], args[1:]

    return action, args, options, parser

def toJSON(s):
    if type(s) in types.StringTypes:
        return s
    else:
        return s.toJSON()

def toOutputString(s):
    if type(s) in types.StringTypes:
        return s
    else:
        return unicode(s)

def execute_command_line(action, args, options, parser, user=None, pwd=None,
                         unixPaths=None, docbase=None, saveOut=False,
                         rawargs=None, cache=None):
    credentials = (Credentials(user or options.user[0], pwd)
                   if (user or options.user) else None)
    unixPaths = (path_style(options) if path_style(options) is not None
                                     else unixPaths)
    db = ls.ExtendedFluidinfo(host=options.hostname, credentials=credentials,
                              debug=options.debug, unixStylePaths=unixPaths,
                              saveOut=saveOut, cache=cache)
    quiet = (action == 'get')

    command_list = [
        'help',
        'version',
        'commands',
        'tag',
        'untag',
        'show',
        'get',
        'tags',
        'count',
        'ls',
        'rm',
        'perms',
        'pwd',
        'pwn',
        'rmdir',
        'rmns',
        'touch',
        'mkns',
        'mkdir',
        'amazon',
        'test',
        'testcli',
        'testdb',
        'testapi',
        'whoami',
        'su',
        'abouttag',
        'about',
        'normalize',
        'seq',
        'listseq',
        'mkseq',
        'alias',
        'unalias',
        'init',
        'search',
        'showcache',
        'sync',
        'quit',
        'exit',
    ]
    command_list.sort()

    # Expand aliases
    alias = db.cache.get_alias(action)
    if alias:
        words = cline.CScanSplit(alias, ' \t', quotes='"\'').words
        loc = rawargs.index(action)
        args = words + rawargs[:loc] + rawargs[loc + 1:]
        action, args, options, parser = parse_args(args)
        if options.verbose or options.debug:
            db.Print('Expanded to %s %s' % (action, u'   '.join(args)))
            db.Print('  with Query %s' % (options.query))

    ids_from_queries = chain(*imap(lambda q: get_ids_or_fail(q, db,
                                                             quiet=quiet),
        options.query))
    ids = chain(options.id, ids_from_queries)
    if options.anon:
        o = db.create_object()
        if type(o) == int:
           raise CommandError(u'Error Status: %d' % o) 
        else:
            ids = [o.id]
    objs = [O(about=a) for a in options.about] + [O(id=id) for id in ids]

    if action == 'version' or options.version:
        db.Print('fish %s' % version())
        if action == 'version':
            return
    
    try:
        if action == 'help':
            if args and args[0] in command_list:
                base = docbase or sys.path[0]
                path = os.path.join(base, 'doc/build/text/%s.txt' % args[0])
                f = open(path)
                s = f.read()
                db.Print(s.decode('UTF-8'))
                f.close()
            else:
                db.Print(USAGE_FISH if db.unixStyle else USAGE_FI)
        elif action == 'commands':
            db.Print(' '.join(command_list))
        elif action not in command_list:
            db.Print('Unrecognized command %s' % action)        
        elif (action.lower() not in ARGLESS_COMMANDS
              and not args and not options.anon):
            db.Print('Too few arguments for action %s' % action)
        elif action == 'count':
            db.Print('Total: %s' % (flags.Plural(len(objs), 'object')))
        elif action in ('tags', 'tag', 'untag', 'show', 'get'):
            if not (options.about or options.query or options.id
                    or options.anon):
                if args:
                    spec = args[0]
                    if re.match(UUID_RE, spec):
                        objs = [O(id=spec)]
                        options.id = [spec]
                    else:
                        objs = [O(about=spec)]
                        options.about = [spec]
                    args = args[1:]
                else:
                    db.Print('You must use -q or specify an about tag or'
                             ' object ID for the %s command.' % action)
            if action == 'tags':
                execute_tags_command(objs, db, options)
            elif objs:
                tags = args
                if len(tags) == 0 and action != 'count':
                    db.nothing_to_do('No tags specified')
                actions = {
                    'tag': execute_tag_command,
                    'untag': execute_untag_command,
                    'show': execute_show_command,
                    'get': execute_show_command,
                }
                command = actions[action]
                command(objs, db, args, options, action)
        elif action == 'ls':
            ls.execute_ls_command(db, objs, args, options, credentials,
                                  unixPaths)
        elif action == 'rm':
            ls.execute_rm_command(db, objs, args, options, credentials,
                                  unixPaths)
        elif action in ('rmdir', 'rmns'):
            raise CommandError(u'Use rm to remove namespaces as well as tags')
        elif action == 'chmod':
            ls.execute_chmod_command(db, objs, args, options, credentials,
                                     unixPaths)
        elif action == 'perms':
            ls.execute_perms_command(db, objs, args, options, credentials,
                                     unixPaths)
        elif action in ('pwd', 'pwn', 'whoami'):
            execute_whoami_command(db)
        elif action == 'touch':
            execute_touch_command(db, args, options)
        elif action in ('mkns', 'mkdir'):
            execute_mkns_command(db, args, options)
        elif action == 'su':
            execute_su_command(db, args)
        elif action == 'amazon':
            execute_amazon_command(db, args)
        elif action in ('abouttag', 'about'):
            execute_abouttag_command(db, args)
        elif action == 'normalize':
            execute_normalize_command(db, args)
        elif action == 'seq':
            execute_seq_command(db, args, options)
        elif action == 'listseq':
            execute_listseq_command(db, args, options)
        elif action == 'mkseq':
            execute_mkseq_command(db, args, options)
        elif action == 'alias':
            execute_alias_command(db, args, options)
        elif action == 'unalias':
            execute_unalias_command(db, args, options)
        elif action == 'showcache':
            execute_showcache_command(db, args, options)
        elif action == 'sync':
            execute_sync_command(db, args, options)
        elif action == 'init':
            execute_init_command(db, args, options)
        elif action == 'search':
            execute_search_command(db, args, options)
        elif action in ('quit', 'exit'):
            pass
        else:
            db.Print('Unrecognized command %s' % action)
    except Exception, e:
        if options.debug:
            db.Print(unicode(traceback.format_exc()))
        db.Print(u'Fish failure:\n  %s' % unicode(e))
    if db.saveOutput:
        if db.saveOutput == u'python':
            return db.buffer
        elif db.saveOutput == u'json':
            s =  json.dumps({u'result': [toJSON(s) for s in db.buffer]})
            return json.dumps({u'result': [toJSON(s) for s in db.buffer]})
        else:
            return (u'\n'.join([toOutputString(b) for b in db.buffer])
                    if saveOut else None)
