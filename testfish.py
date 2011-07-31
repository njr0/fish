# -*- coding: utf-8 -*-
#
# testfish.py
#
# Copyright (c) Nicholas J. Radcliffe 2009-2011 and other authors specified
#               in the AUTHOR
# Licence terms in LICENCE.
#
import unittest
from fishlib import *
from cli import *

class TestFluidDB(unittest.TestCase):

    def setUp(self):
        self.db = FluidDB()
        self.user = self.db.credentials.username   # UNICODE
        self.db.set_connection_from_global()
        self.db.set_debug_timeout(5.0)
        self.dadgadID = id(u'DADGAD', self.db.host)

    def testCreateObject(self):
        db = self.db
        o = db.create_object(u'DADGAD')
        self.assertEqual(o.id, self.dadgadID)
        self.assertEqual(o.URI, object_uri(self.dadgadID))

    def testCreateObjectNoAbout(self):
        db = self.db
        o = db.create_object()
        self.assertEqual(type(o) not in (int, long), True)

    def testCreateObjectFail(self):
        bad = Credentials(u'doesnotexist', u'certainlywiththispassword')
        db = FluidDB(bad)
        o = db.create_object(u'DADGAD')
        self.assertEqual(o, STATUS.UNAUTHORIZED)

    def testCreateTag(self):
        db = self.db
        o = db.delete_abstract_tag(u'test-fish/testrating')
        # doesn't really matter if this works or not

        o = db.create_abstract_tag(u'test-fish/testrating',
                        u"%s's test-fish/testrating (0-10; more is better)"
                        % self.user)
        self.assertEqual(type(o.id) in types.StringTypes, True)
        self.assertEqual(unicode(urllib.unquote(o.URI.encode('UTF-8')),
                                 'UTF-8'),
                         tag_uri(db.credentials.username,
                         u'test-fish/testrating'))
                                                

    def testTags(self):
        db = self.db
        user = db.credentials.username
        o = db.tag_object_by_about(u'αβγδε', u'test-fish/ζηθικ', u'φχψω')
        o = db.tag_object_by_about(u'αβγδε', u'test-fish/λμνξο', u'πρστυ')

        # check tags function OK
        tags = db.get_object_tags_by_about(u'αβγδε')
        self.assertEqual(u'%s/test-fish/ζηθικ' % user in tags, True)
        self.assertEqual(u'%s/test-fish/λμνξο' % user in tags, True)

        # check tag values are OK
        status, v = db.get_tag_value_by_about(u'αβγδε', u'test-fish/ζηθικ')
        self.assertEqual(v, u'φχψω')

        # clean up
        o = db.untag_object_by_about(u'αβγδε', u'test-fish/ζηθικ')
        o = db.untag_object_by_about(u'αβγδε', u'test-fish/λμνξο')

    def testValuesAPISetGet(self):
        db = self.db
        user = db.credentials.username
        pairs = {
            u'test-fish/αβγδε': u'αβγδε',
            u'test-fish/ζηθικ': 1,
            u'test-fish/φχψω': 2.5,
            u'test-fish/λμνξο': True,
            u'test-fish/πρστυ': None,
            u'test-fish/testrating': u'αβγδε',
            u'test-fish/testrating2': 1,
            u'test-fish/testrating3': 2.5,
            u'test-fish/testrating4': True,
            u'test-fish/testrating5': None,
        }
        tagsToSet = {}
