# coding: utf8
"""
Various dict-related special classes.

>>> mod = remvdodd([(1, 1), (2, 1.4), (1, 2)])
>>> mod
remvdodd(1: 1, 2: 1.4, 1: 2)
>>> mod['mod'] = mod
>>> mod
remvdodd(1: 1, 2: 1.4, 1: 2, 'mod': ...)
>>> mod.modmod = mod['mod']
>>> mod
remvdodd(1: 1, 2: 1.4, 1: 2, 'mod': ..., 'modmod': ...)
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
remvdodd(1: 1, 2: 1.4, 1: 2, 'mod': ..., 'modmod': ...)
>>> mod.mod is mod
True
>>> mod.update(u1='y')
>>> mod
remvdodd(1: 1, 2: 1.4, 1: 2, 'mod': ..., 'modmod': ..., 'u1': 'y')
>>> mod.update_inplace([(2, 2.6), (3, 3.6)])
>>> mod
remvdodd(1: 1, 2: 2.6, 1: 2, 'mod': ..., 'modmod': ..., 'u1': 'y', 3: 3.6)
>>> mod.pop(3)
3.6
>>> mod.update_replace([(1, -1)])
>>> mod
remvdodd(2: 2.6, 'mod': ..., 'modmod': ..., 'u1': 'y', 1: -1)
>>> del mod['modmod']
>>> mod
remvdodd(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1)
>>> mod._data
((2, 2.6), ('mod', remvdodd(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1)), ('u1', 'y'), (1, -1))
>>> mod._data is not mod.items(), mod._data == tuple(mod.items())
(True, True)
>>> mod[1] = 3
>>> mod
remvdodd(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1, 1: 3)
>>> mod.update(u1='n')
>>> mod
remvdodd(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')
>>> mod
remvdodd(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')
>>> mod.lists()
[(2, [2.6]), ('mod', [remvdodd(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')]), ('u1', ['y', 'n']), (1, [-1, 3])]
>>> mod.popitem()
('u1', 'n')
>>> mod.popitem(last=False)
(2, 2.6)
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
# not tested:  [iter](keys|values|lists), pop, fromkeys, eq
# ipy to doctest:  sed -r 's/^In[^:]+: />>> /; s/^Out[^:]+: //; /^ *$/ d'
# test to locals:  from pyaux import dicts; reload(dicts); from pyaux.dicts import *; exec '\n'.join(v[4:] for v in dicts.__doc__.split('\n\n')[-1].splitlines() if v.startswith('>>> '))

import six
import copy
import itertools
try:
    from UserDict import DictMixin
except ImportError:
    from collections import MutableMapping as DictMixin

from pyaux.base import uniq_g
from pyaux.base import dotdict


__all__ = (
    'ODReprMixin', 'OrderedDict',
    'MVOD',
    'hasattr_x',
    'dotdictx', 'defaultdictx', 'DefaultDotDictMixin',
    'dodd', 'mvdodd', 'remvdodd', 'redodd',
)


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
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join(
                '%r: %r' % (key, val)
                for key, val in self.items()))

    def __repr__(self, _repr_running={}, fn=__drepr__):
        """ Wrapped around __drepr__ that makes it possible to
        represent infinitely-recursive dictionaries of this type. """
        # NOTE: version variety; might be a _get_ident or something else.
        try:
            from thread import get_ident as _get_ident
        except ImportError:
            from threading import get_ident as _get_ident

        call_key = (id(self), _get_ident())
        if call_key in _repr_running:
            # TODO?: make a YAML-like naming & referencing?
            # (too complicated for a repr() though)
            return '...'
        _repr_running[call_key] = 1
        try:
            return fn(self)
        finally:
            del _repr_running[call_key]


# https://pypi.python.org/pypi/ordereddict
# or /usr/lib/python2.7/collections.py
# with modifications
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
        if self.__end is None:
            # XX: What was that, an inheritance support?
            # (the original OrderedDict code even does an AttributeError catch)
            self.clear()
        # self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        # sentinel node for doubly linked list
        end += [None, end, end]
        # key --> [key, prev, next]
        self.__map = {}
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next_ = self.__map.pop(key)
        prev[2] = next_
        next_[1] = prev

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
            key = next(reversed(self))
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

    # Will be provided in any version from whichever is available.
    iterkeys = getattr(DictMixin, 'iterkeys', None) or getattr(DictMixin, 'keys')
    itervalues = getattr(DictMixin, 'itervalues', None) or getattr(DictMixin, 'values')
    iteritems = getattr(DictMixin, 'iteritems', None) or getattr(DictMixin, 'items')

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
            for p, q in zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)  # not self == other


# ###
# MultiValueDict from django.utils.datastructures
# ###

class MultiValueDictKeyError(KeyError):
    pass


class MultiValueDict(dict):
    """
    A subclass of dictionary customized to handle multiple values for the
    same key.

    >>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
    >>> d['name']
    'Simon'
    >>> d.getlist('name')
    ['Adrian', 'Simon']
    >>> d.getlist('doesnotexist')
    []
    >>> d.getlist('doesnotexist', ['Adrian', 'Simon'])
    ['Adrian', 'Simon']
    >>> d.get('lastname', 'nonexistent')
    'nonexistent'
    >>> d.setlist('lastname', ['Holovaty', 'Willison'])

    This class exists to solve the irritating problem raised by cgi.parse_qs,
    which returns a list for every key, even though most Web forms submit
    single name-value pairs.
    """
    def __init__(self, key_to_list_mapping=()):
        super(MultiValueDict, self).__init__(key_to_list_mapping)

    @classmethod
    def make_from_items(cls, items):
        key_to_list_mapping = {}
        for key, val in items:
            key_to_list_mapping.setdefault(key, []).append(val)
        return cls(key_to_list_mapping)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__,
                             super(MultiValueDict, self).__repr__())

    def __getitem__(self, key):
        """
        Returns the last data value for this key, or [] if it's an empty list;
        raises KeyError if not found.
        """
        try:
            list_ = super(MultiValueDict, self).__getitem__(key)
        except KeyError:
            raise MultiValueDictKeyError(repr(key))
        try:
            return list_[-1]
        except IndexError:
            return []

    def __setitem__(self, key, value):
        super(MultiValueDict, self).__setitem__(key, [value])

    def __copy__(self):
        return self.__class__([
            (k, v[:])
            for k, v in self.lists()
        ])

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        result = self.__class__()
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo),
                             copy.deepcopy(value, memo))
        return result

    def __getstate__(self):
        obj_dict = self.__dict__.copy()
        obj_dict['_data'] = {k: self.getlist(k) for k in self}
        return obj_dict

    def __setstate__(self, obj_dict):
        data = obj_dict.pop('_data', {})
        for k, v in data.items():
            self.setlist(k, v)
        self.__dict__.update(obj_dict)

    def get(self, key, default=None):
        """
        Returns the last data value for the passed key. If key doesn't exist
        or value is an empty list, then default is returned.
        """
        try:
            val = self[key]
        except KeyError:
            return default
        if val == []:
            return default
        return val

    def getlist(self, key, default=None):
        """
        Returns the list of values for the passed key. If key doesn't exist,
        then a default value is returned.
        """
        try:
            return super(MultiValueDict, self).__getitem__(key)
        except KeyError:
            if default is None:
                return []
            return default

    def setlist(self, key, list_):
        super(MultiValueDict, self).__setitem__(key, list_)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
            # Do not return default here because __setitem__() may store
            # another value -- QueryDict.__setitem__() does. Look it up.
        return self[key]

    def setlistdefault(self, key, default_list=None):
        if key not in self:
            if default_list is None:
                default_list = []
            self.setlist(key, default_list)
            # Do not return default_list here because setlist() may store
            # another value -- QueryDict.setlist() does. Look it up.
        return self.getlist(key)

    def appendlist(self, key, value):
        """Appends an item to the internal list associated with key."""
        self.setlistdefault(key).append(value)

    def _iteritems(self):
        """
        Yields (key, value) pairs, where value is the last item in the list
        associated with the key.
        """
        for key in self:
            yield key, self[key]

    def _iterlists(self):
        """Yields (key, list) pairs."""
        return six.iteritems(super(MultiValueDict, self))

    def _itervalues(self):
        """Yield the last value on every key list."""
        for key in self:
            yield self[key]

    if six.PY3:
        items = _iteritems
        lists = _iterlists
        values = _itervalues
    else:
        iteritems = _iteritems
        iterlists = _iterlists
        itervalues = _itervalues

        def items(self):
            return list(self.iteritems())

        def lists(self):
            return list(self.iterlists())

        def values(self):
            return list(self.itervalues())

    def copy(self):
        """Returns a shallow copy of this object."""
        return copy.copy(self)

    def update(self, *args, **kwargs):
        """
        update() extends rather than replaces existing key lists.
        Also accepts keyword args.
        """
        if len(args) > 1:
            raise TypeError("update expected at most 1 arguments, got %d" % len(args))
        if args:
            other_dict = args[0]
            if isinstance(other_dict, MultiValueDict):
                for key, value_list in other_dict.lists():
                    self.setlistdefault(key).extend(value_list)
            else:
                try:
                    for key, value in other_dict.items():
                        self.setlistdefault(key).append(value)
                except TypeError:
                    raise ValueError("MultiValueDict.update() takes either a MultiValueDict or dictionary")
        for key, value in six.iteritems(kwargs):
            self.setlistdefault(key).append(value)

    def dict(self):
        """
        Returns current object as a dict with singular values.
        """
        return {key: self[key] for key in self}


# ######
# Other stuff
# ######


class MVOD(ODReprMixin, dict):
    """ MultiValuedOrderedDict: A not-very-optimized (most write operations
    are at least O(N) with the re-hashing cost) somewhat-trivial verison.
    Stores a tuple of pairs as the actual data (in `_data`), uses it for
    iteration, caches dict(data) as self for optimized key-access. """
    # TODO?: support unhashable keys (by skipping them in the cache)
    # TODO?: make the setitem behaviour configurable per instance

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
                raise ValueError((
                    "dictionary update sequence element #%d has"
                    " length %r; 2 is required") % (i, lv))
            key, val = item
            res.append((key, val))
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
            arg = getattr(arg, 'iteritems', arg.items)()
        if kwds:
            # Append the keywords to the other stuff
            arg = itertools.chain(arg, kwds.items())
            # raise TypeError('initializing an ordered dict from keywords is not recommended')
        if preprocess:
            arg = self._preprocess_data(arg)  ## NOTE: iterates over it and makes a tuple.
        return arg

    def update_append(self, *args, **kwds):
        """ ...
        (the usual equivalent of dict.update)

        WARNING: appends the data; thus, multiple `update`s will cause
        it to grow; thus, might need to be `.deduplicate`d.
        """
        data_new = self._process_upddata(args, kwds)
        # XXXXX: A dilemma:
        #  * If self._data is a list, then it can be mutated by the
        #    user without updating the cache
        #  * If self._data is a tuple, then it has to be re-created for
        #    any change (current version).
        #  * If self._data is a custom proxy to a list... dunno. TODO?
        #    (similar to the django.utils.datastructures.ImmutableList
        #    except not tuple-derived)
        self._data_checked = self._data + data_new

    def update_replace(self, *args, **kwds):
        """ A closer equivalent of dict.update that removes all the previous
        occurrences of the keys that are updated and appends the new ones to
        the end. The new keys still can occur multiple times. """
        data_new = self._process_upddata(args, kwds)
        keys = set(key for key, val in data_new)
        pre_data = tuple((key, val) for key, val in self._data
                         if key not in keys)
        self._data_checked = pre_data + data_new

    def update_inplace(self, *args, **kwds):
        """ A closer equivalent of OrderedDict.update that replaces the
        previous occurrences at the point of first occurrence.  Does not yet
        support multiple items handling in the updated keys. """
        data_new = self._process_upddata(args, kwds)
        news = dict(*args, **kwds)
        # XXXX/TODO: To update with multiple values will have to do `MVOD(*args,
        #   **kwds).lists()`, and (configurably) pop either each item from the
        #   list when it occurs or just one item each time.
        pre_data = tuple((key, news.pop(key, val))
                         for key, val in self._data)
        # Add the non-previously-existing ones.
        data_new = [(key, val) for key, val in data_new if key in news]
        self._data_checked = pre_data + tuple(data_new)

    update = update_append

    def __delitem__(self, key):
        self._data_checked = tuple((k, v) for k, v in self._data if k != key)

    # A set of properties to set the data with or without checking it
    # for validity.
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
        # just a check that can be optimized out.
        assert isinstance(val, tuple)
        self.__data = val
        self._update_cache()

    # def __getitem__:  inherited from `dict`

    def __setitem__(self, key, value):
        return self.update(((key, value),))
        # self._data_checked = self._data + ((key, value),)

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
        data_pre = uniq_g(reversed(self._data), key=lambda item: item[0])
        data_pre = list(data_pre)
        self._data_checked = tuple(reversed(data_pre))

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

    copy = __copy__  # XXX: re-check.

    # XXX/TODO: PY3.  (see django.utils.datastructures.MultiValueDict)

    def iteritems(self):
        # XXXX: no dict-changed-while-iterating handling.
        return iter(self._data)

    def iterlists(self):
        """ MultiValueDict-like (django) method. Not very optimal. """
        # XXX: no dict-changed-while-iterating handling.
        order = []
        lists = {}
        for key, val in self.iteritems():
            if key not in lists:
                lst = lists[key] = [val]
                order.append((key, lst))
            else:
                lists[key].append(val)
        for key, lst in order:
            yield key, lst  # lists[k]

    def getlist(self, key, default=None):
        values = [item_val for item_key, item_val in self.iteritems() if item_key == key]
        if values:
            return values
        if default is None:
            return []
        return default

    def iterkeys(self):
        for key, _ in self.iteritems():
            yield key

    def __iter__(self):
        return self.iterkeys()

    def __reversed__(self):
        for key, val in reversed(self._data):
            yield key

    # Copypaste from UserDict.DictMixin
    def itervalues(self):
        for _, val in self.iteritems():
            yield val

    def values(self):
        return [val for _, val in self.iteritems()]

    def items(self):
        return list(self.iteritems())

    def keys(self):
        return [k for k, _ in self.iteritems()]

    def lists(self, **kwa):
        return list(self.iterlists(**kwa))

    # Bit more copypaste from UserDict.DictMixin (because most other
    # methods from it are unnecessary)
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

        WARN: `mvod == od` and `od == mvod` might have different
        results (because OD doesn't handle MVODs).
        """
        if isinstance(other, (MVOD, OrderedDict)):
            # In the end it comes down to items.
            return dict.__eq__(self, other) and (self.items() == other.items())
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # __nonzero__ does not need overriding as dict handles that.

    # XXX: some other methods?


