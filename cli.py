# -*- coding: utf-8 -*-
#
# cli.py
#
# Copyright (c) Nicholas J. Radcliffe 2009-2011 and other authors specified
#               in the AUTHOR
# Licence terms in LICENCE.

import os
import shutil
import sys
import time
import types
import traceback
from optparse import OptionParser, OptionGroup
from itertools import chain, imap
from fishlib import (
    FluidDB,
    O,
    Credentials,
    get_credentials_file,
    get_typed_tag_value,
    path_style,
    toStr,
    version,
    DEFAULT_ENCODING,
    STATUS,
    DADGAD_ID,
    PARIS_ID,
    HTTP_TIMEOUT,
    SANDBOX_PATH,
    FLUIDDB_PATH,
    json,
    TagValue,
    Namespace,
)
import ls
import flags
try:
    import abouttag.amazon
    import abouttag.generic
    import abouttag.nacolike
except ImportError:
    pass


HTTP_METHODS = ['GET', 'PUT', 'POST', 'DELETE', 'HEAD']

ARGLESS_COMMANDS = ['COUNT', 'TAGS', 'LS', 'PWD', 'PWN', 'WHOAMI', 'QUIT',
                    'EXIT']

AT_ERROR = (u'You need the abouttag library to use the abouttag command.\n'
            u'This is available from http://github.com/njr0/abouttag.')

