"""
...

NOTE: python3.5+ only (only tested on python3.7).
"""
# pylint: disable=no-else-return
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=fixme

import copy
import re
# pylint: disable=no-name-in-module
from sre_constants import (
    LITERAL, RANGE, IN, NOT_LITERAL, NEGATE, MIN_REPEAT, MAX_REPEAT, MAXREPEAT,
    ANY, AT, AT_BEGINNING, AT_END, SUBPATTERN, BRANCH,
)
import sre_parse
import sre_compile


UNESCAPE = {val: key for key, val in sre_parse.ESCAPES.items()}
UNCATEGORIES = {
    ((val[0], tuple(val[1])) if isinstance(val, tuple) and len(val) == 2 and isinstance(val[1], list) else val): key
    for key, val in sre_parse.CATEGORIES.items()}


def _ensure_grouped(pattern, source=None):
    """
    ...

    >>> _ensure_grouped(pattern='zxcv', source=[(LITERAL, 122), (LITERAL, 120), (LITERAL, 99), (LITERAL, 118)])
    '(?:zxcv)'
    >>> _ensure_grouped(pattern='(?:zxcv)', source=[(LITERAL, 122), (LITERAL, 120), (LITERAL, 99), (LITERAL, 118)])
    '(?:zxcv)'
    >>> _ensure_grouped(pattern='[abc]', source=[(IN, [(LITERAL, 97), (LITERAL, 98), (LITERAL, 99)])])
    '[abc]'
    """
    if pattern.startswith('(') or pattern.startswith('['):
        return pattern
    if len(pattern) == 1:
        return pattern
    # TODO: e.g. '\r*'
    # if not source: source = sre_parse.parse(pattern)
    # if len(source.data) == 1: return pattern
    return '(?:{})'.format(pattern)


def _flags_to_list(flags):
    result = []
    if not flags:
        return result
    for key, value in sre_parse.FLAGS.items():
        if flags & value:
            result.append(key)
    return result


