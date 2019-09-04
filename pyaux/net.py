# coding: utf8
"""
...
"""

from __future__ import division, absolute_import, print_function, unicode_literals

import socket


def get_constants(
        module, prefix,
        named=True, unprefixed=True, valued=True,
        lowercase=True,
        value_only=False):
    """ Mapping of constants by several ways to specify them """
    result = {}
    for name in dir(module):
        if not name.startswith(prefix):
            continue
        shortname = name[len(prefix):]
        value = getattr(module, name)
        if value_only:
            item = value
        else:
            item = dict(value=value, name=name, shortname=shortname)
        if named:
            result[name] = item
            if lowercase:
                result[name.lower()] = item
        if unprefixed:
            result[shortname] = item
            if lowercase:
                result[shortname.lower()] = item
        if valued:
            result[value] = item

    return result


SOCKET_FAMILIES = get_constants(socket, 'AF_')
SOCKET_TYPES = get_constants(socket, 'SOCK_')
SOCKET_PROTOS = get_constants(socket, 'IPPROTO_')
SOCKET_AI = get_constants(socket, 'AI_')


def gai_verbose(
        host,
        port=0, family=0, type='stream', proto='tcp',
        canonname=False, addrconfig=False, v4mapped=False, v4mapped_all=False,
        numerichost=False, numericserv=False, passive=False,
        flags=0):
    """

    :param addrconfig: return only address families (INET / INET6) that are configured on the current system.

    :param canonname: populate the "canonname" field ("official name of the host").

    :param v4mapped: return IPv4-mapped IPv6 addresses for hosts with no IPv6 addresses.

    :param v4mapped_all: return all IPv4 addresses as IPv4-mapped.

    :param numerichost: disallow network host address lookups.

    :param numericserv: disallow lookups of the service (`port`) names.

    :param passive: return addresses for binding sockets (rather than connecting).

    See also:
    http://man7.org/linux/man-pages/man3/getaddrinfo.3.html
    https://docs.python.org/3/library/socket.html
    """
    family_set = None
    if isinstance(family, (list, tuple, set)):
        family_set = set(
            SOCKET_FAMILIES[family_one]['value']
            for family_one in family)
        family = 0

    flags = flags or 0
    if addrconfig:
        flags = flags | socket.AI_ADDRCONFIG
    if canonname:
        flags = flags | socket.AI_CANONNAME
    if v4mapped or v4mapped_all:
        flags = flags | socket.AI_V4MAPPED
    if v4mapped_all:
        flags = flags | socket.AI_ALL
    if numerichost:
        flags = flags | socket.AI_NUMERICHOST
    if numericserv:
        flags = flags | socket.AI_NUMERICSERV
    if passive:
        flags = flags | socket.AI_PASSIVE

    responses = socket.getaddrinfo(
        host,
        port or 0,
        SOCKET_FAMILIES[family or 0]['value'],
        SOCKET_TYPES[type or 0]['value'],
        SOCKET_PROTOS[proto or 0]['value'],
        flags,
    )
    return gai_verbose_parse(responses, family_set=family_set, flags=flags)


def gai_verbose_parse(responses, family_set=None, flags=None):
    results = []
    flag_names = set()
    if flags is not None:
        flag_names = set(
            item['name']
            for num, item in SOCKET_AI.items()
            if flags & item['value']
        )

    for family, socktype, proto, canonname, sockaddr in responses:

        if family_set is not None and family not in family_set:
            continue
        # TODO: same for the rest.

        flow_info = None
        scope_id = None
        if len(sockaddr) == 2:
            address, port = sockaddr
        elif len(sockaddr) == 4:
            address, port, flow_info, scope_id = sockaddr
        else:
            raise Exception("Unexpected getaddrinfo sockaddr length", sockaddr)

        results.append(dict(
            address=address,
            port=port,
            flow_info=flow_info,
            scope_id=scope_id,

            canonname=canonname,
            family_name=SOCKET_FAMILIES[family]['name'],  # family.name,
            family=int(family),  # family.numerator,
            type_name=SOCKET_TYPES[socktype]['name'],  # socktype.name,
            type=int(socktype),  # socktype.numerator,
            proto_name=SOCKET_PROTOS[proto]['name'],
            proto=proto,

            sockaddr=sockaddr,
            flags=flags,
            flag_names=flag_names,
        ))
    return results


def _gai_example():
    hostname = 'ipv6-test.com'
    res = gai_verbose(
        hostname,
        family=('inet', 'inet6'),
        # canonname=True,
        # addrconfig=True,
        # v4mapped=True,
    )
    # res = pd.DataFrame(res, columns=res[0].keys() if res else None)
    return res


if __name__ == '__main__':
    print(_gai_example())
