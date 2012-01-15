import math
import sys
import types
import fishlib
import cli
import flags

if sys.version_info < (2, 6):
    try:
        import simplejson as json
    except ImportError:
        from django.utils import simplejson as json
else:
    import json


class PermissionsError(Exception):
    pass


class WisdomFailure(Exception):
    pass


class RemoveError(Exception):
    pass


class PermissionDesc:
    def __init__(self, entity, path, actions, names):
        self.entity = entity
        self.path = path
        self.actions = actions
        self.names = names

    def action(self, name):
        return self.actions[self.names.index(name)]


RAW_PERMS = {
    u'abstract-tag': PermissionDesc(u'abstract-tag', u'tags',
                                    [u'update', u'delete', u'control'],
                                    [u'metadata', u'delete', u'acontrol']),
    u'tag': PermissionDesc(u'tag', u'tag-values',
                           [u'create', u'read', u'delete', u'control'],
                           [u'tag', u'read', u'untag', 'tcontrol']),
    u'namespace': PermissionDesc(u'namespace', u'namespaces',
                                 [u'create', u'update', u'delete', u'list',
                                  u'control'],
                                 [u'create', u'metadata', u'delete', u'read',
                                  u'control'])
}

RAW_PERM_ENTITIES = RAW_PERMS.keys()

READ_NAMES = [u'read']
WRITE_NAMES = [u'create', u'metadata', u'tag', u'untag', u'delete']
CONTROL_NAMES = [u'acontrol', u'tcontrol', u'control']
ALL_NAMES = READ_NAMES + WRITE_NAMES + CONTROL_NAMES


class UnixPerm:
    def __init__(self, s):
        n = ord(s) - ord(u'0')
        if not 0 <= n <= 7:
            raise PermissionsError(u'Permissions string must have form ddd '
                                   u'with each d in range 0-7')
        self.read = n & 4 == 4
        self.write = n & 2 == 2
        self.control = n & 1 == 1

    def __unicode__(self):
        return u'%s%s%s' % (u'r' if self.read else u'-',
                            u'w' if self.write else u'-',
                            u'c' if self.control else u'-')


class UnixPerms:
    def __init__(self, spec, user, isTag=None):
        self.user = user
        self.owner = UnixPerm(spec[0])
        self.group = UnixPerm(spec[1])
        self.world = UnixPerm(spec[2])

        self.read = self.fi_perm(self.world.read, self.owner.read, isTag)
        self.write = self.fi_perm(self.world.write, self.owner.write, isTag)
        self.control = self.fi_perm(self.world.control, self.owner.control,
                                    isTag)

    def fi_perm(self, w, o, isTag):
        policy = u'open' if w else u'closed'

        if policy == u'closed':
            exceptions = [self.user] if o else []
        else:
            exceptions = [] if o else [self.user]
        return FluidinfoPerm(self.user, policy, exceptions, isTag)

    def check_owner_control_ok(self):
        if not self.owner.control:
            raise WisdomFailure(u'I\'m reluctant to all you to remove your '
                                u'own control permission')

    def __unicode__(self):
        return u'%s%s%s' % (unicode(self.owner), unicode(self.group),
                            unicode(self.world))


class FluidinfoPerm:
    def __init__(self, owner, policy=None, exceptions=None, hash=None,
                 name=None, action=None, isTag=None, isPolicy=False):
        self.owner = owner
        self.name = name
        self.action = action
        self.isTag = isTag
        self.isPolicy = isPolicy
        if hash:
            self.policy=hash[u'policy']
            self.exceptions=hash[u'exceptions']
        else:
            self.policy = policy
            self.exceptions = exceptions

    def accessible(self, code, user):
         return (code if self.policy == u'open' or user in self.exceptions
                      else u'-')

    def isOpen(self, code):
         return code if self.policy == u'open' else u'-'

    def __unicode__(self):
        return u'policy: %s; exceptions = [%s]' % (self.policy,
                                                   u', '.join(self.exceptions))


