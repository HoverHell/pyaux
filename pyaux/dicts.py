# coding: utf8
"""
Various dict-related special classes.

>>> mod = remvdodd([(1, 1), (2, 1.4), (1, 2)])
>>> mod
remvdodd(1: 1, 2: 1.3999999999999999, 1: 2)
>>> mod['mod'] = mod
>>> mod
remvdodd(1: 1, 2: 1.3999999999999999, 1: 2, 'mod': ...)
>>> mod.modmod = mod['mod']
>>> mod
remvdodd(1: 1, 2: 1.3999999999999999, 1: 2, 'mod': ..., 'modmod': ...)
>>> import copy
>>> mc = copy.deepcopy(mod)
>>> mod.mod is mod.mod, mc.mod is not mod.mod
(True, True)
>>> mcc = mod.copy()
>>> mcc.mod is mod.mod
True
>>> mcc.clear()
>>> mcc
remvdodd()
>>> mod
remvdodd(1: 1, 2: 1.3999999999999999, 1: 2, 'mod': ..., 'modmod': ...)
>>> mod.mod is mod
True
>>> mod.update(u1='y')
>>> mod
remvdodd(1: 1, 2: 1.3999999999999999, 1: 2, 'mod': ..., 'modmod': ..., 'u1': 'y')
>>> mod.update_inplace([(2, 2.6), (3, 3.6)])
>>> mod
remvdodd(1: 1, 2: 2.6000000000000001, 1: 2, 'mod': ..., 'modmod': ..., 'u1': 'y', 3: 3.6000000000000001)
>>> mod.pop(3)
3.6000000000000001
>>> mod.update_replace([(1, -1)])
>>> mod
remvdodd(2: 2.6000000000000001, 'mod': ..., 'modmod': ..., 'u1': 'y', 1: -1)
>>> del mod['modmod']
>>> mod
remvdodd(2: 2.6000000000000001, 'mod': ..., 'u1': 'y', 1: -1)
>>> mod._data
((2, 2.6000000000000001), ('mod', remvdodd(2: 2.6000000000000001, 'mod': ..., 'u1': 'y', 1: -1)), ('u1', 'y'), (1, -1))
>>> mod._data is not mod.items(), mod._data == tuple(mod.items())
(True, True)
>>> mod[1] = 3
>>> mod
remvdodd(2: 2.6000000000000001, 'mod': ..., 'u1': 'y', 1: -1, 1: 3)
>>> mod.update(u1='n')
>>> mod
remvdodd(2: 2.6000000000000001, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')
>>> mod
remvdodd(2: 2.6000000000000001, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')
>>> mod.lists()
[(2, [2.6000000000000001]), ('mod', [remvdodd(2: 2.6000000000000001, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')]), ('u1', ['y', 'n']), (1, [-1, 3])]
>>> mod.popitem()
('u1', 'n')
>>> mod.popitem(last=False)
(2, 2.6000000000000001)
>>> mod
remvdodd('mod': ..., 'u1': 'y', 1: -1, 1: 3)
>>> mod.deduplicate()
>>> mod
remvdodd('mod': ..., 'u1': 'y', 1: 3)
>>> mod.u1 = 'yy'
>>> mod
remvdodd('mod': ..., 'u1': 'y', 1: 3, 'u1': 'yy')
>>> mod.deduplicate(how='first')
>>> mod
remvdodd('mod': ..., 'u1': 'y', 1: 3)
>>> list(reversed(mod))
[1, 'u1', 'mod']
>>> mod
remvdodd('mod': ..., 'u1': 'y', 1: 3)
>>> mod.setdefault(5, 2)
2
>>> mod
remvdodd('mod': ..., 'u1': 'y', 1: 3, 5: 2)
>>> mod.setdefault(5, 1)
2
>>> mod
remvdodd('mod': ..., 'u1': 'y', 1: 3, 5: 2)
"""
## not tested:  [iter](keys|values|lists), pop, fromkeys, eq
## ipy to doctest:  sed -r 's/^In[^:]+: />>> /; s/^Out[^:]+: //; /^ *$/ d'
## test to locals:  from sbdutils import dicts; reload(dicts); from sbdutils.dicts import *; exec '\n'.join(v[4:] for v in dicts.__doc__.split('\n\n')[-1].splitlines() if v.startswith('>>> '))

