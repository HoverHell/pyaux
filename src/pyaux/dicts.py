"""
Various dict-related special classes.

>>> mod = REMVDODD([(1, 1), (2, 1.4), (1, 2)])
>>> mod
REMVDODD(1: 1, 2: 1.4, 1: 2)
>>> mod["mod"] = mod
>>> mod
REMVDODD(1: 1, 2: 1.4, 1: 2, 'mod': ...)
>>> mod.modmod = mod["mod"]
>>> mod
REMVDODD(1: 1, 2: 1.4, 1: 2, 'mod': ..., 'modmod': ...)
>>> import copy
>>> mc = copy.deepcopy(mod)
>>> mod.mod is mod.mod, mc.mod is not mod.mod
(True, True)
>>> mcc = mod.copy()
>>> mcc.mod is mod.mod
True
>>> mcc.clear()
>>> mcc
REMVDODD()
>>> mod
REMVDODD(1: 1, 2: 1.4, 1: 2, 'mod': ..., 'modmod': ...)
>>> mod.mod is mod
True
>>> mod.update(u1="y")
>>> mod
REMVDODD(1: 1, 2: 1.4, 1: 2, 'mod': ..., 'modmod': ..., 'u1': 'y')
>>> mod.update_inplace([(2, 2.6), (3, 3.6)])
>>> mod
REMVDODD(1: 1, 2: 2.6, 1: 2, 'mod': ..., 'modmod': ..., 'u1': 'y', 3: 3.6)
>>> mod.pop(3)
3.6
>>> mod.update_replace([(1, -1)])
>>> mod
REMVDODD(2: 2.6, 'mod': ..., 'modmod': ..., 'u1': 'y', 1: -1)
>>> del mod["modmod"]
>>> mod
REMVDODD(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1)
>>> mod._data
((2, 2.6), ('mod', REMVDODD(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1)), ('u1', 'y'), (1, -1))
>>> mod._data is not mod.items(), mod._data == tuple(mod.items())
(True, True)
>>> mod[1] = 3
>>> mod
REMVDODD(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1, 1: 3)
>>> mod.update(u1="n")
>>> mod
REMVDODD(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')
>>> mod
REMVDODD(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')
>>> list(mod.lists())[:2]
[(2, [2.6]), ('mod', [REMVDODD(2: 2.6, 'mod': ..., 'u1': 'y', 1: -1, 1: 3, 'u1': 'n')])]
>>> list(mod.lists())[2:]
[('u1', ['y', 'n']), (1, [-1, 3])]
>>> mod.popitem()
('u1', 'n')
>>> mod.popitem(last=False)
(2, 2.6)
>>> mod
REMVDODD('mod': ..., 'u1': 'y', 1: -1, 1: 3)
>>> mod.deduplicate()
>>> mod
REMVDODD('mod': ..., 'u1': 'y', 1: 3)
>>> mod.u1 = "yy"
>>> mod
REMVDODD('mod': ..., 'u1': 'y', 1: 3, 'u1': 'yy')
>>> mod.deduplicate(how="first")
>>> mod
REMVDODD('mod': ..., 'u1': 'y', 1: 3)
>>> list(reversed(mod))
[1, 'u1', 'mod']
>>> mod
REMVDODD('mod': ..., 'u1': 'y', 1: 3)
>>> mod.setdefault(5, 2)
2
>>> mod
REMVDODD('mod': ..., 'u1': 'y', 1: 3, 5: 2)
>>> mod.setdefault(5, 1)
2
>>> mod
REMVDODD('mod': ..., 'u1': 'y', 1: 3, 5: 2)
"""

from __future__ import annotations

import copy
import itertools
from collections.abc import Callable, MutableMapping
from typing import Any

from pyaux.iterables import iterator_is_over, uniq

__all__ = (
    "DODD",
    "MVDODD",
    "MVOD",
    "REDODD",
    "REMVDODD",
    "DefaultDictExt",
    "DefaultDotDictMixin",
    "DotDict",
    "DotDictExt",
    "Dotdictify",
    "ODReprMixin",
    "OrderedDict",
    "dict_fget",
    "dict_fsetdefault",
    "dict_is_subset",
    "dict_merge",
    "hasattr_x",
)


def dict_fget(dictobj, key, default):
    """
    `dict_fget(dictobj, key, default)`
    ->
    `dictobj[key] if key in dictobj, else default().`
    - a lazy-evaluated dict.get.
    (`default` is mandatory but can be None).
    """
    try:
        return dictobj[key]
    except KeyError:
        if default is None:
            return None
        return default()