class FluidinfoPerms:
    def __init__(self, db, path, isTag, getFromFI=True, isPolicy=False):
        self.isTag = isTag
        self.isPolicy = isPolicy
        self.path = path
        self.valid = True
        self.entities = [u'abstract-tag', u'tag'] if isTag else [u'namespace']
        self.compressIfPoss = True              # used by ls -L / -G

        self.owner = path.split(u'/')[1]
        for entity in self.entities:
            desc = RAW_PERMS[entity]
            for (action, name) in zip(desc.actions, desc.names):
                if getFromFI:
                    if isPolicy:
                        p = db.get_raw_policy(entity, path[1:], action)
                        
                    else:
                        p = db.get_raw_perm(entity, path[1:], action, isTag)
                    self.__dict__[name] = p
                    if type(p) in (int, long):
                        self.value = False
                else:
                    # figure out defaults etc.
                    policy = u'open' if name in READ_NAMES else u'closed'
                    exceptions = [] if name in READ_NAMES else [self.owner]
                    self.__dict__[name] = FluidinfoPerm(self.owner, policy,
                                                        exceptions, None,
                                                        name, action, isTag,
                                                        isPolicy)

    def set_to_private(self):
        for name in ALL_NAMES:
            if name in self.__dict__:
                self.__dict__[name].policy = u'closed'
                self.__dict__[name].exceptions = [self.owner]
            
    def set_to_default(self):
        for name in ALL_NAMES:
            if name in self.__dict__:
                if name in READ_NAMES:
                    self.__dict__[name].policy = u'open'
                    self.__dict__[name].exceptions = []
                else:
                    self.__dict__[name].policy = u'closed'
                    self.__dict__[name].exceptions = [self.owner]

    def set_group_writable(self, group):
        fullgroup = group + ([] if self.owner in group else [self.owner])
        for name in WRITE_NAMES:
            if hasattr(self, name):
                self.__dict__[name].policy = u'closed'
                self.__dict__[name].exceptions = fullgroup

    def set_group_readable(self, group):
        fullgroup = group + ([] if self.owner in group else [self.owner])
        self.__dict__[u'read'].policy = u'closed'
        self.__dict__[u'read'].exceptions = fullgroup

    def lock(self):
        for name in WRITE_NAMES:
            if hasattr(self, name):
                self.__dict__[name].policy = u'closed'
                self.__dict__[name].exceptions = []

    def unlock(self):
        for name in WRITE_NAMES:
            if hasattr(self, name):
                self.__dict__[name].policy = u'closed'
                self.__dict__[name].exceptions = [self.owner]

    def check_owner_control(self, p):
        if ((p.policy == 'open' and self.owner in p.exceptions)
                or (p.policy == 'closed' and not self.owner in p.exceptions)):
            raise PermissionsError(u'You are attempting to set permissions '
                                   u'that do not include owner control.\n'
                                   u'  If you are sure you know what you are '
                                   u'doing, you can force this with -f.')

    def update_fluidinfo(self, db, permsToSet=None, force=False,
                         restrict_to=None, verbose=False):
        permsToSet = permsToSet or ALL_NAMES
        # check owner has control permissions
        if not force:
            for name in CONTROL_NAMES:
                if hasattr(self, name):
                    self.check_owner_control(self.__dict__[name])
        entities = (u'abstract-tag', u'tag') if self.isTag else (u'namespace',)
        for entity in entities:
            for name in RAW_PERMS[entity].names:
                if name in permsToSet and (not restrict_to
                                           or name in restrict_to):
                    action = RAW_PERMS[entity].action(name)
                    if verbose:
                        db.Print(u'Setting %s %s\'s %s permission to %s '
                                 u'except %s' % (entity, self.path[1:],
                                                 action,
                                  self.__dict__[name].policy,
                                  unicode(self.__dict__[name].exceptions)))
                    err = db.set_raw_perm(entity, self.path[1:], action,
                                          self.__dict__[name].policy,
                                          self.__dict__[name].exceptions)
                    if err:
                        db.warning(cli.error_code(err))

    def fi_tag_desc(self):
        s = [u'']
        writes = (u'metadata', u'delete', u'tag', u'untag')
        controls = (self.acontrol, self.tcontrol)
        wPerms = []
        for kind in (u'ABSTRACT TAG', u'TAG'):
            desc = RAW_PERMS[u'tag' if kind == u'TAG' else u'abstract-tag']
            L = u't' if kind == u'TAG' else u'a'
            s.append(kind[-3:] + u' (/%s)' % desc.path)
            if kind == u'TAG':
                s.append(u'  Read')
                s.append(u'    %-19s  %s' % (u'read (read):',
                                             unicode(self.read)))
            s.append(u'  Write')
            for (fi, fdb) in zip(desc.actions, desc.names):
                if fdb in writes:
                    w = unicode(self.__dict__[fdb])
                    wPerms.append(w)
                    s.append(u'    %-19s  %s' % (u'%s (%s):' % (fi, fdb), w))
            s.extend([u'  Control'])
            c = self.tcontrol if kind == u'TAG' else self.acontrol
            s.append(u'    %-19s  %s' % (u'control (%scontrol):' % L,
                                         unicode(c)))
            s.append(u'')

        if self.compressIfPoss:
            if (all(w == wPerms[0] for w in wPerms[1:])
                  and unicode(self.acontrol) == unicode(self.tcontrol)):
                s = [u'     read: %s' % unicode(self.read),
                     u'    write: %s' % unicode(wPerms[0]),
                     u'  control: %s' % unicode(self.acontrol),
                     u'']
        return u'\n'.join(s)

    def fi_ns_desc(self):
        s = [u'']
        writes = (u'create', u'metadata', u'delete')
        desc = RAW_PERMS[u'namespace']
        s.append(u'NAMESPACE (/%s)' % desc.path)
        s.append(u'  Read')
        s.append(u'    %-18s  %s' % (u'list (read):', unicode(self.read)))
                                     
        s.append(u'  Write')
        wPerms = []
        for (fi, fdb) in zip(desc.actions, desc.names):
            if fdb in writes:
                w = unicode(self.__dict__[fdb])
                wPerms.append(w)
                s.append(u'    %-18s  %s' % (u'%s (%s):' % (fi, fdb), w))
        s.append(u'  Control')
        s.append(u'    %-18s  %s' % (u'control (control):', self.control))
        if self.compressIfPoss and all(w == wPerms[0] for w in wPerms[1:]):
            s = [u'     read: %s' % unicode(self.read),
                 u'    write: %s' % unicode(wPerms[0]),
                 u'  control: %s' % unicode(self.control)]
        s.append(u'')
        return u'\n'.join(s)

    def __unicode__(self):
        if self.isTag is None:
            raise Exception
        if not self.valid:
            return ' (denied) '
        return self.fi_tag_desc() if self.isTag else self.fi_ns_desc() 