import copy
import itertools

from .base import uniq_g
from .base import dotdict


class ODReprMixin(object):
    """ A mixin for ordered dicts that provides two different representations
    and a wrapper for handling self-referencing structures. """
    def __irepr__(self):
        """ The usual (default) representation of an ordereddict """
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())
    def __drepr__(self):
        """ A slightly more visual-oriented representation of an ordereddict """
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%s)' % (self.__class__.__name__, ', '.join('%r: %r' % (k, v) for k, v in self.iteritems()))
    def __repr__(self, _repr_running={}, fn=__drepr__):
        """ Wrapped around __drepr__ that makes it possible to represent infinitely-recursive dictionaries of this type. """
        from thread import get_ident as _get_ident  ## NOTE: version variety; might be a _get_ident or something else.
        call_key = (id(self), _get_ident())
        if call_key in _repr_running:
            return '...'  ## XXXX: make a YAML-like naming & referencing?  (might be too complicated for a repr() though)
        _repr_running[call_key] = 1
        try:
            return fn(self)
        finally:
            del _repr_running[call_key]



# https://pypi.python.org/pypi/ordereddict
# or /usr/lib/python2.7/collections.py
# with modifications
from UserDict import DictMixin
class OrderedDict(dict, ODReprMixin, DictMixin):

    __end = None
    __map = None
    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        # try:
        #     self.__end
        # except AttributeError:
        #     self.clear()
        if self.__end is None:  ## XX: What was that, an inheritance support? (the original OrderedDict code even does an AttributeError catch)
            self.clear()
        # self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for p, q in  zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other


