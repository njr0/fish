# -*- coding: utf-8 -*-
#
# cli.py
#
# Copyright (c) Nicholas J. Radcliffe 2009-2011 and other authors specified
#               in the AUTHOR
# Licence terms in LICENCE.

import sys
import types
from optparse import OptionParser, OptionGroup
from itertools import chain, imap
from fdbcore import (
    FluidDB,
    O,
    get_typed_tag_value,
    toStr,
    STATUS,
    DADGAD_ID,
    HTTP_TIMEOUT,
    SANDBOX_PATH,
    FLUIDDB_PATH,
)


HTTP_METHODS = ['GET', 'PUT', 'POST', 'DELETE', 'HEAD']

USAGE = """Run Tests:
   fdb test            (runs all tests)
   fdb testcli         (tests command line interface only)
   fdb testdb          (tests core FluidDB interface only)
   fdb testutil        (runs tests not requiring FluidDB access)

 Tag objects:
   fdb tag -a 'DADGAD' tuning rating=10
   fdb tag -i %s /njr/tuning /njr/rating=10
   fdb tag -q 'about = "DADGAD"' tuning rating=10

 Untag objects:
   fdb untag -a 'DADGAD' /njr/tuning rating
   fdb untag -i %s
   fdb untag -q 'about = "DADGAD"' tuning rating

 Fetch objects and show tags
   fdb show -a 'DADGAD' /njr/tuning /njr/rating
   fdb show -i %s tuning rating
   fdb show -q 'about = "DADGAD"' tuning rating

 Count objects matching query:
   fdb count -q 'has fluiddb/users/username'

 Get tags on objects and their values:
   fdb tags -a 'DADGAD'
   fdb tags -i %s

 Raw HTTP GET:
   fdb get /tags/njr/google
   fdb get /permissions/tags/njr/rating action=delete
   (use POST/PUT/DELETE/HEAD at your peril; currently untested.)
""" % (DADGAD_ID, DADGAD_ID, DADGAD_ID, DADGAD_ID)


class ModeError(Exception):
    pass


class TooFewArgsForHTTPError(Exception):
    pass


class UnrecognizedHTTPMethodError(Exception):
    pass


class TagValue:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def __str__(self):
        return ('Tag "%s", value "%s" of type %s'
                     % (self.name, toStr(self.value), toStr(type(self.value))))


def execute_tag_command(objs, db, tags, options):
    tags = form_tag_value_pairs(tags)
    actions = {
            'id': db.tag_object_by_id,
            'about': db.tag_object_by_about,
            }
    for obj in objs:
        description = describe_by_mode(obj.specifier, obj.mode)
        for tag in tags:
            o = actions[obj.mode](obj.specifier, tag.name, tag.value)
            if o == 0:
                if options.verbose:
                    print('Tagged object %s with %s'
                            % (description,
                               formatted_tag_value(tag.name, tag.value)))
            else:
                warning('Failed to tag object %s with %s'
                            % (description, tag.name))
                warning('Error code %d' % o)


def execute_untag_command(objs, db, tags, options):
    actions = {
        'id': db.untag_object_by_id,
        'about': db.untag_object_by_about,
    }
    for obj in objs:
        description = describe_by_mode(obj.specifier, obj.mode)
        for tag in tags:
            o = actions[obj.mode](obj.specifier, tag)
            if o == 0:
                if options.verbose:
                    print('Removed tag %s from object %s\n'
                          % (tag, description))
            else:
                warning('Failed to remove tag %s from object %s'
                        % (tag, description))
                warning('Error code %d' % o)


def execute_show_command(objs, db, tags, options):
    actions = {
        'id': db.get_tag_value_by_id,
        'about': db.get_tag_value_by_about,
    }
    for obj in objs:
        description = describe_by_mode(obj.specifier, obj.mode)
        print 'Object %s:' % description

        for tag in tags:
            fulltag = db.encode(db.abs_tag_path(tag))
            if tag == '/id':
                if obj.mode == 'about':
                    o = db.query('fluiddb/about = "%s"' % obj.specifier)
                    if type(o) == types.IntType:  # error
                        status, v = o, None
                    else:
                        status, v = STATUS.OK, o[0]
                else:
                    status, v = STATUS.OK, obj.specifier
            else:
                status, v = actions[obj.mode](obj.specifier, tag)

            if status == STATUS.OK:
                print '  %s' % formatted_tag_value(fulltag, v)
            elif status == STATUS.NOT_FOUND:
                print '  %s' % cli_bracket('tag %s not present' % fulltag)
            else:
                print cli_bracket('error code %d getting tag %s' % (status,
                                                                    fulltag))


def execute_tags_command(objs, db, options):
    for obj in objs:
        description = describe_by_mode(obj.specifier, obj.mode)
        print 'Object %s:' % description
        id = (db.create_object(obj.specifier).id if obj.mode == 'about'
              else obj.specifier)
        for tag in db.get_object_tags_by_id(id):
            fulltag = '/%s' % tag
            status, v = db.get_tag_value_by_id(id, fulltag)

            if status == STATUS.OK:
                print '  %s' % formatted_tag_value(fulltag, v)
            elif status == STATUS.NOT_FOUND:
                print '  %s' % cli_bracket('tag %s not present' % fulltag)
            else:
                print cli_bracket('error code %d getting tag %s' % (status,
                                                                    fulltag))