# NOTE: A simpler form is available in the `base`
class dotdictx(dict):
    """ A dict subclass with items also available over
    attributes. Skips the attributes starting with '_' (for
    mixinability) """

    def __getattr__(self, name):
        if name.startswith('__'):  # NOTE: two underscores.
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
        except KeyError:
            if self._default is not None:
                val = self._default()
                self[name] = val
                return val
            raise


def hasattr_x(obj, name):
    """ A safer `hasattr` that only checks for simple attributes
    rather than properties or __getattr__ results. """
    try:
        object.__getattribute__(obj, name)
    except AttributeError:
        return False
    return True


class DefaultDotDictMixin(dotdict, defaultdictx):
    """ A class that tries to combine DefaultDict and dotdict without causing
    too much of a mess. NOTE: skips _attributes on setattr and __attributes on
    getattr. """

    def __getattr__(self, name):
        # Mostly necessary to avoid `defaultdict`ing some special
        # methods like __getstate__ that weren't defined on the class.
        # (could disable the defaultdict'ing for that, though)
        if name.startswith('__'):  # NOTE: two underscores.
            return self.__getattribute__(name)  # Basically `raise AttributeError`.
        return super(DefaultDotDictMixin, self).__getattr__(name)  # __getitem__

    def __setattr__(self, name, value):
        # if name in self.__dict__:
        # if hasattr_x(self, name):
        #     self.__dict__[name] = value
        #     return

        # Mostly necessary for class code that sets attributes like
        # '_OrderedDict__end' (or the defaultdictx._default)
        if name.startswith('_'):
            # Basically `object.__setattr__(…)`
            # WARN: querying `d._attr` still sets it to the
            # default. Not necessarily problematic though.
            return dict.__setattr__(self, name, value)

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


# TODO: test... things...

# TODO?: Add some other sort of multivaluedness
# (django.utils.datastructures.MultiValueDict).  (and maybe add a
# separate class compatible with id and/or the django.http.QueryDict
# or something)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
