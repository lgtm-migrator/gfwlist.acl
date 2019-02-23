#!/usr/bin/env python3
"""Convert gfwlist format to ssr compatible acl file"""

import fileinput
import re
from datetime import datetime, timedelta, tzinfo
from itertools import chain


class ChinaTimezone(tzinfo):
    def tzname(self, dt):
        return 'UTC+8'

    def utcoffset(self, dt):
        return timedelta(hours=8)

    def dst(self, dt):
        return timedelta()


def get_regexp(line):

    # Escape, not use `re.escape` since it behavior changes in diffrent python version
    line = re.sub(r'[.*+?^${}()|[\]\\]', lambda x: '\\{}'.format(x.group(0)), line)

    # https://adblockplus.org/filters#basic
    line = line.replace(r'\*', '.+')
    # https://adblockplus.org/filters#separators
    line = line.replace(r'\^', r'([^a-zA-Z0-9_-.%]|$)')

    # https://adblockplus.org/filters#anchors
    line = re.sub(r'^\\\|\\\|(https?\??://)?', r'(^|\.)', line)
    line = re.sub(r'^\\\|(https?\??://)?', '^', line)
    line = re.sub(r'\\\|$', '$', line)

    return get_rules(line)
    

def get_rules(regexp):
    regexp = re.sub(r'\^?https?\??://', '^', regexp)
    regexp = re.sub(r'(\.\*)+$', '', regexp)
    regexp = re.sub(r'/$', '$', regexp)

    ret = [regexp]
    # Split long line by `|`
    match = len(regexp) > 80 and re.match(r'(.*)\((.*)\)(.*)', regexp)
    if match:
        prefix = match.group(1)
        items = match.group(2).split('|')
        suffix = match.group(3)
        ret = []
        size = 10
        for i in range(0, len(items),size):
            chunk = items[i:i+size]
            ret.append('{}({}){}'.format(prefix, '|'.join(chunk), suffix))

    # SSR can not deal with too long rule in one line
    ret = [i for i in ret if len(i) < 500]
    return ret

def convert_line(line):
    """ Convert gfwlist rule to acl format   """

    if not line:
        return []

    line = line.replace(r'\/', '/')

    # IP
    if re.match(r'^[\d.:/]+$', line):
        return [line]

    # https://adblockplus.org/filters#regexps
    if line.startswith('/') and line.endswith('/'):
        return get_rules(line[1:-1])

    return get_regexp(line)


def main():
    header = [
        '#',
        '# Date: {}'.format(datetime.now(ChinaTimezone()).isoformat()),
        '# Home Page: {}'.format('https://github.com/NateScarlet/gfwlist.acl'),
        '# URL: {}'.format(
            'https://raw.githubusercontent.com/NateScarlet/gfwlist.acl/master/gfwlist.acl'),
        '#',
        '',
        '[bypass_all]',
    ]
    blacklist = ['', '[proxy_list]', '']
    whitelist = ['', '[bypass_list]', '']

    for line in fileinput.input():
        line = line.strip()  # type: str
        # https://adblockplus.org/filters#comments
        if line.startswith(('!', '[AutoProxy')):
            continue

        # https://adblockplus.org/filters#whitelist
        is_whitelist = line.startswith('@@')
        if is_whitelist:
            line = line[2:]
        (whitelist if is_whitelist else blacklist).extend(convert_line(line))

    for i in chain(header, blacklist, whitelist):
        print(i)


if __name__ == '__main__':
    main()