def string_format(n):
    return u'%%-%ds' % n


def len_exc(exceptions, owner):
    return len(exceptions) - 1 if owner in exceptions else len(exceptions)


def combined_status(list_):
    L = list_[0]
    return L if all(ell == L for ell in list_) else u'/'

def to_string_grid(items, pageWidth=78, maxCols=9):
    if items == []:
        return u''
    widest = max([len(s) for s in items])
    nCols = min(max(pageWidth / (widest + 1), 1), maxCols)
    colWidth = int(math.ceil(float(pageWidth) / nCols)) - 1
    fmt = string_format(colWidth)
    nItems = len(items)
    nRows = int(math.ceil(float(nItems) / nCols))

    return u'\n'.join([u' '.join([fmt % items[col * nRows + row]
                           for col in range(nCols)
                               if col * nRows + row < nItems])
                                   for row in range(nRows)])


class ExtendedFluidinfo(fishlib.Fluidinfo):
    def __init__(self, credentials=None, host=None, debug=False,
                 encoding=fishlib.DEFAULT_ENCODING, unixStylePaths=None,
                 saveOut=False, cache=None, webapp=False):
        fishlib.Fluidinfo.__init__(self, credentials, host, debug,
                                   encoding, unixStylePaths, saveOut,
                                   cache, webapp)

    def list_namespace(self, ns, returnDescription=True,
                        returnNamespaces=True, returnTags=True):
        status, content = self.call(u'GET', u'/namespaces/%s' % ns, None,
                                    returnDescription=returnDescription,
                                    returnNamespaces=returnNamespaces,
                                    returnTags=returnTags)
        return content if status == fishlib.STATUS.OK else status

    def list_r_namespace(self, rootns):
        L = self.list_namespace(rootns, returnDescription=False)
        if L == fishlib.STATUS.NOT_FOUND:
            return fishlib.STATUS.NOT_FOUND
        if type(L) in (int, long):
            return {u'namespaceNames': [], u'tagNames': [], u'failures': True}
        failures = False
        namespaces = [u'%s/%s' % (rootns, space)
                        for space in L[u'namespaceNames']]
        tags = [u'%s/%s' % (rootns, tag) for tag in L[u'tagNames']]
        subns = []
        subtags = []
        for s in namespaces:
            L = self.list_namespace(s, returnDescription=False)
            if type(L) in (int, long):
                failures = True
            else:
                subns.extend([u'%s/%s' % (s, space)
                                  for space in L[u'namespaceNames']])
                subtags.extend([u'%s/%s' % (s, space)
                                  for space in L[u'tagNames']])
        namespaces.extend(subns)
        tags.extend(subtags)
        return {u'namespaceNames': namespaces, u'tagNames': tags,
                u'failures': failures}

    def rm_r(self, rootns):
        L = self.list_r_namespace(rootns)
        if L == fishlib.STATUS.NOT_FOUND:
            return L
        elif L[u'failures']:
            return 1            # non-zero failure code
        # First delete all the tags & sub-namespaces
        for items, fn in ((L[u'tagNames'], self.delete_abstract_tag),
                          (L[u'namespaceNames'], self.delete_namespace)):
            si = [(i.split(u'/'), i) for i in items]
            z = [(len(s), i) for (s, i) in si]
            z.sort()
            z.reverse()
            failed = 0
            for (n, i) in z:
                r = fn(u'/%s' % i)
                failed = failed or (r if r != fishlib.STATUS.NO_CONTENT
                                    else 0)
        if failed:
            return failed
        return self.delete_namespace(u'/' + rootns)

    def rm_all_tag_values(self, tag):
        self.untag_by_query()

    def list_sorted_ns(self, ns, long_=False, columns=True, recurse=False,
                       prnt=False, longer=False, longest=False):
        h = self.list_namespace(ns)
        return self.list_sorted_nshash(h, ns, long_, columns, recurse,
                                       prnt=prnt, longer=longer,
                                       longest=longest)

    def list_sorted_nshash(self, h, ns, long_=False, columns=True,
                           recurse=False, prnt=False, longer=False,
                           longest=False):
        if type(h) in (int, long):
            if h == fishlib.STATUS.UNAUTHORIZED:
                return u'Permission denied.'
            else:
                return u'Error status %s' % h

        tagNames = h[u'tagNames']
        tagNames.sort()
        spaces = h[u'namespaceNames']
        spaces.sort()
        items = tagNames[:] + [u'%s/' % space for space in spaces]
        items.sort()
        if items:
            fmt = string_format(max([len(item) for item in items]))
        if recurse:
            self.Print(u'\n%s:' % ns)
        if long_ or longer or longest:
            res = []
            for item in items:
                r = self.full_perms(ns + u'/' + fmt % item, longer,
                                    longest=longest)
                res.append(r)
                if prnt:
                    self.Print(r)
            result = u'\n'.join(res)
        elif columns == False:
            result = u'\n'.join(items)
            if prnt:
                self.Print(result)
        else:
            result = to_string_grid(items)
            if prnt:
                self.Print(result)
        if recurse:
            others = u'\n'.join([self.list_sorted_ns(u'%s/%s' % (ns, space),
                                                     long_, columns, recurse,
                                                     prnt=prnt, longer=longer,
                                                     longest=longest)
                                 for space in spaces])
            return u'%s:\n%s\n\n%s' % (ns, result, others)
        else:
            return result

    def get_raw_perm(self, entity, name, action, isTag):
        assert entity in RAW_PERM_ENTITIES
        owner = entity.split(u'/')[0]
        perm = RAW_PERMS[entity]
        assert action in perm.actions
        path = u'/permissions/%s/%s' % (perm.path, name)
        status, content = self.call(u'GET', path, None, action=action)
        return (FluidinfoPerm(owner, hash=content, name=name, action=action,
                              isTag=isTag)
                if status == fishlib.STATUS.OK else status)

    def get_raw_policy(self, entity, owner, action):
        assert entity in RAW_PERM_ENTITIES
        perm = RAW_PERMS[entity]
        assert action in perm.actions
        path = u'/policies/%s/%s/%s' % (owner, perm.path, action)
        status, content = self.call(u'GET', path, None, action=action)
        return (FluidinfoPerm(owner, hash=content, name=owner, action=action,
                              isPolicy=True)
                if status == fishlib.STATUS.OK else status)

    def get_tag_perms_hash(self, tag):
        h = {}
        for entity in [u'abstract-tag', u'tag']:
            desc = RAW_PERMS[entity]
            for (action, name) in zip(desc.actions, desc.names):
                h[name] = self.get_raw_perm(entity, tag, action, True)
        return h

    def get_ns_perms_hash(self, ns):
        h = {}
        for entity in [u'namespace']:
            desc = RAW_PERMS[entity]
            for (action, name) in zip(desc.actions, desc.names):
                h[name] = self.get_raw_perm(entity, ns, action, False)
        return h

    def tag_perms_string(self, tag, group=False):
        h = self.get_tag_perms_hash(tag)
        s = []
        owner = tag.split(u'/')[0]
        r = h[u'read']
        a, t = h[u'acontrol'], h[u'tcontrol']
        writes = (h[u'metadata'], h[u'delete'], h[u'tag'], h[u'untag'])
        ownerRead = r.accessible(u'r', owner)
        ownerWrites = [w.accessible(u'w', owner) for w in writes]
        ownerControl = combined_status((t.accessible(u'c', owner),
                                        a.accessible(u'c', owner)))
        worldControlT = t.isOpen(u'c')
        worldControlA = a.isOpen(u'c')
        worldControl = (worldControlT if worldControlT == worldControlA
                                      else u'/')
        worldRead = r.isOpen(u'r')
        worldWrites = [w.isOpen(u'w') for w in writes]
        ownerWrite = write_status(ownerWrites)
        worldWrite = write_status(worldWrites)

        groupRead = self.group_perm(u'r', r, owner)
        groupWrite = combined_status([self.group_perm(u'w', w, owner)
                                      for w in writes])
        groupControl = combined_status([self.group_perm(u'c', c, owner)
                                        for c in (a, t)])

        ps = u't%s%s%s%s%s%s%s%s%s' % (ownerRead, ownerWrite, ownerControl,
                                       groupRead, groupWrite, groupControl,
                                       worldRead, worldWrite, worldControl)
        if group:
            return ps + u'   ' + self.group_members(r, writes, owner)
        else:
            return ps


    def group_perm(self, code, perm, owner):
        n = len_exc(perm.exceptions, owner)
        if perm.policy == u'closed':
            return code if n > 0 else u'-'
        else:
            return u'-' if n > 0 else code

    def fi_perm_desc(self, perm):
        return (u'policy: %s; exceptions [%s]'
                % (perm.policy,
                   u', '.join(u for u in perm.exceptions)))

    def ns_perms_string(self, ns, group=False):
        h = self.get_ns_perms_hash(ns)
        for k in h:
            if type(h[k]) in (int, long):
                return ' (denied) '
        s = []
        owner = ns.split(u'/')[0]
        r = h[u'read']
        control = h[u'control']
        writes = (h[u'create'], h[u'metadata'], h[u'delete'])
        ownerRead = r.accessible(u'r', owner)
        ownerWrites = [w.accessible(u'w', owner) for w in writes]
        worldRead = r.isOpen(u'r')
        worldWrites = [w.isOpen(u'w') for w in writes]
        ownerWrite = write_status(ownerWrites)
        worldWrite = write_status(worldWrites)
        ownerControl = control.accessible(u'c', owner)
        worldControl = control.isOpen(u'c')
        groupRead = self.group_perm(u'r', r, owner)
        groupWrite = combined_status([self.group_perm(u'w', w, owner)
                                      for w in writes])
        groupControl = self.group_perm(u'c', control, owner)

        ps = u'n%s%s%s%s%s%s%s%s%s' % (ownerRead, ownerWrite, ownerControl,
                                       groupRead, groupWrite, groupControl,
                                       worldRead, worldWrite, worldControl)
        if group:
            return ps + u'   ' + self.group_members(r, writes, owner)
        else:
            return ps

    def group_members(self, r, writes, owner):
        if r.isOpen(u'r') == u'r':
            gr = u''.join((u'-%s' % e) for e in r.exceptions
                                       if not e == owner)
        else:
            gr = u'+'.join(e for e in r.exceptions if not e == owner)

        gw = []
        for w in writes:
            if w.isOpen(u'w') == u'w':
                g = u''.join((u'-%s' % e) for e in w.exceptions
                                       if not e == owner)
            else:
                g = u'+'.join(e for e in w.exceptions if not e == owner)
            gw.append(g)
        gw = gw[0] if all(w == gw[0] for w in gw) else u'<variable>'
        if gw == u'':
            gw = u'(world)'
        if gr == u'':
            gr = u'(world)'
        if gw == gr:
            gs = gr
        else:
            gs = u'r:%s  w:%s' % (gr, gw)
        return gs

    def perms_string(self, tagOrNS, longer=False, group=False, longest=False):
        tagOrNS = tagOrNS.strip()
        if tagOrNS.endswith(u'/'):
            if longer or longest:
                p = FluidinfoPerms(self, u'/' + tagOrNS[:-1], isTag=False)
                p.compressIfPoss = not longest
                return unicode(p)
            else:
                return self.ns_perms_string(tagOrNS[:-1], group)
        else:
            if longer or longest:
                p = FluidinfoPerms(self, u'/' + tagOrNS, isTag=True)
                p.compressIfPoss = not longest
                return unicode(p)
            else:
                try:
                    return self.tag_perms_string(tagOrNS, group)
                except AttributeError:
                    raise PermissionsError(u'Forbidden (you don\'t appear to'
                        u' have control permission for %s)' % tagOrNS)

    def full_perms(self, tagOrNS, longer, group=False, longest=False):
        perms = self.perms_string(tagOrNS, longer, group, longest)
        if longer or longest:
            return u'\n%s:\n%s' % (tagOrNS, perms)
        else:
            return u'%s   %s' % (perms, tagOrNS)
                
    def set_raw_perm(self, entity, path, action, policy, exceptions):
        assert entity in RAW_PERM_ENTITIES
        perm = RAW_PERMS[entity]
        assert action in perm.actions
        assert policy in (u'open', u'closed')
        assert not type(exceptions) in types.StringTypes    # forgot the []
        body = json.dumps({u'policy': policy, u'exceptions': exceptions})
        path = u'/permissions/%s/%s' % (perm.path, path)
        if self.debug:
            self.Print(u'%s %s %s' % (path, body, action))
        status, content = self.call(u'PUT', path, body, action=action)
        return 0 if status == fishlib.STATUS.NO_CONTENT else status