def dict_fsetdefault(dictobj, key, default):
    """
    `dict_fsetdefault(dictobj, key, default)`
    ->
    `dictobj[key] if key in dictobj else dictobj.setdefault(key, default())`
    - a lazy-evaluated dict.setdefault.
    (`default` is mandatory but can be None).
    """
    # Can be `D[k] = dict_fget(D, k, d); return D[k]`, but let's micro-optimize.
    # NOTE: not going over 'keyerror' for the defaultdict or alike classes.
    try:
        return dictobj[key]
    except KeyError:
        value = default() if default is not None else default
        dictobj[key] = value
        return value


def dict_is_subset(smaller_obj, larger_obj, *, recurse_iterables=False, require_structure_match=True):
    """
    Recursive check "smaller_dict's keys are subset of
    larger_dict's keys.

    NOTE: in practice, supports non-dict values at top.

    >>> value = {"a": 1, "b": [2, {"c": 3, "d": None}]}
    >>> dict_is_subset({}, value)
    True
    >>> dict_is_subset({"a": 1}, value)
    True
    >>> dict_is_subset({"a": 2}, value)
    False
    >>> dict_is_subset({"a": {"x": 4}}, value, require_structure_match=False)
    True
    >>> dict_is_subset({"b": [2]}, value, recurse_iterables=False)
    False
    >>> dict_is_subset({"b": [2]}, value, recurse_iterables=True, require_structure_match=True)
    False
    >>> dict_is_subset({"b": [2]}, value, recurse_iterables=True, require_structure_match=False)
    True
    >>> dict_is_subset({"b": [2, {}]}, value, recurse_iterables=True)
    True
    >>> dict_is_subset({"b": [2, {"c": 3}]}, value, recurse_iterables=True)
    True
    >>> dict_is_subset({"b": [2, {"c": 4}]}, value, recurse_iterables=True)
    False
    """
    kwa = dict(
        recurse_iterables=recurse_iterables,
        require_structure_match=require_structure_match,
    )
    if isinstance(smaller_obj, dict):
        if not isinstance(larger_obj, dict):
            return not require_structure_match

        # Both are dicts.
        for key, val in smaller_obj.items():
            try:
                lval = larger_obj[key]
            except KeyError:
                return False
            # 'compare' the values whatever they are
            if not dict_is_subset(val, lval, **kwa):
                return False

        return True

    # else:
    if recurse_iterables and hasattr(smaller_obj, "__iter__"):
        if not hasattr(larger_obj, "__iter__"):
            return not require_structure_match
        # smaller_value_iter, larger_value_iter
        svi = iter(smaller_obj)
        lvi = iter(larger_obj)
        for sval, lval in zip(svi, lvi):
            if not dict_is_subset(sval, lval, **kwa):
                return False
        if require_structure_match and (not iterator_is_over(svi) or not iterator_is_over(lvi)):  # noqa: SIM103
            # One of the iterables was longer and thus was not
            # consumed entirely by the izip
            return False
        return True

    # else:
    # elif not dict or iterable:
    return smaller_obj == larger_obj


def dict_merge(
    target,
    source,
    *,
    instancecheck=None,
    dictclass=dict,
    del_obj=object(),
    _copy=True,
    inplace=False,
):
    """
    do update() on 'dict of dicts of di...' structure recursively.
    Also, see sources for details.
    NOTE: does not keep target's specific tree structure (forces source's)
    :param del_obj: allows for deletion of keys if the key in the `source` is set to this.

    >>> data = {}
    >>> data = dict_merge(data, {"open_folders": {"my_folder_a": False}})
    >>> data
    {'open_folders': {'my_folder_a': False}}
    >>> data = dict_merge(data, {"open_folders": {"my_folder_b": True}})
    >>> assert data == {"open_folders": {"my_folder_a": False, "my_folder_b": True}}
    >>> _del = object()
    >>> data = dict_merge(data, {"open_folders": {"my_folder_b": _del}}, del_obj=_del)
    >>> assert data == {"open_folders": {"my_folder_a": False}}
    """
    if instancecheck is None:  # funhorrible ducktypings

        def instancecheck_default(iv):
            return hasattr(iv, "items")

        instancecheck = instancecheck_default

    # Recursive parameters shorthand
    kwa = dict(instancecheck=instancecheck, dictclass=dictclass, del_obj=del_obj)

    if _copy and not inplace:  # 'both are default'
        target = copy.deepcopy(target)

    for key, val in source.items():
        if val is del_obj:
            target.pop(key, None)
        elif instancecheck(val):  # (val -> source -> items())
            # NOTE: if target[key] wasn't a dict - it will be, now.
            target[key] = dict_merge(dict_fget(target, key, dictclass), val, **kwa)
        else:  # nowhere to recurse into - just replace
            # NOTE: if target[key] was a dict - it won't be, anymore.
            target[key] = val

    return target