#######
## Other stuff
#######
class MVOD(ODReprMixin, dict):
    """ MultiValuedOrderedDict: A not-very-optimized (most write operations
    are at least O(N) with the re-hashing cost) somewhat-trivial verison.
    Stores a tuple of pairs as the actual data (in `_data`), uses it for
    iteration, caches dict(data) as self for optimized key-access. """
    ## TODO?: support unhashable keys (by skipping them in the cache)
    ## TODO?: make the setitem behaviour configurable per instance
    __data = ()
    def __init__(self, *args, **kwds):
        self.update(*args, **kwds)

    def clear(self):
        self._data_checked = ()  # still does the _update_cache (over property)
    def _update_cache(self):
        dict.clear(self)
        dict.update(self, self.__data)
    def _preprocess_data(self, data):
        """ Make sure the passed data is a list of pairs; returns a tuple with
        the pair-tuples. """
        res = []
        for i, item in enumerate(data):
            lv = len(item)  ## Paranoidally avoid calling it twice.
            if lv != 2:
                raise ValueError("dictionary update sequence element #%d has length %r; 2 is required" % (i, lv))
            k, v = item
            res.append((k, v))
        return tuple(res)
    def _process_upddata(self, args, kwds, preprocess=True):
        """ Convert some function call args into list of key-value pairs (same
        as `dict(*args, **kwds)` does).
        Returns a tuple with pair-tuples.  """
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        arg = args[0] if args else []
        if isinstance(arg, MVOD):  ## support init / update from antother MVOD
            arg = arg._data
        elif isinstance(arg, dict):
            arg = arg.iteritems()
        if kwds:
            ## Append the keywords to the other stuff
            arg = itertools.chain(arg, kwds.iteritems())
            #raise TypeError('initializing an ordered dict from keywords is not recommended')
        if preprocess:
            arg = self._preprocess_data(arg)  ## NOTE: iterates over it and makes a tuple.
        return arg

    def update_append(self, *args, **kwds):
        """ ...
        (the usual equivalent of dict.update)
        WARNING: appends the data (thus, multiple `update`s will cause it to grow; thus, might need to be `.deduplicate`d)
        """
        data_new = self._process_upddata(args, kwds)
        ## XXXXX: A dilemma:
        ##   If self._data is a list, then it can be mutated by the user without updating the cache
        ##   If self._data is a tuple, then it has to be re-created for any change (current version).
        ##   If self._data is a custom proxy to a list... Dunno.  TODO?
        ##     (similar to the django.utils.datastructures.ImmutableList except not tuple-derived)
        self._data_checked = self._data + data_new
    def update_replace(self, *args, **kwds):
        """ A closer equivalent of dict.update that removes all the previous
        occurrences of the keys that are updated and appends the new ones to
        the end. The new keys still can occur multiple times. """
        data_new = self._process_upddata(args, kwds)
        keys = set(k for k, v in data_new)
        self._data_checked = tuple((k, v) for k, v in self._data if k not in keys) + data_new
    def update_inplace(self, *args, **kwds):
        """ A closer equivalent of OrderedDict.update that replaces the
        previous occurrences at the point of first occurrence.  Does not yet
        support multiple items handling in the updated keys. """
        data_new = self._process_upddata(args, kwds)
        news = dict(*args, **kwds)
        ## XXXX/TODO: To update with multiple values will have to do `MVOD(*args,
        ##   **kwds).lists()`, and (configurably) pop either each item from the
        ##   list when it occurs or just one item each time.
        pre_data = tuple((k, news.pop(k, v)) for k, v in self._data)
        data_new = [(k, v) for k, v in data_new if k in news]  ## Add the non-previously-existing ones.
        self._data_checked = pre_data + tuple(data_new)

    update = update_append

    def __delitem__(self, key):
        self._data_checked = tuple((k, v) for k, v in self._data if k != key)

    ## A set of properties to set the data with or without checking it for validity.
    @property
    def _data(self):
        return self.__data
    @_data.setter
    def _data(self, val):
        self.__data = self._preprocess_data(val)
        self._update_cache()
    @property
    def _data_checked(self):
        return self.__data
    @_data_checked.setter
    def _data_checked(self, val):
        assert isinstance(val, tuple)  ## just a check that can be optimized out.
        self.__data = val
        self._update_cache()

    #def __getitem__:  inherited from `dict`
    def __setitem__(self, key, value):
        return self.update(((key, value),))
        #self._data_checked = self._data + ((key, value),)

    def deduplicate(self, how='last'):
        """ ...
        NOTE: this method is equivalent to deduplicate_last by default. """
        if how == 'first':
            pass
        elif how == 'last':
            return self.deduplicate_last()
        else:
            raise ValueError("Unknown deduplication `how`: %r" % (how,))
        self._data_checked = tuple(uniq_g(self._data, key=lambda item: item[0]))
    def deduplicate_last(self):
        self._data_checked = tuple(reversed(list(uniq_g(reversed(self._data), key=lambda item: item[0]))))
    def deduplicated(self, **kwa):
        cp = self.copy()
        cp.deduplicate(**kwa)
        return cp

    def __copy__(self):
        return self.__class__(self._data)
    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        result = self.__class__()
        memo[id(self)] = result
        result._data_checked = copy.deepcopy(self.__data, memo)
        return result
    copy = __copy__  ## XXXXX: re-check.

    ## XXXX/TODO: PY3.  (see django.utils.datastructures.MultiValueDict)
    def iteritems(self):
        return iter(self._data)  ## XXXX: no dict-changed-while-iterating handling.
    def iterlists(self):
        """ MultiValueDict-like (django) method. Not very optimal. """
        ## XXXX: no dict-changed-while-iterating handling.
        order = []
        lists = {}
        for k, v in self.iteritems():
            if k not in lists:
                l = lists[k] = [v]
                order.append((k, l))
            else:
                lists[k].append(v)
        for k, l in order:
            yield k, l  #lists[k]
    def iterkeys(self):
        for k, _ in self.iteritems():
            yield k
    def __iter__(self):
        return self.iterkeys()
    def __reversed__(self):
        for k, v in reversed(self._data):
            yield k

    ## Copypaste from UserDict.DictMixin
    def itervalues(self):
        for _, v in self.iteritems():
            yield v
    def values(self):
        return [v for _, v in self.iteritems()]
    def items(self):
        return list(self.iteritems())

    def keys(self):
        return [k for k, _ in self.iteritems()]
    def lists(self, **kwa):
        return list(self.iterlists(**kwa))


    ## Bit more copypaste from UserDict.DictMixin (because most other methods from it are unnecessary)
    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop expected at most 2 arguments, got %r" % (1 + len(args),))
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            raise
        del self[key]
        return value
    def setdefault(self, key, failobj=None):
        if key not in self:
            self[key] = failobj
        return self[key]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        data = self._data
        if last:
            item = data[-1]
            self._data_checked = data[:-1]
        else:
            item = data[0]
            self._data_checked = data[1:]
        return item
    @classmethod
    def fromkeys(cls, iterable, value=None):
        return cls([(k, value) for k in iterable])
    def __eq__(self, other):
        """ ...
        NOTE: `mvod == od` and `od == mvod` might have different results (because OD doesn't handle MVODs).
        """
        if isinstance(other, (MVOD, OrderedDict)):
            return dict.__eq__(self, other) and (self.items() == other.items())  ## In the end it comes to items.
        return dict.__eq__(self, other)
    def __ne__(self, other):
        return not self == other
    # __nonzero__ does not need overriding as dict handles that.
    ## XXX: some other methods?