def write_status(writes):
    if all(w == u'w' for w in writes):
        return u'w'
    else:
         return u'-' if all(w == u'-' for w in writes) else u'/'


def execute_ls_command(db, objs, tags, options, credentials, unixPaths=None):
    long_ = options.long or options.group or options.longest
    if len(tags) == 0:
        tags = [(u'/' if db.unixStyle else u'') + db.credentials.username]
    for tag in tags:
        fulltag = db.abs_tag_path(tag, inPref=True)
        if options.namespace or options.ns:
            if db.ns_exists(fulltag):
                if long_ or options.longer or options.longest:
                    nsResult = db.full_perms(fulltag[1:] + u'/',
                                             options.longer, options.group,
                                             options.longest)
                else:
                    nsResult = fulltag
                db.Print(nsResult)
            else:
                nsResult = u'Error status 404'
        else:
            nsResult = db.list_sorted_ns(fulltag[1:], long_=long_,
                                         recurse=options.recurse, prnt=True,
                                         longer=options.longer,
                                         longest=options.longest)
        tagExists = db.tag_exists(fulltag)
        if nsResult == 'Error status 404':
            if not tagExists:
                db.Print(u'%s not found' % fulltag)
        if tagExists:
            if long_ or options.longer or options.longest:
                db.Print(db.full_perms(fulltag[1:], options.longer,
                         options.group, options.longest))
            else:
                db.Print(tag)