class DotDict(dict):
    """A simple dict subclass with items also available over attributes"""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class DotDictExt(dict):
    """
    A dict subclass with items also available over
    attributes. Skips the attributes starting with '_' (for
    mixinability)
    """

    def __getattr__(self, name):
        if name.startswith("__"):  # NOTE: two underscores.
            return super().__getattr__(name)
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        if name.startswith("_"):
            return super().__setattr__(name, value)
        self[name] = value
        return None


_dotdictify_marker = object()


class Dotdictify(dict):
    """Recursive automatic doctdict thingy"""

    def __init__(self, value=None):
        if value is None:
            pass
        elif isinstance(value, dict):
            for key in value:
                self.__setitem__(key, value[key])
        else:
            raise TypeError("expected a dict")

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, Dotdictify):
            value = Dotdictify(value)
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        found = self.get(key, _dotdictify_marker)
        if found is _dotdictify_marker:
            found = Dotdictify()
            dict.__setitem__(self, key, found)
        return found

    __setattr__ = __setitem__
    __getattr__ = __getitem__


_repr_running = {}


class ODReprMixin:
    """
    A mixin for ordered dicts that provides two different representations
    and a wrapper for handling self-referencing structures.
    """

    def __irepr__(self):
        """The usual (default) representation of an ordereddict"""
        if not self:
            return f"{self.__class__.__name__}()"
        return f"{self.__class__.__name__}({self.items()!r})"

    def __drepr__(self):
        """A slightly more visual-oriented representation of an ordereddict"""
        if not self:
            return f"{self.__class__.__name__}()"
        items_s = ", ".join(f"{key!r}: {val!r}" for key, val in self.items())
        return f"{self.__class__.__name__}({items_s})"

    def __repr__(self, fn=__drepr__):
        """
        Wrapped around __drepr__ that makes it possible to
        represent infinitely-recursive dictionaries of this type.
        """
        # NOTE: version variety; might be a _get_ident or something else.
        try:
            from thread import get_ident as _get_ident
        except ImportError:
            from threading import get_ident as _get_ident

        call_key = (id(self), _get_ident())
        if call_key in _repr_running:
            # TODO?: make a YAML-like naming & referencing?
            # (too complicated for a repr() though)
            return "..."
        _repr_running[call_key] = 1
        try:
            return fn(self)
        finally:
            del _repr_running[call_key]


