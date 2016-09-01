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
>>> list(mod.lists())
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

from __future__ import print_function

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
            # Does anyone know the reason for this behaviour and ways
            # there could happen to be an empty list?
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


def _is_MultiValueDict(val, deep=False):
    """
    Check the object for MultiValueDict face (to support e.g. the
    django's one). Does not include MVODs.
    """
    if isinstance(val, MultiValueDict):
        return True
    # The interesting internal-data access method 'lists':
    if not hasattr(val, 'lists'):
        return False
    if deep:
        return any(
            cls.__name__ == 'MultiValueDict'
            for cls in val.__class__.__mro__)
    else:
        return isinstance(val, dict)


def _lists_group(items):
    """ items -> key_to_list_mapping """
    # Pretty much `pyaux.base.group()`
    result = {}
    for key, val in items:
        try:
            list_ = result[key]
        except KeyError:
            list_ = [val]
            result[key] = list_
        else:
            list_.append(val)
    return result


def _lists_group_ordered(items):
    """ items -> key_to_list_mapping keeping some order """
    order = []
    lists = {}
    for key, val in items:
        try:
            list_ = lists[key]
        except KeyError:
            lst = [val]
            lists[key] = lst
            order.append((key, lst))
        else:
            list_.append(val)
    return iter(order)


def _lists_ungroup(key_to_list_mapping):
    """" key_to_list_mapping -> items """
    if isinstance(key_to_list_mapping, dict):
        key_to_list_mapping = key_to_list_mapping.items()
    result = [
        (key, val)
        for key, vals in key_to_list_mapping
        for val in vals]
    return result


class MVOD_Common(ODReprMixin, object):

    _data_internal = ()

    # Conveniences

    _lists_group = staticmethod(_lists_group)
    _lists_group_ordered = staticmethod(_lists_group_ordered)
    _lists_ungroup = staticmethod(_lists_ungroup)

    def _preprocess_data(self, data):
        """
        Make sure the passed data is a list of pairs; returns a tuple
        with the pair-tuples.
        """
        res = []
        for i, item in enumerate(data):
            lv = len(item)  # Paranoidally avoid calling it twice.
            if lv != 2:
                raise ValueError((
                    "dictionary update sequence element #%d has"
                    " length %r; 2 is required") % (i, lv))
            key, val = item
            res.append((key, val))
        return tuple(res)

    def _process_upddata(self, args, kwds, preprocess=True, strict=False):
        """
        Convert some function call args into list of key-value pairs
        (same as `dict(*args, **kwds)` does).  Returns a tuple with
        pair-tuples.
        """
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        arg = args[0] if args else []
        if isinstance(arg, MVOD):  # support init / update from antother MVOD
            arg = arg._data
        elif _is_MultiValueDict(arg):  # Other `MultiValueDict`s
            arg = self._lists_ungroup(arg.lists())
        elif isinstance(arg, dict):
            arg = getattr(arg, 'iteritems', arg.items)()
        if kwds:
            if strict:
                raise TypeError('initializing an ordered dict from keywords is not recommended')
            # Append the keywords to the other stuff
            arg = itertools.chain(arg, kwds.items())
        if preprocess:
            arg = self._preprocess_data(arg)  ## NOTE: iterates over it and makes a tuple.
        return arg

    # A set of properties to set the data with or without checking it
    # for validity.

    @property
    def _data(self):
        return self._data_internal

    @_data.setter
    def _data(self, val):
        self._data_internal = self._preprocess_data(val)
        self._update_cache()

    @property
    def _data_checked(self):
        return self._data_internal

    @_data_checked.setter
    def _data_checked(self, val):
        assert isinstance(val, tuple)
        self._data_internal = val
        self._update_cache()

    def _update_cache(self):
        raise NotImplementedError

    # Commonly usable methods

    def clear(self):
        # does `self._update_cache`:
        self._data_checked = ()

    def __copy__(self):
        return self.__class__(self._data)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        result = self.__class__()
        memo[id(self)] = result
        result._data_checked = copy.deepcopy(self._data, memo)
        return result

    copy = __copy__  # XXX: re-check.

    # TODO?: __getstate__, __setstate__; probably not useful.

    def _iteritems(self):
        # WARN: no dict-changed-while-iterating handling. In practice,
        # iteration is always over a copy (since self._data is a tuple).
        for item in self._data:
            yield item

    def __reversed__(self):
        # See the `_iteritems` dict-changed-while-iterating note.
        for key, _ in reversed(self._data):
            yield key

    def _iterlists(self, ordered=True):
        """ MultiValueDict-like (django) method. Not very optimal. """
        # See the `_iteritems` dict-changed-while-iterating note.
        pre_func = self._lists_group_ordered if ordered else self._lists_group
        for key, lst in pre_func(self._data):
            yield key, lst

    def _itervalues(self):
        for _, val in self._iteritems():
            yield val

    def _iterkeys(self):
        # Supports the duplicates.
        for key, _ in self._iteritems():
            yield key

    def __iter__(self):
        return self._iterkeys()

    # # six:

    if six.PY3:

        def items(self, *args, **kwargs):
            return self._iteritems(*args, **kwargs)

        def lists(self, *args, **kwargs):
            return self._iterlists(*args, **kwargs)

        def values(self, *args, **kwargs):
            return self._itervalues(*args, **kwargs)

        def keys(self, *args, **kwargs):
            return self._iterkeys(*args, **kwargs)

    else:

        def iteritems(self, *args, **kwargs):
            return self._iteritems(*args, **kwargs)

        def iterlists(self, *args, **kwargs):
            return self._iterlists(*args, **kwargs)

        def itervalues(self, *args, **kwargs):
            return self._itervalues(*args, **kwargs)

        def iterkeys(self, *args, **kwargs):
            return self._iterkeys(*args, **kwargs)

        def items(self, *args, **kwargs):
            return list(self.iteritems(*args, **kwargs))

        def lists(self, *args, **kwargs):
            return list(self.iterlists(*args, **kwargs))

        def values(self, *args, **kwargs):
            return list(self.itervalues(*args, **kwargs))

        def keys(self, *args, **kwargs):
            return list(self.iterkeys(*args, **kwargs))

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
        if isinstance(other, (MVOD_Common, OrderedDict)):
            # Quicker pre-check:
            if not dict.__eq__(self, other):
                return False
            # In the end it comes down to items.
            if self._data == tuple(other.items()):
                return True
            return False
        elif _is_MultiValueDict(other):
            return self._data == tuple(self._lists_ungroup(other.lists()))
        else:
            return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # __nonzero__ does not need overriding as dict handles that.

    # XXX: some other methods?