def execute_rm_command(db, objs, tags, options, credentials, unixPaths=None):
    if len(tags) == 0:
        raise RemoveError('Remove what?')
    failures = []
    for tag in tags:
        nsDone = tagDone = False
        fulltag = db.abs_tag_path(tag, inPref=True)
        if db.ns_exists(fulltag):
            if options.recurse:
                nsResult = db.rm_r(fulltag[1:])
            else:
                nsResult = db.delete_namespace(fulltag)
            if nsResult:
                raise RemoveError(fishlib.human_status(nsResult, 
                                        db.abs_tag_path(tag, True, True),
                                        {412: '(probably not empty)'}))
            nsDone = True

        if db.tag_exists(fulltag):
            if options.force or options.recurse:
                db.untag_by_query(u'has %s' % fulltag[1:],
                                  [fulltag[1:]])
            else:
                ids = db.query(u'has %s' % fulltag[1:])
                if type(ids) in (int, long):
                    raise RemoveError(fishlib.human_status(ids))
                elif len(ids) > 0:
                    raise RemoveError(u'%s tagged with %s:\n%s'
                                      % (flags.Plural(len(ids),
                                                 'object').decode('UTF-8'),
                                         db.abs_tag_path(tag, True, True),
                                          u'  Use -f to force removal'))
            tagResult = db.delete_abstract_tag(fulltag)
            if tagResult:
                raise RemoveError(fishlib.human_status(tagResult,
                                         db.abs_tag_path(tag, True, True)))
            tagDone = True

        if not nsDone and not tagDone:
            failures.append(tag)

    if failures:
        if not options.force:
            raise RemoveError(u'No tag or namespace found for: %s'
                              % u' '.join(failures))