## A simpler form is available in the sbdutils itself
class dotdictx(dict):
    """ A dict subclass with items also available over attributes. Skips the
    attributes starting with '_' (for mixinability) """
    def __getattr__(self, name):
        if name.startswith('__'):  ## NOTE: two underscores.
            return super(dotdictx, self).__getattr__(name)
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(e)
    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super(dotdictx, self).__setattr__(name, value)
        self[name] = value


class defaultdictx(dict):
    """ A purepython & simplified `defaultdict` version that doesn't change
    the interface except for the `_default` attribute (with the
    default_factory) """
    _default = None
    def __getitem__(self, name):
        try:
            return super(defaultdictx, self).__getitem__(name)
        except KeyError as e:
            if self._default is not None:
                val = self._default()
                self[name] = val
                return val
            raise
def hasattr_x(o, name):
    try:
        object.__getattribute__(o, name)
    except AttributeError:
        return False
    return True
class DefaultDotDictMixin(dotdict, defaultdictx):
    """ A class that tries to combine DefaultDict and dotdict without causing
    too much of a mess. NOTE: skips _attributes on setattr and __attributes on
    getattr. """
    def __getattr__(self, name):
        ## Mostly necessary to avoid `defaultdict`ing some special methods
        ##   like __getstate__ that weren't defined on the class.
        ## (could disable the defaultdict'ing for that, though)
        if name.startswith('__'):  ## NOTE: two underscores.
            return self.__getattribute__(name)  ## Basically `raise AttributeError`.
        return super(DefaultDotDictMixin, self).__getattr__(name)  # __getitem__
    def __setattr__(self, name, value):
        # if name in self.__dict__:
        # if hasattr_x(self, name):
        #     self.__dict__[name] = value
        #     return
        ## Mostly necessary for class code that sets attributes like '_OrderedDict__end' (or the defaultdictx._default)
        if name.startswith('_'):
            ## XX: querying `d._attr` still sets it to the default. Not necessarily problematic though.
            return dict.__setattr__(self, name, value)  ## Basically `object.__setattr__(…)`
        return super(DefaultDotDictMixin, self).__setattr__(name, value)  # __setitem__


class dodd(DefaultDotDictMixin, OrderedDict):
    """ DotOrderedDefaultDict. Set `_default` attribute on it to a factory to
    use it as a defaultdict. NOTE: ignores attributes starting with '_' """
    pass
class mvdodd(DefaultDotDictMixin, MVOD):
    pass
class redodd(dodd):
    """ Recursive dodd (by default) """
redodd._default = redodd
class remvdodd(mvdodd):
    """ ... """
remvdodd._default = remvdodd
## TODO: test... things...

## TODO?: Add some other sort of multivaluedness
##   (django.utils.datastructures.MultiValueDict).  (and maybe add a separate
##   class compatible with id and/or the django.http.QueryDict or something)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