#        object_about = u'ΔΑΔΓΑΔ'
        object_about = u'DADGAD'
        for tag in pairs:
            db.tag_object_by_about(object_about, tag, None)   # make sure 
                                                              # tag exists
            tagsToSet[db.abs_tag_path(tag)[1:]] = pairs[tag]

        query = u'fluiddb/about = "%s"' % object_about
        tag_by_query(db, query, tagsToSet)
        objects = get_values_by_query(db, query, tagsToSet)
        self.assertEqual(len(objects), 1)
        o = objects[0]
        for key in tagsToSet:
            self.assertEqual(o.__dict__[key], tagsToSet[key])
            db.delete_abstract_tag(u'/' + tag)

    def testSetTagByID(self):
        db = self.db
        user = db.credentials.username
        o = db.delete_abstract_tag(u'test-fish/testrating')
        o = db.create_abstract_tag(u'test-fish/testrating',
               u"%s's test-fish/testrating (0-10; more is better)" % self.user)
        o = db.tag_object_by_id(self.dadgadID,
                                u'/%s/test-fish/testrating' % user, 5)
        self.assertEqual(o, 0)
        _status, v = db.get_tag_value_by_id(self.dadgadID,
                                            u'test-fish/testrating')
        self.assertEqual(v, 5)

    def testSetTagByAbout(self):
        db = self.db
        user = db.credentials.username
        o = db.delete_abstract_tag(u'test-fish/testrating')
        o = db.tag_object_by_about(u'http://dadgad.com',
                                   u'/%s/test-fish/testrating' % user, u'five')
        o = db.tag_object_by_about('DAD +GAD',
                                   u'/%s/test-fish/testrating' % user, u'five')
        self.assertEqual(o, 0)
        _status, v = db.get_tag_value_by_about(u'http://dadgad.com',
                                               u'test-fish/testrating')
        _status, v = db.get_tag_value_by_about(u'DAD +GAD',
                                               u'test-fish/testrating')

        self.assertEqual(v, u'five')

    def testDeleteNonExistentTag(self):
        db = self.db
        o = db.delete_abstract_tag(u'test-fish/testrating')
        o = db.delete_abstract_tag(u'test-fish/testrating')  # definitely
                                                             # doesn't exist

    def testSetNonExistentTag(self):
        db = self.db
        o = db.delete_abstract_tag(u'test-fish/testrating')
        o = db.tag_object_by_id(self.dadgadID, u'test-fish/testrating', 5)
        self.assertEqual(o, 0)
        status, v = db.get_tag_value_by_id(self.dadgadID,
                                           u'test-fish/testrating')
        self.assertEqual(v, 5)

    def testUntagObjectByID(self):
        db = self.db

        # First tag something
        o = db.tag_object_by_id(self.dadgadID, u'test-fish/testrating', 5)
        self.assertEqual(o, 0)

        # Now untag it
        error = db.untag_object_by_id(self.dadgadID, u'test-fish/testrating')
        self.assertEqual(error, 0)
        status, v = db.get_tag_value_by_id(self.dadgadID,
                                           u'test-fish/testrating')
        self.assertEqual(status, STATUS.NOT_FOUND)

        # Now untag it again (should be OK)
        error = db.untag_object_by_id(self.dadgadID, u'test-fish/testrating')
        self.assertEqual(error, 0)

        # And again, but this time asking for error if untagged
        error = db.untag_object_by_id(self.dadgadID, u'test-fish/testrating',
                                      False)
        self.assertEqual(error, 0)  # The API has changed so that in fact
                                    # a 204 (NO CONTENT) is always returned,
                                    # so this test and the flag are now
                                    # less meaningful.
                                    # For now, just updated to be consistent
                                    # with the latest API.
                                    

    def testUntagObjectByAbout(self):
        db = self.db

        # First tag something
        o = db.tag_object_by_id(self.dadgadID, u'test-fish/testrating', 5)
        self.assertEqual(o, 0)

        # Now untag it
        error = db.untag_object_by_about(u'DADGAD', u'test-fish/testrating')
        self.assertEqual(error, 0)
        status, v = db.get_tag_value_by_about(u'DADGAD',
                                              u'test-fish/testrating')
        self.assertEqual(status, STATUS.NOT_FOUND)

    def testAddValuelessTag(self):
        db = self.db
        o = db.delete_abstract_tag(u'test-fish/testconvtag')
        o = db.create_abstract_tag(u'test-fish/testconvtag',
                                   u"a conventional (valueless) tag")
        o = db.tag_object_by_id(self.dadgadID, u'test-fish/testconvtag')
        self.assertEqual(o, 0)
        status, v = db.get_tag_value_by_id(self.dadgadID,
                                           u'test-fish/testconvtag')
        self.assertEqual(v, None)


