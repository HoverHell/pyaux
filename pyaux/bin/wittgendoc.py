#!/usr/bin/env python
# coding: utf8
"""
A script to convert convenient text to markdown to html.
"""


import os
import sys
import re
import pyaux


def repl_header(match):
    """ Replace '=' header with '#' header """
    lh, text, rh = match.groups()
    anchor = text.strip().replace(' ', '_')
    res = '%(lh)s %(text)s <a name="%(anchor)s" href="#%(anchor)s">§</a> %(rh)s' % dict(
        lh='#' * len(lh), text=text, anchor=anchor, rh='#' * len(rh))
    # # Add an anchor
    # res = '<a href="%s">\n%s\
    # res += '\n<a name="%s"></a>' % (text.strip(),)
    return res


class Worker:
    result = None
    state = None
    state__list = None
    state__location = None

    simple_replacements = (
        # header
        (r'^(=+) (.+) (=+)$', repl_header),
        # trailing whitespaces
        (r' *$', ''),
    )

    header = '''
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <style type="text/css">
      h1, h2, h3 {
        line-height: 1.2;
      }
      body {
        margin: 40px auto;
        max-width: 650px;
        line-height: 1.6;
        font-size: 18px;
        color: #444;
        padding: 0 10px;
      }
      ol {
        padding: 0 0 0 2em;
      }
      ol[manual] {
        padding-left: 1em;
        list-style: none;

      }
      ol[manual] li {
        padding-top: 0.25em;

        text-indent: -1em;
        padding-left: 1em;
      }
      li[value]:before {
        content: attr(value) ". ";
      }
    </style>
  </head>
  <body>
    '''

    footer = '''
  </body>
</html>
    '''

    list_header = '<ol manual=1>'
    list_footer = '</ol>'
    item_footer = '</li>'  # non-item-specific

    def process(self, lines):
        self.state = ''
        self.state__list = []
        self.state__location = []
        self.result = []

        # self.result.append(self.header)

        lines = (self.handle_simple_replacements(line) for line in lines)
        line_iter = pyaux.window(lines, fill_left=True, fill=None)

        for prev_line, line in line_iter:
            self.check_state(prev_line, line)
            if self.state == 'list':
                self.process_list(line)
            else:
                self.result.append(line)

        # self.result.append(self.footer)

        return self.result

    def handle_simple_replacements(self, line):
        # simple replacements
        for rex, repl in self.simple_replacements:
            line = re.sub(rex, repl, line)
        return line

    def check_state(self, prev_line, line):
        """ State changes handler """
        if self.state == 'list':
            # empty line and then a non-list.
            # Almost markdown-like behaviour for lists: single empty
            # lines will not break the list; but unlike markdown, two
            # empty lines will.
            if not prev_line and not re.search(r'^ +[0-9].*\. ', line):
                # Not a list anymore
                self.result, prev_line_x = self.result[:-1], self.result[-1]
                self.unwind_list()
                self.result.append(prev_line_x)
                self.state = ''
                self.state__list = None
        elif not prev_line and line.startswith(' 1. '):
            # note the very specific list starter
            self.state = 'list'
            self.state_list = []

        if self.state == '':
            # Process the headings-state
            self.check_state_header(line)

    def check_state_header(self, line):
        """ Keep the state__location current """
        heading_match = re.search(
            r'^(?P<tag>#+).*name="(?P<name>[^"]+)".*',
            line)
        if not heading_match:
            return

        data = heading_match.groupdict()
        depth = len(data['tag'])
        # Should almost always exist because of repl_header.
        name = data.get('name') or ''
        data.update(depth=depth, name=name)
        if not self.state__location:
            self.state__location = [data]
            return

        shallower, same_or_deeper = pyaux.split_list(
            self.state__location, lambda info: info['depth'] < depth)
        self.state__location = shallower + [data]

    def process_list(self, line):
        # any line should match
        match = re.search(
            r'^(?P<spaces> *)(?:(?P<num>[0-9a-z.]+)\. )?(?P<text>.*)$',
            line)
        data = match.groupdict()
        spaces = data['spaces']
        indent = len(spaces)
        num = data.get('num')
        text = data['text']
        # Synopsis: markdown considers everything within html tags to
        # be written as-is. Therefore, process all htat stuff
        # explicitly.
        # TODO: this all should've probably been done as markdown
        # extender subclass.
        text = _markdown_process(text)
        text = re.sub(r'^ *<p>(.*)</p> *$', r'\1', text)

        if not num:
            # put as-is
            # e.g.: empty lines
            self.result.append(line)
            return

        item_header = '<li value="%s">' % (num,)

        anchor_name = ''.join(
            "%s__" % (info['name'],) for info in self.state__location)
        anchor_name = anchor_name + num.rstrip('.').replace('.', '_')
        item_header = item_header + '<a name="%s"></a>' % (anchor_name,)
        item_footer = self.item_footer
        item_info = dict(data, indent=indent)

        # else:  if num:
        if not self.state__list:
            # starting a list
            self.result.extend((
                self.list_header,  # <ol>
                spaces + item_header,  # <li>
                spaces + text))
            self.state__list = [item_info]
            return

        # else: if within a list already:
        last_info = self.state__list[-1]
        if last_info['indent'] == indent:
            # same indent, i.e. continuing the list
            self.result.extend((
                spaces + item_footer,  # </li>
                spaces + item_header,  # <li>
                spaces + text))
            last_info.update(item_info)  # replace the num for possible recursion
        elif 0 < indent - last_info['indent'] <= 2:
            # going deeper
            # ol-li-ol-li chain
            self.result.extend((
                spaces + self.list_header,  # <ol>
                spaces + item_header,  # <li>
                spaces + text))
            self.state__list.append(item_info)
        elif indent - last_info['indent'] < 0:
            # returning
            state_closing, state_remain = pyaux.split_list(
                self.state__list, lambda info: info['indent'] > indent)
            self.unwind_list(state_closing)  # </li></ol>
            self.state__list = state_remain
            self.result.extend((
                spaces + item_footer,  # </li>
                spaces + item_header,  # <li>
                spaces + text))
        else:  # more than 2 spaces deeper in; assume it's just more text
            self.result.append(line)

    def unwind_list(self, infos=None):
        if infos is None:
            infos = self.state__list or []
        for info in reversed(infos):
            spaces = info['spaces']
            self.result.extend((
                spaces + self.item_footer,  # </li>
                spaces + self.list_footer))  # </ol>


def _markdown_process(text, *ar, **kwa):
    import markdown
    # Not exactly by the standard, but visually better for the lists:
    kwa.setdefault('tab_length', 2)
    return markdown.Markdown(*ar, **kwa).convert(text)


def main(src_ext='.txt'):
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = os.path.join(os.path.dirname(__file__), '..', 'doc.txt')

    basename = filename
    if basename.endswith(src_ext):
        basename = basename[:-len(src_ext)]

    with open(filename) as fo:
        data = fo.read()


    lines = data.splitlines()

    worker = Worker()
    result = worker.process(lines)
    result_s = '\n'.join(result)

    if not os.environ.get('NO_MD'):
        with open(basename + '.md', 'w') as fo:
            fo.write(result_s)

    import markdown
    result_html_base = _markdown_process(result_s)
    result_html = worker.header + result_html_base + worker.footer
    with open(basename + '.html', 'w') as fo:
        fo.write(result_html)


if __name__ == '__main__':
    main()