USAGE = u'''

For help with a specific command, type help followed by the command name.
For a list of commands, type commands.

 Tag objects:
   tag -a 'Paris' /alice/visited /alice/rating=10
   tag -i %s /bert/visited /bert/rating=10
   tag -q 'about = "Paris"' /alice/visited /alice/rating=10
   [On windows: tag -q "about = "Paris""" /alice/visited /alice/rating=10

 Untag objects:
   untag -a 'Paris' /bert/visited /alice/rating
   untag -i %s
   untag -q 'about = "Paris"' /alice/visited /alice/rating

 Fetch objects and show tags
   show -a 'Paris' /bert/visited /bert/rating
   show -i %s /alice/visited /alice/rating
   show -q 'about = "Paris"' /alice/visited /alice/rating

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
   testdb              tests core FluidDB interface only
   testutil            runs tests not requiring FluidDB access


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
    tags = form_tag_value_pairs(tags)
    actions = {
        u'id': db.tag_object_by_id,
        u'about': db.tag_object_by_about,
    }
    for obj in objs:
        description = describe_by_mode(obj.specifier, obj.mode)
        for tag in tags:
            o = actions[obj.mode](obj.specifier, tag.name, tag.value,
                                  inPref=True)
            if o == 0:
                if options.verbose:
                    db.Print(u'Tagged object %s with %s'
                             % (description,
                                formatted_tag_value(tag.name, tag.value,
                                                    prefix=u'')))
            else:
                db.warning(u'Failed to tag object %s with %s'
                        % (description, tag.name))
                db.warning(u'Error code %s' % error_code(o))


def execute_untag_command(objs, db, tags, options, action):
    actions = {
        'id': db.untag_object_by_id,
        'about': db.untag_object_by_about,
    }
    for obj in objs:
        description = describe_by_mode(obj.specifier, obj.mode)
        for tag in tags:
            o = actions[obj.mode](obj.specifier, tag, inPref=True)
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


def execute_show_command(objs, db, tags, options, action):
    actions = {
        u'id': db.get_tag_value_by_id,
        u'about': db.get_tag_value_by_about,
    }
    terse = (action == u'get')
    for obj in objs:
        description = describe_by_mode(obj.specifier, obj.mode)
        if not terse:
            db.Print(u'Object %s:' % description)
#            sort_tags(tags)
        for tag in tags:
            fulltag = db.abs_tag_path(tag, inPref=True)
            outtag = db.abs_tag_path(tag, inPref=True, outPref=True)
            if tag == u'/id':
                if obj.mode == u'about':
                    o = db.query(u'fluiddb/about = "%s"' % obj.specifier)
                    if type(o) == types.IntType:  # error
                        status, v = o, None
                    else:
                        status, v = STATUS.OK, o[0]
                else:
                    status, v = STATUS.OK, obj.specifier
            else:
                status, v = actions[obj.mode](obj.specifier, tag, inPref=True)

            saveForNow = True   # while getting ready to move to objects
            if status == STATUS.OK:
                db.Print(formatted_tag_value(outtag, v, terse),
                         allowSave=saveForNow)
                obj.__dict__[outtag] = v
            elif status == STATUS.NOT_FOUND:
                db.Print(u'  %s' % cli_bracket(u'tag %s not present' % outtag),
                         allowSave=saveForNow)
                obj.__dict__[outtag] = O     # Object class; signifies missing
            else:
                db.Print(cli_bracket(u'error code %s attempting to read tag %s'
                                     % (error_code(status), outtag)),
                                     allowSave=saveForNowe)
#            db.Print(obj, allowPrint=False)


def execute_tags_command(objs, db, options):
    for obj in objs:
        description = describe_by_mode(obj.specifier, obj.mode)
        db.Print(u'Object %s:' % description)
        id = (db.create_object(obj.specifier).id if obj.mode == u'about'
              else obj.specifier)
        tags = db.get_object_tags_by_id(id)
        sort_tags(tags)
        for tag in tags:
            fulltag = u'/%s' % tag
            outtag = u'/%s' % tag if db.unixStyle else tag
            status, v = db.get_tag_value_by_id(id, fulltag)

            if status == STATUS.OK:
                db.Print(formatted_tag_value(outtag, v))
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
    db = FluidDB(Credentials(filename=dest))
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


def execute_sequence_command(db, args):
    tag, content = args[0], args[1]
    fi = abouttag.fluidinfo.FluidDB()
    nextTag = u'%s-next' % tag
    dateTag = u'%s-date' % tag
    numberTag = u'%s-number' % tag
    userAbout = fi.user(db.user)
    s, n = db.get_tag_value_by_about(userAbout, nextTag, inPref=True)
    if s != STATUS.OK:
        if s == STATUS.NOT_FOUND:
            db.warning(u'No previous item.\n Please use:\n'
                       u'  touch %s %s %s %s\n'
                       u'and then set permissions as appropriate.'
                       % (tag, tag, tag, tag))
        else:
            #nasty error
            db.warning(u'Failed to read last item number from %s'
                        % (nextTag))
            db.warning(u'Error code %s' % error_code(o))

    ds = FloatDateTime()
    o = O(((u'/about', unicode(n)), (tag, content), (dateTag, ds),
           (numberTag, n)))
    status = db.write_tags(o)
    status = db.tag_object_by_about(userAbout, nextTag, n + 1)
    status = db.read_tags(o)
    # Check Statuses and show tags.      
    # In fact, finish with a seq thought 1 command??

    # nextInSeq = get -a 'user object' tagname-next
    # if not defined: 0 : create tags, make private if start private
    # datestamp
    # tag -a unicode(nextInSeq) tagname=value tagname=date tagname-number=nextInSueq
    # tag -a 'user obkect' tagname-next+= 1
    # get -a 
    
    
    pass


def execute_http_request(action, args, db, options):
    """Executes a raw HTTP command (GET, PUT, POST, DELETE or HEAD)
       as specified on the command line."""
    method = action.upper()
    if method not in HTTP_METHODS:
        raise UnrecognizedHTTPMethodError(u'Only supported HTTP methods are'
                u'%s and %s' % (' '.join(HTTP_METHODS[:-1], HTTP_METHODS[-1])))

    if len(args) == 0:
        raise TooFewArgsForHTTPError(u'HTTP command %s requires a URI'
                                     % method)
    uri = args[0]
    tags = form_tag_value_pairs(args[1:])
    if method == u'PUT':
        body = {tags[0].tag: tags[0].value}
        tags = tags[1:]
    else:
        body = None
    hash = {}
    for pair in tags:
        hash[pair.name] = pair.value
    status, result = db.call(method, uri, body, hash)
    db.Print(u'Status: %d' % status)
    db.Print(u'Result: %s' % toStr(result))


def describe_by_mode(specifier, mode):
    """mode can be a string (about, id or query) or a flags object
        with flags.about, flags.query and flags.id"""
    if mode == u'about':
        return describe_by_about(specifier)
    elif mode == u'id':
        return describe_by_id(specifier)
    elif mode == u'query':
        return describe_by_id(specifier)
    raise ModeError(u'Bad Mode')


def describe_by_about(specifier):
    return u'with about="%s"' % specifier


def describe_by_id(specifier):
    return specifier


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


def form_tag_value_pairs(tags):
    pairs = []
    for tag in tags:
        eqPos = tag.find('=')
        if eqPos == -1:
            pairs.append(TagValue(tag, None))
        else:
            t = tag[:eqPos]
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
        usage = USAGE_FI
    parser = OptionParser(usage=usage)
    general = OptionGroup(parser, 'General options')
    general.add_option('-a', '--about', action='append', default=[],
            help='used to specify objects by about tag')
    general.add_option('-i', '--id', action='append', default=[],
            help='used to specify objects by ID')
    general.add_option('-q', '--query', action='append', default=[],
            help='used to specify objects with a FluidDB query')
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
            help='force (override pettifogging objections).')
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
    general.add_option('-P', '--policy', action='store_true',
                       default=False,
            help='policy (i.e. default permission).')
    general.add_option('-n', '--ns', action='store_true',
                       default=False,
            help='don\'t list namespace; just name of namespace.')
    general.add_option('-m', '--description', action='store_true',
                       default=False,
            help='set description ("metadata") for tag/namespace.')
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
                         unixPaths=None, docbase=None, saveOut=False):
    credentials = (Credentials(user or options.user[0], pwd)
                   if (user or options.user) else None)
    unixPaths = (path_style(options) if path_style(options) is not None
                                     else unixPaths)
    db = ls.ExtendedFluidDB(host=options.hostname, credentials=credentials,
                            debug=options.debug, unixStylePaths=unixPaths,
                            saveOut=saveOut)
    quiet = (action == 'get')
    ids_from_queries = chain(*imap(lambda q: get_ids_or_fail(q, db,
                                                             quiet=quiet),
        options.query))
    ids = chain(options.id, ids_from_queries)

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
        'quit',
        'exit',
    ]
    command_list.sort()

    objs = [O({'mode': 'about', 'specifier': a}) for a in options.about] + \
            [O({'mode': 'id', 'specifier': id}) for id in ids]

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
        elif (action.upper() not in HTTP_METHODS + ARGLESS_COMMANDS
              and not args):
            db.Print('Too few arguments for action %s' % action)
        elif action == 'count':
            db.Print('Total: %s' % (flags.Plural(len(objs), 'object')))
        elif action == 'tags':
            execute_tags_command(objs, db, options)
        elif action in ('tag', 'untag', 'show', 'get'):
            if not (options.about or options.query or options.id):
                db.Print('You must use -q, -a or -i with %s' % action)
            else:
                tags = args
                if len(tags) == 0 and action != 'count':
                    db.nothing_to_do()
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
#        elif action in ('get', 'put', 'post', 'delete'):
#            execute_http_request(action, args, db, options)
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