class TestFDBUtilityFunctions(unittest.TestCase):

    def setUp(self):
        self.db = FluidDB()
        self.user = self.db.credentials.username
        self.db.set_connection_from_global()
        self.db.set_debug_timeout(5.0)
        self.dadgadID = id(u'DADGAD', self.db.host)

    def testFullTagPath(self):
        db = self.db
        user = db.credentials.username
        self.assertEqual(db.full_tag_path(u'rating'),
                          u'/tags/%s/rating' % user)
        self.assertEqual(db.full_tag_path(u'/%s/rating' % user),
                          u'/tags/%s/rating' % user)
        self.assertEqual(db.full_tag_path(u'/tags/%s/rating' % user),
                          u'/tags/%s/rating' % user)
        self.assertEqual(db.full_tag_path(u'foo/rating'),
                          u'/tags/%s/foo/rating' % user)
        self.assertEqual(db.full_tag_path(u'/%s/foo/rating' % user),
                          u'/tags/%s/foo/rating' % user)
        self.assertEqual(db.full_tag_path(u'/tags/%s/foo/rating' % user),
                          u'/tags/%s/foo/rating' % user)

    def testAbsTagPath(self):
        db = self.db
        user = db.credentials.username
        self.assertEqual(db.abs_tag_path(u'rating'), u'/%s/rating' % user)
        self.assertEqual(db.abs_tag_path(u'/%s/rating' % user),
                         u'/%s/rating' % user)
        self.assertEqual(db.abs_tag_path(u'/tags/%s/rating' % user),
                         u'/%s/rating' % user)
        self.assertEqual(db.abs_tag_path('foo/rating'),
                         u'/%s/foo/rating' % user)
        self.assertEqual(db.abs_tag_path('/%s/foo/rating' % user),
                         u'/%s/foo/rating' % user)
        self.assertEqual(db.abs_tag_path('/tags/%s/foo/rating' % user),
                         u'/%s/foo/rating' % user)

    def testTagPathSplit(self):
        db = self.db

        user = db.credentials.username
        self.assertEqual(db.tag_path_split(u'rating'), (user, u'', u'rating'))
        self.assertEqual(db.tag_path_split(u'/%s/rating' % user),
                         (user, u'', u'rating'))
        self.assertEqual(db.tag_path_split('/tags/%s/rating' % user),
                         (user, u'', u'rating'))
        self.assertEqual(db.tag_path_split(u'foo/rating'),
                         (user, u'foo', u'rating'))
        self.assertEqual(db.tag_path_split('/%s/foo/rating' % user),
                         (user, u'foo', u'rating'))
        self.assertEqual(db.tag_path_split(u'/tags/%s/foo/rating' % user),
                         (user, u'foo', u'rating'))
        self.assertEqual(db.tag_path_split(u'foo/bar/rating'),
                               (user, u'foo/bar', u'rating'))
        self.assertEqual(db.tag_path_split(u'/%s/foo/bar/rating' % user),
                         (user, u'foo/bar', u'rating'))
        self.assertEqual(db.tag_path_split('/tags/%s/foo/bar/rating' % user),
                         (user, u'foo/bar', u'rating'))
        self.assertRaises(TagPathError, db.tag_path_split, u'')
        self.assertRaises(TagPathError, db.tag_path_split, u'/')
        self.assertRaises(TagPathError, db.tag_path_split, u'/foo')

    def testTypedValueInterpretation(self):
        corrects = {
                u'TRUE': (True, bool),
                u'tRuE': (True, bool),
                u't': (True, bool),
                u'T': (True, bool),
                u'f': (False, bool),
                u'false': (False, bool),
                u'1': (1, int),
                u'+1': (1, int),
                u'-1': (-1, int),
                u'0': (0, int),
                u'+0': (0, int),
                u'-0': (0, int),
                u'123456789': (123456789, int),
                u'-987654321': (-987654321, int),
                u'011': (11, int),
                u'-011': (-11, int),
                u'3.14159': (float('3.14159'), float),
                u'-3.14159': (float('-3.14159'), float),
                u'.14159': (float('.14159'), float),
                u'-.14159': (float('-.14159'), float),
                u'"1"': ('1', unicode),
                u'DADGAD': ('DADGAD', unicode),
                u'': ('', unicode),
                u'1,300': ('1,300', unicode),
                u'.': ('.', unicode),
                u'+.': ('+.', unicode),
                u'-.': ('-.', unicode),
                u'+': ('+', unicode),
                u'-': ('-', unicode),
        }
        for s in corrects:
            target, targetType = corrects[s]
            v = get_typed_tag_value(s)
            self.assertEqual((s, v), (s, target))
            self.assertEqual((s, type(v)), (s, targetType))


def specify_DADGAD(mode, host):
    if mode == 'about':
        return ('-a', 'DADGAD')
    elif mode == 'id':
        return ('-i', id('DADGAD', host))
    elif mode == 'query':
        return ('-q', 'fluiddb/about="DADGAD"')
    else:
        raise ModeError('Bad mode')