# https://pypi.python.org/pypi/ordereddict
# or /usr/lib/python2.7/collections.py
# with modifications
class OrderedDict(ODReprMixin, dict, MutableMapping):
    __end = None
    __map = None

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError(f"expected at most 1 arguments, got {len(args)}")
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

    def popitem(self, *, last=True):
        if not self:
            raise KeyError("dictionary is empty")
        key = next(reversed(self)) if last else iter(self).next()
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

    setdefault = MutableMapping.setdefault
    update = MutableMapping.update
    pop = MutableMapping.pop
    values = MutableMapping.values
    items = MutableMapping.items

    # Will be provided in any version from whichever is available.
    iterkeys = getattr(MutableMapping, "iterkeys", None) or MutableMapping.keys
    itervalues = getattr(MutableMapping, "itervalues", None) or MutableMapping.values
    iteritems = getattr(MutableMapping, "iteritems", None) or MutableMapping.items

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
            return all(p == q for p, q in zip(self.items(), other.items()))
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

    >>> d = MultiValueDict({"name": ["Adrian", "Simon"], "position": ["Developer"]})
    >>> d["name"]
    'Simon'
    >>> d.getlist("name")
    ['Adrian', 'Simon']
    >>> d.getlist("doesnotexist")
    []
    >>> d.getlist("doesnotexist", ["Adrian", "Simon"])
    ['Adrian', 'Simon']
    >>> d.get("lastname", "nonexistent")
    'nonexistent'
    >>> d.setlist("lastname", ["Holovaty", "Willison"])

    This class exists to solve the irritating problem raised by cgi.parse_qs,
    which returns a list for every key, even though most Web forms submit
    single name-value pairs.
    """

    def __init__(self, key_to_list_mapping=()):
        super().__init__(key_to_list_mapping)

    @classmethod
    def make_from_items(cls, items):
        key_to_list_mapping = {}
        for key, val in items:
            key_to_list_mapping.setdefault(key, []).append(val)
        return cls(key_to_list_mapping)

    def __repr__(self):
        sup = super().__repr__()
        return f"<{self.__class__.__name__}: {sup}>"

    def __getitem__(self, key):
        """
        Returns the last data value for this key, or [] if it's an empty list;
        raises KeyError if not found.
        """
        try:
            list_ = super().__getitem__(key)
        except KeyError as exc:
            raise MultiValueDictKeyError(repr(key)) from exc
        try:
            return list_[-1]
        except IndexError:
            # Does anyone know the reason for this behaviour and ways
            # there could happen to be an empty list?
            return []

    def __setitem__(self, key, value):
        super().__setitem__(key, [value])

    def __copy__(self):
        return self.__class__([(k, v[:]) for k, v in self.lists()])

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        result = self.__class__()
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def __getstate__(self):
        obj_dict = self.__dict__.copy()
        obj_dict["_data"] = {k: self.getlist(k) for k in self}
        return obj_dict

    def __setstate__(self, obj_dict):
        data = obj_dict.pop("_data", {})
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
            return super().__getitem__(key)
        except KeyError:
            if default is None:
                return []
            return default

    def setlist(self, key, list_):
        super().__setitem__(key, list_)

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

    def iteritems(self):
        """
        Yields (key, value) pairs, where value is the last item in the list
        associated with the key.
        """
        for key in self:
            yield key, self[key]

    def iterlists(self):
        """Yields (key, list) pairs."""
        return super().items()

    def itervalues(self):
        """Yield the last value on every key list."""
        for key in self:
            yield self[key]

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
            raise TypeError(f"`update` expected at most 1 arguments, got {len(args)}")
        if args:
            other_dict = args[0]
            if isinstance(other_dict, MultiValueDict):
                for key, value_list in other_dict.lists():
                    self.setlistdefault(key).extend(value_list)
            else:
                try:
                    for key, value in other_dict.items():
                        self.setlistdefault(key).append(value)
                except TypeError as exc:
                    raise ValueError("MultiValueDict.update() takes either a MultiValueDict or dictionary") from exc
        for key, value in kwargs.items():
            self.setlistdefault(key).append(value)

    def dict(self):
        """Returns current object as a dict with singular values."""
        return {key: self[key] for key in self}


# ######
# Other stuff
# ######


def _is_multivaluedict(val, *, deep=False):
    """
    Check the object for MultiValueDict face (to support e.g. the
    django's one). Does not include MVODs.
    """
    if isinstance(val, MultiValueDict):
        return True
    # The interesting internal-data access method 'lists':
    if not hasattr(val, "lists"):
        return False
    if deep:
        return any(cls.__name__ == "MultiValueDict" for cls in val.__class__.__mro__)
    return isinstance(val, dict)


def _lists_group(items):
    """items -> key_to_list_mapping"""
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
    """items -> key_to_list_mapping keeping some order"""
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
    """key_to_list_mapping -> items"""
    if isinstance(key_to_list_mapping, dict):
        key_to_list_mapping = key_to_list_mapping.items()
    return [(key, val) for key, vals in key_to_list_mapping for val in vals]


class MVODCommon(ODReprMixin):
    _data_internal: tuple[Any, ...] = ()

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
                raise ValueError(("dictionary update sequence element #%d has length %r; 2 is required") % (i, lv))
            key, val = item
            res.append((key, val))
        return tuple(res)

    def _process_upddata(self, args, kwds, *, preprocess=True, strict=False):
        """
        Convert some function call args into list of key-value pairs
        (same as `dict(*args, **kwds)` does).  Returns a tuple with
        pair-tuples.
        """
        if len(args) > 1:
            raise TypeError(f"Expected at most 1 arguments, got {len(args)}")
        arg = args[0] if args else []
        if isinstance(arg, MVOD):  # support init / update from antother MVOD
            arg = arg._data
        elif _is_multivaluedict(arg):  # Other `MultiValueDict`s
            arg = self._lists_ungroup(arg.lists())
        elif isinstance(arg, dict):
            arg = getattr(arg, "iteritems", arg.items)()
        if kwds:
            if strict:
                raise TypeError("initializing an ordered dict from keywords is not recommended")
            # Append the keywords to the other stuff
            arg = itertools.chain(arg, kwds.items())
        if preprocess:
            arg = self._preprocess_data(arg)  # NOTE: iterates over it and makes a tuple.
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

    def copy(self):
        return self.__copy__()

    # TODO?: __getstate__, __setstate__; probably not useful.

    def _iteritems(self):
        # WARN: no dict-changed-while-iterating handling. In practice,
        # iteration is always over a copy (since self._data is a tuple).
        yield from self._data

    def __reversed__(self):
        # See the `_iteritems` dict-changed-while-iterating note.
        for key, _ in reversed(self._data):
            yield key

    def _iterlists(self, *, ordered=True):
        """MultiValueDict-like (django) method. Not very optimal."""
        # See the `_iteritems` dict-changed-while-iterating note.
        pre_func = self._lists_group_ordered if ordered else self._lists_group
        yield from pre_func(self._data)

    def _itervalues(self):
        for _, val in self._iteritems():
            yield val

    def _iterkeys(self):
        # Supports the duplicates.
        for key, _ in self._iteritems():
            yield key

    def __iter__(self):
        return self._iterkeys()

    def items(self, *args, **kwargs):
        return self._iteritems(*args, **kwargs)

    def lists(self, *args, **kwargs):
        return self._iterlists(*args, **kwargs)

    def values(self, *args, **kwargs):
        return self._itervalues(*args, **kwargs)

    def keys(self, *args, **kwargs):
        return self._iterkeys(*args, **kwargs)

    # Bit more copypaste from UserDict.DictMixin (because most other
    # methods from it are unnecessary)

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError(f"pop expected at most 2 arguments, got {1 + len(args)!r}")
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

    def popitem(self, *, last=True):
        if not self:
            raise KeyError("dictionary is empty")
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
        """
        ...

        WARN: `mvod == od` and `od == mvod` might have different
        results (because OD doesn't handle MVODs).
        """
        if isinstance(other, (MVODCommon, OrderedDict)):
            # Quicker pre-check:
            if not dict.__eq__(self, other):
                return False

            # In the end it comes down to items.
            return self._data == tuple(other.items())

        if _is_multivaluedict(other):
            return self._data == tuple(self._lists_ungroup(other.lists()))

        if isinstance(other, dict):
            return self._data == tuple(other.items())

        return False

    def __ne__(self, other):
        return not self == other

    # __nonzero__ does not need overriding as dict handles that.

    # some other methods?


class MVOD(MVODCommon, dict):
    """
    MultiValuedOrderedDict: A not-very-optimized (most write operations
    are at least O(N) with the re-hashing cost) somewhat-trivial verison.
    Stores a tuple of pairs as the actual data (in `_data`), uses it for
    iteration, caches dict(data) as self for optimized key-access.
    """

    # TODO?: support unhashable keys (by skipping them in the cache)
    # TODO?: make the setitem behaviour configurable per instance

    def __init__(self, *args, **kwds):
        self.update(*args, **kwds)

    def _update_cache(self):
        dict.clear(self)
        dict.update(self, self._data)

    def update_append(self, *args, **kwds):
        """
        ...
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
        keys = {key for key, val in data_new}
        pre_data = tuple((key, val) for key, val in self._data if key not in keys)
        self._data_checked = pre_data + data_new

    def update_inplace(self, *args, **kwds):
        """
        A closer equivalent of OrderedDict.update that replaces the
        previous occurrences at the point of first occurrence.  Does not yet
        support multiple items handling in the updated keys.
        """
        data_new = self._process_upddata(args, kwds)
        news = dict(*args, **kwds)
        # XXXX/TODO: To update with multiple values will have to do `MVOD(*args,
        #   **kwds).lists()`, and (configurably) pop either each item from the
        #   list when it occurs or just one item each time.
        pre_data = tuple((key, news.pop(key, val)) for key, val in self._data)
        # Add the non-previously-existing ones.
        data_new = [(key, val) for key, val in data_new if key in news]
        self._data_checked = pre_data + tuple(data_new)

    def update(self, *args: Any, **kwargs: Any) -> None:
        return self.update_append(*args, **kwargs)

    def __delitem__(self, key):
        self._data_checked = tuple((k, v) for k, v in self._data if k != key)

    # def __getitem__:  inherited from `dict`

    def __setitem__(self, key, value):
        return self.update(((key, value),))
        # self._data_checked = self._data + ((key, value),)

    def deduplicate(self, how="last"):
        """
        ...
        NOTE: this method is equivalent to deduplicate_last by default.
        """
        if how == "first":
            pass
        elif how == "last":
            return self.deduplicate_last()
        else:
            raise ValueError(f"Unknown deduplication `how`: {how!r}")
        self._data_checked = tuple(uniq(self._data, key=lambda item: item[0]))
        return None

    def deduplicate_last(self):
        data_pre = uniq(reversed(self._data), key=lambda item: item[0])
        data_pre = list(data_pre)
        self._data_checked = tuple(reversed(data_pre))

    def deduplicated(self, **kwa):
        cp = self.copy()
        cp.deduplicate(**kwa)
        return cp

    def getlist(self, key, default=None):
        values = [item_val for item_key, item_val in self._iteritems() if item_key == key]
        if values:
            return values
        if default is None:
            return []
        return default


class MVLOD(MVODCommon, MultiValueDict):
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
        """
        ...
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
        keys = {key for key, val in data_new}
        data_kept = tuple((key, val) for key, val in self._data if key not in keys)
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
        data_result = tuple((item_key, item_val) for item_key, item_val in self._data if item_key != key)
        # See if we removed nothing.
        if len(data_result) == len(self._data):
            raise KeyError(key)
        if not self._optimised:
            self._data_checked = data_result
        else:
            self._data_internal = data_result
            try:
                dict.__delitem__(self, key)
            except KeyError as exc:
                raise Exception("The key should've been there", self, key) from exc

    # The defaults (for setitem, instantiation)

    def update(self, *args: Any, **kwargs: Any) -> None:
        return self.update_append(*args, **kwargs)

    def __setitem__(self, key, value):
        self.update([(key, value)])

    # Other optimisations

    def _iterlists(self, *, ordered=False):
        if ordered:
            return super()._iterlists(ordered=ordered)
        return dict.items(self)


class DotOrderedDict(DotDictExt, OrderedDict):
    """..."""


class DefaultDictExt(dict):
    """
    A purepython & simplified `defaultdict` version that doesn't change
    the interface except for the `_default` attribute (with the default_factory)
    """

    _default: Callable[[], Any] | None = None

    def __getitem__(self, name):
        try:
            return super().__getitem__(name)
        except KeyError:
            if self._default is not None:
                val = self._default()
                self[name] = val
                return val
            raise


def hasattr_x(obj, name):
    """
    A safer `hasattr` that only checks for simple attributes
    rather than properties or __getattr__ results.
    """
    try:
        object.__getattribute__(obj, name)
    except AttributeError:
        return False
    return True


class DefaultDotDictMixin(DotDict, DefaultDictExt):
    """
    A class that tries to combine DefaultDict and dotdict without causing
    too much of a mess. NOTE: skips _attributes on setattr and __attributes on
    getattr.
    """

    def __getattr__(self, name):
        # Mostly necessary to avoid `defaultdict`ing some special
        # methods like __getstate__ that weren't defined on the class.
        # (could disable the defaultdict'ing for that, though)
        if name.startswith("__"):  # NOTE: two underscores.
            return self.__getattribute__(name)  # Basically `raise AttributeError`.
        return super().__getattr__(name)  # __getitem__

    def __setattr__(self, name, value):
        # if name in self.__dict__:
        # if hasattr_x(self, name):
        #     self.__dict__[name] = value
        #     return

        # Mostly necessary for class code that sets attributes like
        # '_OrderedDict__end' (or the defaultdictx._default)
        if name.startswith("_"):
            # Basically `object.__setattr__(…)`
            # WARN: querying `d._attr` still sets it to the
            # default. Not necessarily problematic though.
            return dict.__setattr__(self, name, value)

        return super().__setattr__(name, value)  # __setitem__


class DODD(DefaultDotDictMixin, OrderedDict):
    """
    DotOrderedDefaultDict. Set `_default` attribute on it to a factory
    to use it as a defaultdict.
    NOTE: ignores attributes starting with '_'.
    """


class MVDODD(DefaultDotDictMixin, MVOD):
    pass


class REDODD(DODD):
    """Recursive dodd (by default)"""


REDODD._default = REDODD


class REMVDODD(MVDODD):
    """..."""


REMVDODD._default = REMVDODD


# TODO: test... things...

# TODO?: Add some other sort of multivaluedness
# (django.utils.datastructures.MultiValueDict).  (and maybe add a
# separate class compatible with id and/or the django.http.QueryDict
# or something)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