def execute_chmod_command(db, objs, args, options, credentials, unixPaths=None):
    db.warning('Use the perms command to change permissions.')
    return


def execute_perms_command(db, objs, args, options, credentials, unixPaths=None):
    if len(args) < 2:
        db.Print(u'Form: perms SPEC list of tags and namespaces')
        return
    spec = args[0]
    primitives = [u'write', u'read', u'control']
    if not (spec in [u'private', u'default', u'group', u'group-write',
                     u'group-read', u'lock', u'unlock'] + primitives):
        raise PermissionsError(u'perms must be followed by one of:\n%s'
                                % u', '.join(spec + primitives))
    isGroup = spec.startswith(u'group')
    if isGroup:
        group = args[1].split(u'+')
        if len(args) < 3:
            raise PermissionsError(
                    u'Group form: perms %s list+of+group+members list of tags '
                    u'and namespaces' % spec)

    if spec in primitives:
        errorText = (u'%s form: perms %s [open|closed]'
                     u'[except list+of+group+members list'
                     u'of tags and namespaces]' % (spec, spec))
        if len(args) < 3 or not args[1] in (u'open', u'closed'):
            raise PermissionsError(errorText)
        policy = args[1]
        exceptions = args[3].split(u'+') if args[2] == u'except' else []
        fullpaths = (db.abs_tag_path(t, inPref=True)
                     for t in args[2 + 2 * bool(exceptions):])
        if options.extravals:
            for v in options.extravals:
                assert v in ALL_NAMES
    else:
        fullpaths = (db.abs_tag_path(t, inPref=True)
                     for t in args[1 + isGroup:])
    for path in fullpaths:
        done = False
        owner = path.split(u'/')[1]
        permsToSet = ALL_NAMES
        for (exists, isTag) in ((db.tag_exists, True), (db.ns_exists, False)):
            if exists(path):
                inPerms = FluidinfoPerms(db, path, isTag=isTag,
                                         getFromFI=False)
                if spec == u'private':
                    inPerms.set_to_private()
                elif spec == u'default':
                    inPerms.set_to_default()
                elif spec == u'lock':
                    inPerms = FluidinfoPerms(db, path, isTag=isTag,
                                             getFromFI=True)
                    inPerms.lock()
                elif spec == u'unlock':
                    inPerms = FluidinfoPerms(db, path, isTag=isTag,
                                             getFromFI=True)
                    inPerms.unlock()
                elif isGroup:
                    inPerms = FluidinfoPerms(db, path, isTag=isTag,
                                             getFromFI=True)
                    if spec in (u'group', u'group-read'):
                         inPerms.set_group_readable(group)
                    if spec in (u'group', u'group-write'):
                         inPerms.set_group_writable(group)
                else:  # if spec in primitives:
                    if spec == u'control':
                        permsToSet = CONTROL_NAMES
                    elif spec == u'write':
                        permsToSet = WRITE_NAMES
                    else:
                        permsToSet = READ_NAMES
                    for name in permsToSet:
                        if hasattr(inPerms, name):
                            inPerms.__dict__[name].policy = policy
                            inPerms.__dict__[name].exceptions = exceptions
                inPerms.update_fluidinfo(db, permsToSet, options.force,
                                         restrict_to=options.extravals,
                                         verbose=options.verbose)
                done = True
        if not done:
            db.Print('No tag or namespace %s found' % db.abs_tag_path(path,
                                                                outPref=True))