class TestCLI(unittest.TestCase):

    def setUp(self):
        self.db = FluidDB()
        self.user = self.db.credentials.username
        self.db.set_connection_from_global()
        self.db.set_debug_timeout(5.0)
        self.dadgadID = id('DADGAD', self.db.host)
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.stealOutput()
        self.hostname = ['--hostname', choose_host()]

    def stealOutput(self):
        self.out = SaveOut()
        self.err = SaveOut()
        sys.stdout = self.out
        sys.stderr = self.err

    def reset(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def Print(self, msg):
        self.stdout.write(toStr(msg) + '\n')

    def testOutputManipulation(self):
        print 'one'
        sys.stderr.write('two')
        self.reset()
        self.assertEqual(self.out.buffer, ['one', '\n'])
        self.assertEqual(self.err.buffer, ['two'])

    def tagTest(self, mode, verbose=True):
        self.stealOutput()
        (flag, spec) = specify_DADGAD(mode, self.db.host)
        description = describe_by_mode(spec, mode)
        flags = ['-v', flag] if verbose else [flag]
        args = ['tag'] + ['-U'] + flags + [spec, 'rating=10'] + self.hostname
        execute_command_line(*parse_args(args))
        self.reset()
        if verbose:
            target = ['Tagged object %s with rating = 10' % description, '\n']
        else:
            if mode == 'query':
                target = ['1 object matched', '\n']
            else:
                target = []
        self.assertEqual(self.out.buffer, target)
        self.assertEqual(self.err.buffer, [])

    def untagTest(self, mode, verbose=True):
        self.stealOutput()
        (flag, spec) = specify_DADGAD(mode, self.db.host)
        description = describe_by_mode(spec, mode)
        flags = ['-v', flag] if verbose else [flag]
        args = ['untag'] + ['-U'] + flags + [spec, 'rating'] + self.hostname
        execute_command_line(*parse_args(args))
        self.reset()
        if verbose:
            target = ['Removed tag rating from object %s\n' % description,
                      '\n']
        else:
            target = []
        self.assertEqual(self.out.buffer, target)
        self.assertEqual(self.err.buffer, [])

    def showTaggedSuccessTest(self, mode):
        self.stealOutput()
        (flag, spec) = specify_DADGAD(mode, self.db.host)
        description = describe_by_mode(spec, mode)
        args = (['show', '-U', '-v', flag, spec, 'rating', '/fluiddb/about']
                + self.hostname)
        execute_command_line(*parse_args(args))
        self.reset()
        self.assertEqual(self.out.buffer,
                ['Object %s:' % description, '\n',
                 '  /%s/rating = 10' % self.user, '\n',
                 '  /fluiddb/about = "DADGAD"', '\n'])
        self.assertEqual(self.err.buffer, [])

    def showUntagSuccessTest(self, mode):
        self.stealOutput()
        (flag, spec) = specify_DADGAD(mode, self.db.host)
        description = describe_by_mode(spec, mode)
        args = (['show', '-U', '-v', flag, spec, 'rating', '/fluiddb/about']
                 + self.hostname)
        execute_command_line(*parse_args(args))
        self.reset()
        self.assertEqual(self.out.buffer,
                ['Object %s:' % description, '\n',
                 '  %s' % cli_bracket('tag /%s/rating not present' % self.user),

                '\n', '  /fluiddb/about = "DADGAD"', '\n'])
        self.assertEqual(self.err.buffer, [])

    def testTagByAboutVerboseShow(self):
        self.tagTest('about')
        self.showTaggedSuccessTest('about')

    def testTagByIDVerboseShow(self):
        self.tagTest('id')
        self.showTaggedSuccessTest('id')

    def testTagByQueryVerboseShow(self):
        self.tagTest('query', verbose=False)
        self.showTaggedSuccessTest('id')

    def testTagSilent(self):
        self.tagTest('about', verbose=False)
        self.showTaggedSuccessTest('about')

    def atestUntagByAboutVerboseShow(self):
        self.untagTest('about')
        self.showUntagSuccessTest('about')

    def atestUntagByIDVerboseShow(self):
        self.untagTest('id')
        self.showUntagSuccessTest('id')

    def strip_list(self, list_):
        return [L.strip() for L in list_ if L.strip()]

    def command_sequence_test(self, commands, output):
        self.stealOutput()
        expected = self.strip_list(output if type(output) in (list, tuple)
                                          else [output])
        for command in commands:
            if type(command) == type(''):
                args = command.split(' ')
            else:
                args = command
            execute_command_line(*parse_args(args))
        self.reset()
        self.assertEqual(self.strip_list(self.out.buffer), expected)

    def test_simple_rm(self):
        commands = ('-U mkns test-fish/testns',
                    '-U rm test-fish/testns',
                    '-U ls -d test-fish/testns',)
        output = u'/%s/test-fish/testns not found' % self.user
        self.command_sequence_test(commands, output)
        
    def test_perms_simples(self):
        # Tests the simple permissions settings for namespaces
        #   --- private, default, lock, unlock

        commands = ('-U mkns test-fish/testns',
                    '-U perms private test-fish/testns',
                    '-U ls -ld test-fish/testns',
                    '-U perms default test-fish/testns',
                    '-U ls -ld test-fish/testns',
                    '-U perms lock test-fish/testns',
                    '-U ls -ld test-fish/testns',
                    '-U perms unlock test-fish/testns',
                    '-U ls -ld test-fish/testns',
                    '-U rm test-fish/testns',
        )
        output = (u'nrwc------   %s/test-fish/testns/' % self.user,
                  u'nrwcr--r--   %s/test-fish/testns/' % self.user,
                  u'nr-cr--r--   %s/test-fish/testns/' % self.user,
                  u'nrwcr--r--   %s/test-fish/testns/' % self.user,
        )
        self.command_sequence_test(commands, output)
    

if __name__ == '__main__':
    unittest.main()

