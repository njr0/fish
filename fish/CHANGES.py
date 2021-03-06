# -*- coding: utf-8 -*-

# CHANGES.py

"""
2009/08/20 v0.1       Initial version.   6 tests pass
                      Used to import 1456 objects from delicious sucessfully

2009/08/20 v0.2       Added some path tests and new tag_path_split method.
                      Added untag_object_by_id for removing a tag.
                      Made it so that 'absolute' paths for tags can be
                      used (e.g. '/njr/rating') to denote tags, as well
                      as relative paths (e.g. 'rating').
                      Subnamespaces still not recognized by tag/untag
                      but that should change soon.
                      Also, the tests should all actually work for people
                      whose FluidDB username isn't njr now :-)
                      10 tests pass now.

2009/08/20 v0.3       Reads the credentials file from the home
                      directory (unix/windows).
                      Removed import of no-longer-used fuilddb.py
                        (most of it was in-lined then bastardized)
                      Added ability to use the code from the command line
                      for tagging, untagging and retriving objects.
                      Currently this can be done by specifying the
                      about tag or object ID, though it will soon
                      support queries to select objects too (for some value
                      of 'soon').
                      See the USAGE string for command line usage
                      or run with the command line argument -h, or help.

2009/08/21 v0.4       Added query function to execute a query against
                      FluidDB and extended all the command line functions
                      to handle query, so that now you can tag, untag
                      and get tag values based on a query.
                      Also now specify json as the format on PUT
                      when creating tags; apparently they were binary before.
                      Also fixed things so that objects without an
                      about field can be created (I think).
                      Certainly, they don't cause an error.
                      A few other minor changes to put more sensible
                      defaults in for credentials etc., making it
                      easier to use the lirary interactively.

2009/08/21 v0.5       Renamed command line command get to show to avoid
                      clash with http GET command.
                      Plan to add raw put, get, post, delete, head commands.
                      The tests now assume that the credentials are in
                      the standard place (~/.fluidDBcredentials on unix,
                      or fluidDBcredential.ini in the home folder on
                      windows) and use that, though credentials can still
                      be provided in any of the old ways in the interface.

                      New class for testing the command line interface (CLI)

                      Can now run tests with
                          fdb         --- run all tests
                          fdb test    --- run all tests
                          fdb testcli --- test CLI only
                          fdb testcli --- test DB only

2009/08/22 v0.6       Added delicious2fluiddb.py and its friends
                      (delicious.py, delicious.cgi, deliconfig.py)
                      to the repository.   This allows all public
                      bookmarks from delicious to be uploaded to
                      FluidDB.   (In fact, a one line change would
                      allow private ones to be uploaded too, but
                      since fdb.py knows nothing about permissions
                      on tags yet, that seems like a bad idea for now.)

2009/08/22 v0.7       Corrected copyright year on delicious code

2009/08/22 v0.8       Added README and README-DELICIOUS files as
                      a form of documentation.

2009/08/22 v0.9       Added GET, POST, PUT, DELETE, HEAD commands to
                      command line interface.
                      To be honest, haven't tested most of these,
                         but get works in simple cases.
                      Added note of count of objects matching a query.
                      Added special case: '/about' expands to
                          '/fluiddb/about'
                      Added count command to CLI.
                      Also, in the CLI (but not the API), you can now
                         use /id as shorthand for the object's id.
                      Changed name of createTagIfNeeded parameters
                         to createAbstractTagIfNeeded. (Thanks, Xavi!)

2009/08/23 v1.0       Fixed fdb show -a DADGAD /id
                      which was doubly broken.
                      Hit v1.0 by virtue of adding 0.1 to 0.9 :-)

2009/08/23 v1.01      Added delicious2fluiddb.pdf

2009/08/24 v1.11      Added missing README to repository

2009/08/24 v1.12      Fixed four tests so that they work even
                      for user's *not* called njr...

2009/08/24 v1.13      Fixed bug that prevented tagging with real values.
                      Added tests for reading various values.
                      Made various minor corrections to
                      delicious2fluiddb.pdf.
                      Split out test class for FDB internal unit tests
                      that don't exercise/require the FluidDB API.
                      Added command for that and documented '-v'
                      (Also, in fact, fixed and simplied the regular
                      expressions for floats and things, which were wrong.)

2009/08/24 v1.14      Fixed delicious.py so it sets the font on the page.

2009/08/24 v1.15      Fixed problem with value encoding when setting tags.
                      (The json format was specification was in the wrong
                      place.)
                      @paparent helped to locate the problem --- thanks.
                      Also changed things so that -host/-sand
                      and -D (debug) work when
                      running the tests; unfortunately, this works by
                      reading the global flags variable.
                      Created KNOWN-PROBLEMS file, which is not empty
                      for v1.15.
2009/08/26 v1.16      Changed import httplib2 statement to avoid
                      strange hang when importing fdb from somewhere
                      other than the current directory through the python
                      path.
                      Corrected variable used in error reporting
                      in execute show_ command.

2009/08/26 v1.17      Added blank line between objects on show -q
                      Added -T to allow specification of an Http
                      timeout (useful at the moment, where the
                      sandbox can hang) and a default timeout of c. 300s.
                      Also, I've made the tests set the timeout to 5s
                      unless it has been set to something
                      explcitly by the user.

2009/08/26 v1.18      Yevgen did various bits of cleaning up, debugging
                      and standardization, most notably:
                         -- Using a decorator to avoid code repition
                         -- Moving flag/option handling to use the standard
                            optparse library instead of the custom flags lib.
                         -- fixing a couple of bugs
                         -- making everything work against the sandbox
                            as well as the main instance.
                      Also made the DADGAD_ID host-dependent.
                      May get FluidDB to cache IDs associated with about
                      tags and then load at start, save at end of session.
                      The cache would improve performance, and could
                      get emptied if corrupted or if the sandbox is reset
                      or whatever.

2009/09/01 v1.19      Added calls to the API (only) for creating
                      (sub)namespaces, deleting (sub)namespaces and
                      fetching descriptions of namespaces.
                      These have been manually tested, but no
                      units tests have been written yet, and the
                      command line interface has neither been extended
                      to make use of these calls or to provide new
                      primatives to let users use them from the command line.
                      All this and more will come.
                      The new functions, all methods on FluidDB, are:
                          create_namespace
                          delete_namespace
                          describe_namespace
                      create_namespace has an option to recurse if the
                      parent doesn't exist.   Although planned for the
                      the future (and arguments have been included in the
                      function signature), delete does not currently
                      support recursive deletion or forcing (in the case
                      tags or subnamspaces exist in the namespace).

2009/09/01 v1.20      Added nstest.py to git to illstrate namespace functions
                      added in 1.19.

2009/09/01 v1.21      Made tagging of objects create intermediate namespaces
                      as required.   This affects both the command line
                      utilities and the API calls.   Still no unit tests
                      though.

2009/09/24 v1.22      Updated to "new" API (thanks, Terry...)

2010/03/08 v1.23      Typo fixed; test changed to reflect new (improved)
                      FluidDB response to using bad credentials.
2010/03/26 v1.24      Fixed some weird indentation. Added encoding.
2010/03/28 v1.25      Fixed a unicode problem and some help text.
2010/03/30 v1.26      Changed the default action to be help, rather
                      than running tests.
                      Added tags command.
2010/03/30 v1.27      Removed extra namespace in output from tag above.
2011/01/33 v1.28      Modified testUntagObjectByID to reflect API changes
2011/01/34 v1.29      Added first stage of support for /values API.
                      Currently this is just a few functions to let this
                      be used programatically.
                      These new calls are unicode-based; also started adding
                      support for a future upgrade to the library to be
                      100% unicode.
2011/04/14 v1.30      Added __unicode__ method to class O.
                      Corrected version number.
2011/04/14 v1.31      Split into modules fdb.py, testfdb.py, cli.py,
                      and fdbcore.py
2011/04/14 v1.32      Added support for switching between unix-style
                      paths and Fluidinfo-style paths.   This can be
                      controlled by a line in the credentials file
                      or with command line flags (-F/-U).
                      See help and README for details.
2011/04/14 v1.33      Made help sensitive to path config/flags.

2011/05/26 v2.00      Switched to use Fluidinfo-style paths by default.
                      Fixed bug affecting some unicode characters in queries.
                      Added --version/-V flag to report version

2011/06/04 v2.01      Added pwd/pwn, whoami and su commands.
                      Added embryonic ls command (including embryonic
                      ls -l).
                      Added -u option to allow a user to be specified.
                      Improved handling of encoding to use
                      sys.getfilesystemencoding() rather than assuming
                      UTF-8, at least in some places, but this transition
                      is incomplete.

2011/06/04 v2.02      Fixed encodings so that unicode usernames
                      and passwords work.
                      Credentials file must be encoded in UTF-8.

2011/06/04 v2.03      More complete unicode improvements.
                      To a very good approximation, it is now true that
                         - All strings are stored internally as unicode
                         - Keyboard input is read correctly using the
                           encoding specified by sys.getfilesystemencoding()
                         - Data is UTF-8-encoded just before transmitting
                           to Fluidinfo
                         - Data is decode from UTF-8 immediately upon
                           receipt from Fluidinfo.
                     Not all the test data has yet been upgraded this way
                     and there is still far too little unicode data in
                     the tests.

                     At the time of this commit, lots of things are
                     not working with unicode namespaces, but that appears
                     to be a problem with the main instance; similar
                     things are working on the Sandbox.

2011/06/05 v2.04     Completed ls command, adding ls -L
                     (well, -g still to add...)
                     Completed draft of complete documentation.

2011/06/05 v2.05     Added -g (group) flag to ls.
                     Added fdb perms command.
                     Completed first draft of full command line
                     which is now included in the distribution
                     and available online, hosted in Fluidinfo
                     itself/ at
                     http://fluiddb.fluidinfo.com/about/fdb/njr/index.html.

2011/06/07 v2.06     Fixed some import problems caused by renaming
                     fdb.py as fdb.

2011/06/07 v2.07     Added perms lock command (to remove all write perms)

2011/06/09 v2.08     Changed all the optparse stuff back not to use
                     unicode as a lot of versions of optparse don't
                     seem to work with unicode.

2011/06/09 v2.09     Can now use ls -P to list default permissions
                     (also known as /policies).

2011/06/09 v2.10     Fixed su command, which got broken by the optparse fix.

2011/06/09 v2.11     Changed fdb back to fdb.py and created new fdb
                     that imports it so that it can run.

2011/06/09 v2.12     Changed to use /about wherever possible.
                     Added test for get_object_tags; this
                     also uses non-ASCII, non-latin-1 tag names
                     and values as a test of unicode handling.

2011/06/09 v2.13     Added a test of the values API (which doesn't
                     seem to like unicode tag names.

2011/06/09 v2.14     Fixed some problems I introduced in 2.12
                     that prevented things working correctly with
                     about tags that contained slashes (like URLs).
                     This is because the about tag wasn't being
                     encoded properly when used with /about.
                     Added a couple of tests for that and related,
                     potentially problematical about tags.
                     Improved the readability of the error message
                     printed when fdb fails to find user credentials.

2011/06/09 v2.15     Added -2 flag to force high verbosity on tests
                     (to stop me leaving it set high, as I did in 2.14)

2011/06/11 v2.16     Made a set of changes to make things run better
                     as a web service.
                     Changed the way things work on windows to
                     remove the need for win32com
                     As a result, it now looks for the credentials file
                     in a location specified by the environment variable
                     FDB_CREDENTIALS_FILE, or c:\fdb\credentials.txt if
                     the variable is not defined.
                     Removed use of codecs in win32, since it doesn't
                     seem to work (so perhaps not unicode user names
                     or passwords on windows).

2011/06/15 v2.17     Added amazon command for getting an about tag
                     from an Amazon (US|UK, books/music) product page.

                     This adds a dependency on the abouttag lib,
                     which might be made conditional.

                     Removed leading fdb from top-level help.

                     Restored accidentally disable count command

                     Added per-command help.

                     Changed various things to support the web app
                     (shell-fish) like printing, some exceptions etc.
                     Added extra arguments to functions such as
                     execute command line in support of above.

                     Changed core help examples to use Paris rather
                     than DADGAD as the example object.

2011/06/15 v2.18     Added rm command (including -r)
                     Added touch command and mkns/mkdir commands.
                     Changed execute_command_line to catch exceptions
                     and made a few more commands throw exceptions.
                     (-D suppresses this.)
                     Now accept -r or -R for all recursive commands.

2011/06/18 v3.00     Fish being pushed to github for the first time.
                     Added support for low-level read, write and control
                     arguments to perms command.
                     Check the availability of the abouttag library
                     before using the amazon command.

2011/06/18 v3.01     Fixed touch, which had a verbose option that broke it.
                     Added -X flag to perms to allow even finer-grained
                     control of permissions.

2011/06/18 v3.02     Changed fish descriptions of tag controls, as reported
                     by ls -L, to acontrol and tcontrol (from control).

2011/07/06 v3.04     Added abouttag command (aka about).
                     Repaired whoami documentation.

2011/07/06 v3.05     Merged v3.03 and v3.04

2011/07/09 v3.06     Changed tests so that all tags used/created live in
                     a test-fish namespace under the user.
                     Improved some unicode/UTF8 conversions to fix problem
                     with removing αβγδε from the command line.
                     Fixed at least some problems that had been introduced
                     into the perms command.
                     Made -v do something with perms command

2011/07/09 v3.07     Added a couple of new CLI tests and a new, simpler
                     mechanism for testing CLI command sequences.
                     Added -G option to ls for longest listing, which now
                     does what ls -L used to do; ls -L now compresses
                     the output to show simple read/write/control
                     if this is possible. 
                     Fixed a bug that prevented ls -L from showing
                     the update (metadata) permission for namespaces.
                     Fixed an amazing bug that broke most of the
                     perms command.
                     Fixed a problem preventing ls -d from complaining
                     if the namespace did not exist.

2011/07/11 v3.08     Removed ABSTRACT form ls -G heading.

2011/07/18 v3.09     Added an interactive shell, which uses readline
                     and supports left quoting (backticks) and command
                     history.
                     Added normalize command.
                     Consolidated help for Unix-style paths and
                     Fluidinfo-style paths.
                     Changed example user to alice and bert (though
                     not yet in the documentation).

2011/07/18 v3.10     Committed repl.py

2011/07/18 v3.11     Improved import statement for nacolike

2011/07/18 v3.12     Refactored REPL etc. so it can be used by Shell-Fish

2011/07/26 v3.13     Added quit and exit commands (mostly for interactive
                     shell; some unicode conversion to UTF-8 on output.

2011/07/27 v3.14     Allow string sets to be written.
                     Also Preparing ground for Python/JSON API-FROM-CLI

2011/07/31 v4.00     Added get command; like show, but terser.
                     Improved debugging options to work better with
                     shell-fish.
                     Added embryonic json and python arguments
                     on the way to creating a command-based API.
                     Now route all HTTP requests through
                     FluidDB.request, which checks for 500 errors
                     and reports them.

2011/08/01 v4.01     Reinstated more unicode in the test suite now that
                     some API bugs have been fixed.
                     Started to add sequence support.
                     Upgraded /values support slightly.

2011/08/05 v4.02     Now sort tags when using tags command, always with
                     about tag first, and otherwise in alphabetical order.
                     Also added get_values_by_id function.
                     Now check environment for FISHUSER variable and
                     use that credentials file if it is set.

2011/08/06 v4.03     Fixed sort_tags and removed from show.
                     (Still used in tags.)

2011/08/06 v4.04     Completed first implementation of seq and listseq
                     commands.
                     
2011/08/07 v4.05     Refactored class O in anticipation of pickling it.
                     for aliases etc.
                     Renamed FluidDB class Fluidinfo 

2011/08/07 v4.06     Completed seq, listseq, mkseq commands.
                     Added alias command
                     Added cache and showcache command to view it.
                     Added sync command to refresh the cache.

2011/08/07 v4.07     Added unalias and init commands.

2011/08/07 v4.08     Alias handling enhanced (preserving options better)

2011/08/10 v4.09     Filtering on sequences

2011/08/12 v4.10     Corrected an ._types to a .types, reflecting previous
                     changes to class O.

2011/08/12 v4.11     Added support for migrating shell-fish to abouttag.
                     Rejigged the cache to allow an alternative version
                     to be used from App Engine.
                     Corrected help for show -q etc. (used about = "Paris"
                     instead of fluiddb/about = "Paris").
                     (That change was also the patch applied to 4.00.0
                     after the /. comment.)
                     Cleaned up some of the sequence stuff a little.
                     Started documenting some of the new features
                     and removing silly duplicate documentation.
                     Cleaned up the formatting slightly, too.
                     (Why does Sphinx but lists in blockquotes?)

2011/09/07 v4.12
Updated documentation.   Green colour-scheme.

2011/12/18 v4.13
Fixed a couple of bugs.
  - Non-primitive tag values now show in a more sensible way.
  - Restored the ability to specify objects by ID (which had been
    inadvertantly broken).
  - Format sets of strings slightly better (one per line), so that
    poor humans have some chance of reading them.

2011/12/18 v4.14
Made /id work.   Something broke it.   (Well, someone, to be more precise.)
And made /about show consistently in the tags command.

2011/12/18 v4.15
Manually pulled in otoburb's pull request changes (since too much had
changed for an auto-merge :-().  Thanks, Otoburb, for all the
clean-up.  Sorry for being so slow...

2011/12/18 v4.16
Documented the new commands (sequence commands, alias commands, sync, init
And search).

2011/12/19 v4.17
Fixed a bug that meant /id produced the wrong ID when used with -a.
Changed show, get, tag, untag and tags so that if no -a, =i or -q
option is used, but arguments are present, the first argument will
be taken as either an object ID (if it looks like one) or an about tag,
if it doesn't.

2011/12/19 v4.18
Fixed a typo.

2011/12/30 v4.19
Added -f option tag: allows the contents of a file to be used as a tag value,
with MIME-type guessing.   Also -M, to set the MIME type.

Also added fish_command function to fish.py.   This allows a simple way
to pass a fish command in programmatically, ignoring caches, either as the
default user or as a nominated user.

2012/01/01 v4.20
Fixed a problem introduced when adding the ability to write files with -f
that sometimes caused unicode strings not to be written properly.

2012/01/01 v4.21
Fixed the copyright notices to run to 2012.

2012/01/01 v4.22
Fixed typo: vsg --> svg

2012/01/01 v4.23
Changed compound value handling to reflect the API change in release 1.14.
Now either square or brackets or braces can be used to specify a compound
value, which is a list.   Compound values are shown in square brackets
by show, get etc.

Changed formatted_tag_value so that it shows textual MIME types.

Changed tagging so that -f causes tags with no specified file to be
read from stdin and written as text/plain.

2012/01/01 v4.24
Removed sort from formatted_tag_value for compound values, which are now
lists rather than sets.

2012/01/01 v4.25
Added -@ option, for tagging anonymous objects.

2012/01/14 v4.26
Merged in changes from different machine.

Added to_fi_tags to Fluidinfo in fishlib.py.
Noticed that the test testValuesAPISetGet fails under my python 2.7
installation, which is a 64-bit copy.   Will investigate.

Added values.py to git.

Added webapp option to Fluidinfo to allow the web app to indicate it is
in use.   For now, the only effect of this is to cause the tag command
to complain (exceptionally...) if the -f option is used.

2012/01/15 v4.27
Removed 'with' statements to make run against Python 2.5.
Fixed some unicode issues.
Made the abouttag import test more robust.

2012/01/15 v4.28
Added webapp argument to ExtendedFluidinfo and pass to its superclass
to avoid a crash.

2012/01/15 v4.29
Actually made the change that was supposed to be in 4.28.

2012/01/18 v4.30
Changed from httplib2 to requests.

2012/01/18 v4.31
Fixed a problem whereby sync would fail if there was not .fish/alias
tag defined.   It now defines it in this case.
(This also caused a problem on starting fish interactively,
since that does a sync.)

Moved some code from fish.py to cli.py to facilitate the above change.

Fixed a problem whereby Fluidinfo.tag_by_query would fail under
python2.7 if there were non-ascii characters in tag names or values.
This was because I was lazily constructing a json-like string by hand
instead of using json.dumps.   Oddly, this worked fine in python 2.5, 2.6.

Cleaned up the import structure a bit.

In principle, I would much rather use the requests library rather than
httplib2 in all circumstances, but there are two problems:

  1. It is not universally available (e.g., as far as I can tell, it's
     not available on Google App Engine

  2. Either there's something wrong with 1.0.0 and above or Fish is
     using it wrongly because requests is having a problem iterating
     over the headers Fish is sending it.

For the moment, therefore, I have made it so that tries to import
requests and checks that it is a version under 1.0.0.   If the
library is not present, or is at 1.0.0 or above, Fish falls back to
httplib2.

2012/01/24 v4.32
Turned this into something more like a proper python package
with a setup.py, moved the fish script into scripts etc.
Plan to add to PyPI.

2012/01/24 v4.33
Updated installation section of documentation and README.
Localised imports.
Was getting all ready to push fish to pypi, but there's already a fish there.

2012/01/25 v4.24
Added missing setup.py
"""