# TODO: re.VERBOSE autoindented version.
def rast_to_pattern(rast, _parent_type=None, **kwargs):
    r"""
    Inverse of `sre_parse._parse`.

    Partial implementation (to be completed as needed).

    >>> rex = r'[abc]?(?:^|a{4,}?)[^IO](b\ (?P<zxcv>c|d)+)*($|...|[0-9×][^a-z])(?P<qwer>a-imsx:zxcv)(?a-xsmi:zxcv)'
    >>> rast_to_pattern(sre_parse.parse(rex))
    '[abc]?(?:^|a{4,}?)[^IO](b\\ (?P<zxcv>[cd])+)*($|...|[0-9×][^a-z])(?P<qwer>a\\-imsx:zxcv)(?a-imsx:zxcv)'
    """
    _chr = chr
    # TODO: bytes-regex support: `if not kwargs.get(flags, 0) & re.UNICODE: _chr = lambda num: bytes([num])`

    # # # Reference glue;
    # def _parse(source, state, verbose, nested, first=False):
    # # parse a simple pattern
    # subpattern = SubPattern(state)

    # # # Reference glue;
    # # precompute constants into local variables
    # subpatternappend = subpattern.append
    # sourceget = source.get
    # sourcematch = source.match
    # _len = len
    # _ord = ord

    if isinstance(rast, sre_parse.SubPattern):

        kwargs['flags'] = kwargs.get('flags', 0) | rast.pattern.flags

        if kwargs.get('group_to_name') is None:
            kwargs['group_to_name'] = {
                val: key
                for key, val in rast.pattern.groupdict.items()}

        # Tricky point: support 'branch inside subpattern does not require extra parentheses',
        # AST goes like `SUBPATTERN -> SubPattern -> BRANCH`.
        # Thus, in a general-ish case, pass parent through a single-element SubPattern.
        if len(rast.data) == 1:
            kwargs['_parent_type'] = _parent_type

        return ''.join(
            rast_to_pattern(child, **kwargs)
            for child in rast)

    # # Reference glue:
    # while True:
    #     this = source.next
    #     if this is None:
    #         break # end of pattern
    #     if this in "|)":
    #         break # end of subpattern
    #     sourceget()

    # # Not supported in this function (but could be):
    # # Reference:
    #     if verbose:
    #         # skip whitespace and comments
    #         if this in WHITESPACE:
    #             continue
    #         if this == "#":
    #             while True:
    #                 this = sourceget()
    #                 if this is None or this == "\n":
    #                     break
    #             continue

    elif isinstance(rast, tuple) and len(rast) == 2:
        item_type, item_value = rast
        # For recursion.
        kwargs['_parent_type'] = item_type

        # # Reference:
        # if this[0] == "\\":
        #     code = _escape(source, this, state)
        #     subpatternappend(code)
        # # Reference:
        # elif this not in SPECIAL_CHARS:
        #     subpatternappend((LITERAL, _ord(this)))
        if item_type is LITERAL and isinstance(item_value, int):
            # XXXX: re.escape (re._special_chars_map) does not quite match
            # the sre_parse.ESCAPES. Might prefer to use the latter here.
            # The `re.escape` tends to escape more than needed, e.g. ' ' or '-' in all cases.
            return re.escape(_chr(item_value))

        # # Reference:
        # elif this == "[":
        #     here = source.tell() - 1
        #     # character set
        #     set = []
        #     setappend = set.append
        #     # if sourcematch(":"):
        #         # pass # handle character classes
        #     if source.next == '[':
        #         import warnings
        #         warnings.warn(
        #             'Possible nested set at position %d' % source.tell(),
        #             FutureWarning, stacklevel=nested + 6
        #         )
        #     negate = sourcematch("^")
        #     # check remaining characters
        #     while True:
        #         this = sourceget()
        #         if this is None:
        #             raise source.error("unterminated character set",
        #                                source.tell() - here)
        #         if this == "]" and set:
        #             break
        #         elif this[0] == "\\":
        #             code1 = _class_escape(source, this)
        #         else:
        #             if set and this in '-&~|' and source.next == this:
        #                 import warnings
        #                 warnings.warn(
        #                     'Possible set %s at position %d' % (
        #                         'difference' if this == '-' else
        #                         'intersection' if this == '&' else
        #                         'symmetric difference' if this == '~' else
        #                         'union',
        #                         source.tell() - 1),
        #                     FutureWarning, stacklevel=nested + 6
        #                 )
        #             code1 = LITERAL, _ord(this)
        #         if sourcematch("-"):
        #             # potential range
        #             that = sourceget()
        #             if that is None:
        #                 raise source.error("unterminated character set",
        #                                    source.tell() - here)
        #             if that == "]":
        #                 if code1[0] is IN:
        #                     code1 = code1[1][0]
        #                 setappend(code1)
        #                 setappend((LITERAL, _ord("-")))
        #                 break
        #             if that[0] == "\\":
        #                 code2 = _class_escape(source, that)
        #             else:
        #                 if that == '-':
        #                     import warnings
        #                     warnings.warn(
        #                         'Possible set difference at position %d' % (
        #                             source.tell() - 2),
        #                         FutureWarning, stacklevel=nested + 6
        #                     )
        #                 code2 = LITERAL, _ord(that)
        #             if code1[0] != LITERAL or code2[0] != LITERAL:
        #                 msg = "bad character range %s-%s" % (this, that)
        #                 raise source.error(msg, len(this) + 1 + len(that))
        #             lo = code1[1]
        #             hi = code2[1]
        #             if hi < lo:
        #                 msg = "bad character range %s-%s" % (this, that)
        #                 raise source.error(msg, len(this) + 1 + len(that))
        #             setappend((RANGE, (lo, hi)))

        elif item_type is RANGE and isinstance(item_value, tuple) and len(item_value) == 2:
            assert _parent_type is IN, _parent_type
            lo, hi = item_value
            return '{}-{}'.format(re.escape(_chr(lo)), re.escape(_chr(hi)))

        # # Reference:
        #         else:
        #             if code1[0] is IN:
        #                 code1 = code1[1][0]
        #             setappend(code1)

        # # Reference:
        #     set = _uniq(set)
        #     # XXX: <fl> should move set optimization to compiler!
        #     if _len(set) == 1 and set[0][0] is LITERAL:
        #         # optimization
        #         if negate:
        #             subpatternappend((NOT_LITERAL, set[0][1]))
        elif item_type is NOT_LITERAL:
            raise Exception("TODO", dict(case='NOT_LITERAL', value=rast))

            # # Reference:
            #     else:
            #         subpatternappend(set[0])
            # else:
            #     if negate:
            #         set.insert(0, (NEGATE, None))
        elif item_type is NEGATE and item_value is None:
            assert _parent_type is IN, _parent_type
            return '^'
            # # Reference:
            #     # charmap optimization can't be added here because
            #     # global flags still are not known
            #     subpatternappend((IN, set))
        elif item_type is IN:
            # XXXXX: needs re-checking
            return '[{}]'.format(''.join(
                rast_to_pattern(child, **kwargs)
                for child in item_value))

        # # Reference:
        # elif this in REPEAT_CHARS:
        #     # repeat previous item
        #     here = source.tell()
        #     if this == "?":
        #         min, max = 0, 1
        #     elif this == "*":
        #         min, max = 0, MAXREPEAT
        #     elif this == "+":
        #         min, max = 1, MAXREPEAT
        #     elif this == "{":
        #         if source.next == "}":
        #             subpatternappend((LITERAL, _ord(this)))
        #             continue
        #         min, max = 0, MAXREPEAT
        #         lo = hi = ""
        #         while source.next in DIGITS:
        #             lo += sourceget()
        #         if sourcematch(","):
        #             while source.next in DIGITS:
        #                 hi += sourceget()
        #         else:
        #             hi = lo
        #         if not sourcematch("}"):
        #             subpatternappend((LITERAL, _ord(this)))
        #             source.seek(here)
        #             continue
        #         if lo:
        #             min = int(lo)
        #             if min >= MAXREPEAT:
        #                 raise OverflowError("the repetition number is too large")
        #         if hi:
        #             max = int(hi)
        #             if max >= MAXREPEAT:
        #                 raise OverflowError("the repetition number is too large")
        #             if max < min:
        #                 raise source.error("min repeat greater than max repeat",
        #                                    source.tell() - here)
        #     else:
        #         raise AssertionError("unsupported quantifier %r" % (char,))
        #     # figure out which item to repeat
        #     if subpattern:
        #         item = subpattern[-1:]
        #     else:
        #         item = None
        #     if not item or item[0][0] is AT:
        #         raise source.error("nothing to repeat",
        #                            source.tell() - here + len(this))
        #     if item[0][0] in _REPEATCODES:
        #         raise source.error("multiple repeat",
        #                            source.tell() - here + len(this))
        #     if item[0][0] is SUBPATTERN:
        #         group, add_flags, del_flags, p = item[0][1]
        #         if group is None and not add_flags and not del_flags:
        #             item = p
        #     if sourcematch("?"):
        #         subpattern[-1] = (MIN_REPEAT, (min, max, item))
        # # Reference:
        #     else:
        #         subpattern[-1] = (MAX_REPEAT, (min, max, item))
        elif item_type is MAX_REPEAT or item_type is MIN_REPEAT and len(item_value) == 3:
            min_repeat, max_repeat, child = item_value
            if min_repeat == 0 and max_repeat == 1:
                modifier = '?'
            elif min_repeat == 0 and max_repeat is MAXREPEAT:
                modifier = '*'
            elif min_repeat == 1 and max_repeat is MAXREPEAT:
                modifier = '+'
            elif min_repeat == max_repeat:  # `{a}`
                modifier = '{{{}}}'.format(min_repeat)
            else:  # `{a,b}`
                modifier = '{{{},{}}}'.format(
                    '' if min_repeat == 0 else min_repeat,
                    '' if max_repeat is MAXREPEAT else max_repeat)
            return '{}{}{}'.format(
                _ensure_grouped(rast_to_pattern(child, **kwargs), source=child),
                modifier,
                # e.g. `.{4,}?` i.e. `(?:|.{4,})`
                '?' if item_type is MIN_REPEAT else '')

        # # Reference:
        # elif this == ".":
        #     subpatternappend((ANY, None))
        elif item_type is ANY and item_value is None:
            return '.'

        # # Reference:
        # elif this == "(":

            # # Reference:
            # start = source.tell() - 1
            # group = True
            # name = None
            # add_flags = 0
            # del_flags = 0
            # if sourcematch("?"):
            #     # options
            #     char = sourceget()
            #     if char is None:
            #         raise source.error("unexpected end of pattern")
            #     if char == "P":
            #         # python extensions
            #         if sourcematch("<"):
            #             # named group: skip forward to end of name
            #             name = source.getuntil(">", "group name")
            #             if not name.isidentifier():
            #                 msg = "bad character in group name %r" % name
            #                 raise source.error(msg, len(name) + 1)
            #         elif sourcematch("="):
            #             # named backreference
            #             name = source.getuntil(")", "group name")
            #             if not name.isidentifier():
            #                 msg = "bad character in group name %r" % name
            #                 raise source.error(msg, len(name) + 1)
            #             gid = state.groupdict.get(name)
            #             if gid is None:
            #                 msg = "unknown group name %r" % name
            #                 raise source.error(msg, len(name) + 1)
            #             if not state.checkgroup(gid):
            #                 raise source.error("cannot refer to an open group",
            #                                    len(name) + 1)
            #             state.checklookbehindgroup(gid, source)
            #             subpatternappend((GROUPREF, gid))
            #             continue

            # # Reference:
            #         else:
            #             char = sourceget()
            #             if char is None:
            #                 raise source.error("unexpected end of pattern")
            #             raise source.error("unknown extension ?P" + char,
            #                                len(char) + 2)
            #     elif char == ":":
            #         # non-capturing group
            #         group = None
            #     elif char == "#":
            #         # comment
            #         while True:
            #             if source.next is None:
            #                 raise source.error("missing ), unterminated comment",
            #                                    source.tell() - start)
            #             if sourceget() == ")":
            #                 break
            #         continue

            # # Reference:
            #     elif char in "=!<":
            #         # lookahead assertions
            #         dir = 1
            #         if char == "<":
            #             char = sourceget()
            #             if char is None:
            #                 raise source.error("unexpected end of pattern")
            #             if char not in "=!":
            #                 raise source.error("unknown extension ?<" + char,
            #                                    len(char) + 2)
            #             dir = -1 # lookbehind
            #             lookbehindgroups = state.lookbehindgroups
            #             if lookbehindgroups is None:
            #                 state.lookbehindgroups = state.groups
            #         p = _parse_sub(source, state, verbose, nested + 1)
            #         if dir < 0:
            #             if lookbehindgroups is None:
            #                 state.lookbehindgroups = None
            #         if not sourcematch(")"):
            #             raise source.error("missing ), unterminated subpattern",
            #                                source.tell() - start)
            #         if char == "=":
            #             subpatternappend((ASSERT, (dir, p)))
            #         else:
            #             subpatternappend((ASSERT_NOT, (dir, p)))
            #         continue

            # # Reference:
            #     elif char == "(":
            #         # conditional backreference group
            #         condname = source.getuntil(")", "group name")
            #         if condname.isidentifier():
            #             condgroup = state.groupdict.get(condname)
            #             if condgroup is None:
            #                 msg = "unknown group name %r" % condname
            #                 raise source.error(msg, len(condname) + 1)
            #         else:
            #             try:
            #                 condgroup = int(condname)
            #                 if condgroup < 0:
            #                     raise ValueError
            #             except ValueError:
            #                 msg = "bad character in group name %r" % condname
            #                 raise source.error(msg, len(condname) + 1) from None
            #             if not condgroup:
            #                 raise source.error("bad group number",
            #                                    len(condname) + 1)
            #             if condgroup >= MAXGROUPS:
            #                 msg = "invalid group reference %d" % condgroup
            #                 raise source.error(msg, len(condname) + 1)
            #         state.checklookbehindgroup(condgroup, source)
            #         item_yes = _parse(source, state, verbose, nested + 1)
            #         if source.match("|"):
            #             item_no = _parse(source, state, verbose, nested + 1)
            #             if source.next == "|":
            #                 raise source.error("conditional backref with more than two branches")
            #         else:
            #             item_no = None
            #         if not source.match(")"):
            #             raise source.error("missing ), unterminated subpattern",
            #                                source.tell() - start)
            #         subpatternappend((GROUPREF_EXISTS, (condgroup, item_yes, item_no)))
            #         continue

            # # Reference:
            #     elif char in FLAGS or char == "-":
            #         # flags
            #         flags = _parse_flags(source, state, char)
            #         if flags is None:  # global flags
            #             if not first or subpattern:
            #                 import warnings
            #                 warnings.warn(
            #                     'Flags not at the start of the expression %r%s' % (
            #                         source.string[:20],  # truncate long regexes
            #                         ' (truncated)' if len(source.string) > 20 else '',
            #                     ),
            #                     DeprecationWarning, stacklevel=nested + 6
            #                 )
            #             if (state.flags & SRE_FLAG_VERBOSE) and not verbose:
            #                 raise Verbose
            #             continue

            # # Reference:
            #         add_flags, del_flags = flags
            #         group = None
            #     else:
            #         raise source.error("unknown extension ?" + char,
            #                            len(char) + 1)

            # # Reference:
            # # parse group contents
            # if group is not None:
            #     try:
            #         group = state.opengroup(name)
            #     except error as err:
            #         raise source.error(err.msg, len(name) + 1) from None
            # sub_verbose = ((verbose or (add_flags & SRE_FLAG_VERBOSE)) and
            #                not (del_flags & SRE_FLAG_VERBOSE))
            # p = _parse_sub(source, state, sub_verbose, nested + 1)

            # # Reference glue: `_parse_sub` source:
            # def _parse_sub(source, state, verbose, nested):
            # # parse an alternation: a|b|c

            # # Reference: `_parse_sub` source:
            # items = []
            # itemsappend = items.append
            # sourcematch = source.match
            # start = source.tell()
            # while True:
            #     itemsappend(_parse(source, state, verbose, nested + 1,
            #                        not nested and not items))
            #     if not sourcematch("|"):
            #         break

            # # Reference: `_parse_sub` source:
            # if len(items) == 1:
            #     return items[0]

            # # Reference: `_parse_sub` source:
            # subpattern = SubPattern(state)

            # # Reference: `_parse_sub` source:
            # # check if all items share a common prefix
            # while True:
            #     prefix = None
            #     for item in items:
            #         if not item:
            #             break
            #         if prefix is None:
            #             prefix = item[0]
            #         elif item[0] != prefix:
            #             break
            #     else:
            #         # all subitems start with a common "prefix".
            #         # move it out of the branch
            #         for item in items:
            #             del item[0]
            #         subpattern.append(prefix)
            #         continue # check next one
            #     break

            # # Reference: `_parse_sub` source:
            # # check if the branch can be replaced by a character set
            # set = []
            # for item in items:
            #     if len(item) != 1:
            #         break
            #     op, av = item[0]
            #     if op is LITERAL:
            #         set.append((op, av))
            #     elif op is IN and av[0][0] is not NEGATE:
            #         set.extend(av)
            #     else:
            #         break
            # else:
            #     # we can store this as a character set instead of a
            #     # branch (the compiler may optimize this even more)
            #     subpattern.append((IN, _uniq(set)))
            #     return subpattern

            # # Reference: `_parse_sub` source:
            # subpattern.append((BRANCH, (None, items)))
            # return subpattern

        elif item_type is BRANCH and isinstance(item_value, tuple) and len(item_value) == 2 and item_value[0] is None:
            _, children = item_value
            # XXXXXXX: needs re-checking:
            result = '|'.join(
                rast_to_pattern(child, **kwargs)
                for child in children)
            # Tricky: branch inside subpattern does not require extra parentheses.
            if _parent_type is not SUBPATTERN:
                result = '(?:{})'.format(result)
            return result

            # # Reference:
            # if not source.match(")"):
            #     raise source.error("missing ), unterminated subpattern",
            #                        source.tell() - start)
            # if group is not None:
            #     state.closegroup(group, p)
            # subpatternappend((SUBPATTERN, (group, add_flags, del_flags, p)))
        elif item_type is SUBPATTERN and isinstance(item_value, tuple) and len(item_value) == 4:
            group, add_flags, del_flags, child = item_value
            flags = _flags_to_list(add_flags)
            if del_flags:
                flags.append('-')
                flags.extend(_flags_to_list(del_flags))

            if group is None:
                flags.append(':')
            else:
                group_to_name = kwargs.get('group_to_name')
                name = group_to_name.get(group)
                if name:
                    # NOTE: making a named group with changed flags is syntaxically impossible.
                    assert not flags
                    flags = ['P<{}>'.format(name)] + flags

            return '({}{})'.format(
                '?{}'.format(''.join(flags)) if flags else '',
                rast_to_pattern(child, **kwargs))

        # # Reference:
        # elif this == "^":
        #     subpatternappend((AT, AT_BEGINNING))
        elif item_type is AT and item_value is AT_BEGINNING:
            return '^'

        # # Reference:
        # elif this == "$":
        #     subpatternappend((AT, AT_END))
        elif item_type is AT and item_value is AT_END:
            return '$'

        # # Reference:
        # else:
        #     raise AssertionError("unsupported special character %r" % (char,))

    # # Reference:
    # # unpack non-capturing groups
    # for i in range(len(subpattern))[::-1]:
    #     op, av = subpattern[i]
    #     if op is SUBPATTERN:
    #         group, add_flags, del_flags, p = av
    #         if group is None and not add_flags and not del_flags:
    #             subpattern[i: i+1] = p

    # # Reference:
    # return subpattern
    raise Exception("TODO", dict(case="unknown", cls=rast.__class__, value=rast))