class MVOD(MVOD_Common, dict):
    """ MultiValuedOrderedDict: A not-very-optimized (most write operations
    are at least O(N) with the re-hashing cost) somewhat-trivial verison.
    Stores a tuple of pairs as the actual data (in `_data`), uses it for
    iteration, caches dict(data) as self for optimized key-access. """
    # TODO?: support unhashable keys (by skipping them in the cache)
    # TODO?: make the setitem behaviour configurable per instance

    def __init__(self, *args, **kwds):
        self.update(*args, **kwds)

    def _update_cache(self):
        dict.clear(self)
        dict.update(self, self._data)

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
        """
        A closer equivalent of dict.update that removes all the
        previous occurrences of the keys that are updated and appends
        the new ones to the end. The new keys still can occur multiple
        times.
        """
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

    def getlist(self, key, default=None):
        values = [
            item_val for item_key, item_val in self._iteritems()
            if item_key == key]
        if values:
            return values
        if default is None:
            return []
        return default


class MVLOD(MVOD_Common, MultiValueDict):
    """
    A Multi-Value Ordered Dict with slow modification and fast
    value-list access.

    Implemented as MultiValueDict that stores the original/intended
    items list.

    NOTE: instantiated from `items`, not `key_to_list_mapping`. Use
    `make_from_key_to_list_mapping` for the MultiValueDict()'s
    behaviour.
    """

    _optimised = True

    def __init__(self, *args, **kwds):
        self.update(*args, **kwds)

    @classmethod
    def make_from_key_to_list_mapping(cls, key_to_list_mapping=()):
        return cls(cls._lists_ungroup(key_to_list_mapping))

    @classmethod
    def make_from_items(cls, items):
        return cls(items)

    # Core logic

    def _update_cache(self):
        dict.clear(self)
        dict.update(self, self._lists_group(self._data))

    def update_append(self, *args, **kwds):
        """ ...
        (the usual equivalent of dict.update)

        WARNING: appends the data; thus, multiple `update`s will cause
        it to grow; thus, might need to be `.deduplicate`d.
        """
        data_new = self._process_upddata(args, kwds)
        data_result = self._data + data_new
        if not self._optimised:
            self._data_checked = data_result
        else:
            self._data_internal = data_result
            ktlm_new = self._lists_group(data_new)
            for key, list_ in ktlm_new.items():
                try:
                    target_list = dict.__getitem__(self, key)
                except KeyError:
                    dict.__setitem__(self, key, list_)
                else:
                    target_list.extend(list_)

    def update_replace(self, *args, **kwds):
        """
        A closer equivalent of dict.update that removes all the
        previous occurrences of the keys that are updated and appends
        the new ones to the end. The new keys still can occur multiple
        times.
        """
        data_new = self._process_upddata(args, kwds)
        keys = set(key for key, val in data_new)
        data_kept = tuple(
            (key, val) for key, val in self._data
            if key not in keys)
        data_result = data_kept + data_new
        if not self._optimised:
            self._data_checked = data_result
        else:  # Optimised cache-dict mangle
            self._data_internal = data_result
            ktlm_new = self._lists_group(data_new)
            # # Should be unnecessary:
            # for key in keys:
            #     self.pop(key, None)
            for key, list_ in ktlm_new.items():
                dict.__setitem__(self, key, list_)
                # super(MVLOD, self).setlist(key, list_)

    def setlist(self, key, list_):
        data_new = self._lists_ungroup([(key, list_)])
        self.update_replace(data_new)

    def appendlist(self, key, value):
        self.update_append([(key, value)])

    def __delitem__(self, key):
        data_result = tuple(
            (item_key, item_val) for item_key, item_val in self._data
            if item_key != key)
        # See if we removed nothing.
        if len(data_result) == len(self._data):
            raise KeyError(key)
        if not self._optimised:
            self._data_checked = data_result
        else:
            self._data_internal = data_result
            try:
                dict.__delitem__(self, key)
            except KeyError:
                raise Exception("The key should've been there", self, key)

    # The defaults (for setitem, instantiation)

    update = update_append

    def __setitem__(self, key, value):
        self.update([(key, value)])

    # Other optimisations

    def _iterlists(self, ordered=False):
        if ordered:
            return super(MVLOD, self)._iterlists(ordered=ordered)
        if six.PY3:
            return dict.items(self)
        else:
            return dict.iteritems(self)


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