def execute_http_request(action, args, db, options):
    """Executes a raw HTTP command (GET, PUT, POST, DELETE or HEAD)
       as specified on the command line."""
    method = action.upper()
    if method not in HTTP_METHODS:
        raise UnrecognizedHTTPMethodError('Only supported HTTP methods are'
                '%s and %s' % (' '.join(HTTP_METHODS[:-1], HTTP_METHODS[-1])))

    if len(args) == 0:
        raise TooFewArgsForHTTPError('HTTP command %s requires a URI' % method)
    uri = args[0]
    tags = form_tag_value_pairs(args[1:])
    if method == 'PUT':
        body = {tags[0].tag: tags[0].value}
        tags = tags[1:]
    else:
        body = None
    hash = {}
    for pair in tags:
        hash[pair.name] = pair.value
    status, result = db.call(method, uri, body, hash)
    print 'Status: %d' % status
    print 'Result: %s' % toStr(result)


def execute_command_line(action, args, options, parser):
    db = FluidDB(host=options.hostname, debug=options.debug)

    ids_from_queries = chain(*imap(lambda q: get_ids_or_fail(q, db),
        options.query))
    ids = chain(options.id, ids_from_queries)

    objs = [O({'mode': 'about', 'specifier': a}) for a in options.about] + \
            [O({'mode': 'id', 'specifier': id}) for id in ids]

    if action == 'help':
        print USAGE
        sys.exit(0)
    elif (action.upper() not in HTTP_METHODS + ['COUNT', 'TAGS'] and not args):
        parser.error('Too few arguments for action %s' % action)
    elif action == 'count':
        print "Total: %d objects" % (len(objs))
    elif action == 'tags':
        execute_tags_command(objs, db, options)
    elif action in ('tag', 'untag', 'show'):
        if not (options.about or options.query or options.id):
            parser.error('You must use -q, -a or -i with %s' % action)
        tags = args
        if len(tags) == 0 and action != 'count':
            nothing_to_do()
        actions = {
            'tag': execute_tag_command,
            'untag': execute_untag_command,
            'show': execute_show_command,
        }
        command = actions[action]

        command(objs, db, tags, options)
    elif action in ['get', 'put', 'post', 'delete']:
        execute_http_request(action, args, db, options)
    else:
        parser.error('Unrecognized command %s' % action)


def describe_by_mode(specifier, mode):
    """mode can be a string (about, id or query) or a flags object
        with flags.about, flags.query and flags.id"""
    if mode == 'about':
        return describe_by_about(specifier)
    elif mode == 'id':
        return describe_by_id(specifier)
    elif mode == 'query':
        return describe_by_id(specifier)
    raise ModeError('Bad Mode')


def describe_by_about(specifier):
    return 'with about="%s"' % specifier


def describe_by_id(specifier):
    return specifier


def formatted_tag_value(tag, value):
    if value == None:
        return tag
    elif type(value) in types.StringTypes:
        return '%s = "%s"' % (tag, value)
    else:
        return '%s = %s' % (tag, toStr(value))


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


def warning(msg):
    sys.stderr.write('%s\n' % msg)


def fail(msg):
    warning(msg)
    sys.exit(1)


def nothing_to_do():
    print 'Nothing to do.'
    sys.exit(0)


def cli_bracket(s):
    return '(%s)' % s


def get_ids_or_fail(query, db):
    ids = db.query(query)
    if type(ids) == types.IntType:
        fail('Query failed')
    else:   # list of ids
        print '%s matched' % plural(len(ids), 'object')
        return ids


def plural(n, s, pl=None, str=False, justTheWord=False):
    """Returns a string like '23 fields' or '1 field' where the
        number is n, the stem is s and the plural is either stem + 's'
        or stem + pl (if provided)."""
    smallints = ['zero', 'one', 'two', 'three', 'four', 'five',
                         'six', 'seven', 'eight', 'nine', 'ten']

    if pl == None:
        pl = 's'
    if str and n < 10 and n >= 0:
        strNum = smallints[n]
    else:
        strNum = int(n)
    if n == 1:
        if justTheWord:
            return s
        else:
            return ('%s %s' % (strNum, s))
    else:
        if justTheWord:
            return '%s%s' % (s, pl)
        else:
            return ('%s %s%s' % (strNum, s, pl))


def parse_args(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = OptionParser(usage=USAGE)
    general = OptionGroup(parser, "General options")
    general.add_option("-a", "--about", action="append", default=[],
            help="used to specify objects by about tag")
    general.add_option("-i", "--id", action="append", default=[],
            help="used to specify objects by ID")
    general.add_option("-q", "--query", action="append", default=[],
            help="used to specify objects with a FluidDB query")
    general.add_option("-v", "--verbose", action="store_true", default=False,
            help="encourages FDB to report what it's doing (verbose mode)")
    general.add_option("-D", "--debug", action="store_true", default=False,
            help="enables debug mode (more output)")
    general.add_option("-T", "--timeout", type="float", default=HTTP_TIMEOUT,
            metavar="n", help="sets the HTTP timeout to n seconds")
    parser.add_option_group(general)

    other = OptionGroup(parser, "Other flags")
    other.add_option("-s", "--sandbox", action="store_const", dest="hostname",
            const=SANDBOX_PATH,
            help="use the sandbox at http://sandbox.fluidinfo.com")
    other.add_option("--hostname", default=FLUIDDB_PATH, dest="hostname",
            help="use the specified host (which should start http:// or "\
                    "https://; http:// will be added if it doesn't) default "\
                    "is %default")
    parser.add_option_group(other)

    options, args = parser.parse_args(args)

    if args == []:
        action = 'help'
    else:
        action, args = args[0], args[1:]

    return action, args, options, parser