def cutoff_rast(rast, **kwargs):
    """
    Yield all smaller expressions for the specified parsed regular expressions.

    Intended for figuring out where the matching fails.
    """

    def make_cutoff_obj(lst):
        cutoff_obj = copy.copy(rast)
        cutoff_obj.pattern = copy.copy(cutoff_obj.pattern)
        # TODO?: mockup the cutoff_obj.pattern.str using rast_to_pattern
        cutoff_obj.pattern.str = None

        cutoff_obj.data = lst
        return cutoff_obj

    for idx in reversed(range(len(rast))):
        # Will start with the entire list and end with one item.
        cutoff = rast[:idx + 1]

        yield make_cutoff_obj(cutoff)

        last_child = cutoff[-1]
        if not last_child:
            continue
        # Recurse over the trees:
        if isinstance(last_child, tuple) and len(last_child) == 2:
            item_type, item_value = last_child

            # '...(abcd)' -> ['...(abcd)', '...(abc)', ..., '...(a)', '...']
            if item_type is SUBPATTERN and len(item_value) == 4:
                base_rast = list(cutoff)[:-1]

                subsubpattern_params = item_value[:-1]
                subsubpattern = item_value[-1]
                for subcutoff in cutoff_rast(subsubpattern, **kwargs):
                    cutoff_rec = base_rast + [(item_type, subsubpattern_params + (subcutoff,))]
                    yield make_cutoff_obj(cutoff_rec)

            # '...(abc|de)' -> ['...(abc|de)', '...(abc|d)', '...(ab|d)', '...(a|d)', '...']
            elif item_type is BRANCH and len(item_value) == 2 and item_value[0] is None:
                # item_value: `(None, [subpattern, subpattern, ...])`
                base_rast = list(cutoff)[:-1]

                subsubpattern_params = item_value[:-1]
                subsubpatterns = item_value[-1]
                subsubpatterns = subsubpatterns[:]
                for spidx, subsubpattern in reversed(list(enumerate(subsubpatterns))):
                    for subcutoff in cutoff_rast(subsubpattern, **kwargs):
                        # Mutating so that when a subsubpattern is exhausted it
                        # remains in the minimal form.
                        subsubpatterns[spidx] = subcutoff
                        cutoff_rec = base_rast + [(item_type, subsubpattern_params + (subsubpatterns[:],))]
                        yield make_cutoff_obj(cutoff_rec)


def normalize_pattern(pattern, flags=0):
    rast = sre_parse.parse(pattern, flags=flags)
    return rast_to_pattern(rast)


def find_matching_subregexes(pattern, string, flags=0, verbose=False):
    rast = sre_parse.parse(pattern, flags=flags)
    for cutoff in cutoff_rast(rast):
        subpattern = sre_compile.compile(cutoff, flags=flags)
        match = subpattern.search(string)
        if match:
            # Otherwise unusable:
            pattern_round = re.compile(rast_to_pattern(cutoff), flags=flags)
            if verbose:
                yield dict(
                    cutoff=cutoff,
                    subpattern=subpattern,
                    pattern_round=pattern_round,
                    match=match,
                    substring=match.group(0),
                    substring_unmatched=string[match.end(0):],
                )
            else:
                yield pattern_round


def main():
    import sys
    rex = sys.argv[1]
    string = sys.argv[2]
    print('Regex: {!r}, string: {!r}'.format(rex, string), file=sys.stderr)
    for result in find_matching_subregexes(rex, string, verbose=True):
        print('{pattern_round.pattern!r} -> {substring!r}'.format(**result))


if __name__ == '__main__':
    main()
