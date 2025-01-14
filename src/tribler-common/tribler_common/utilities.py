import itertools
import os
import platform
import re
import sys
from dataclasses import dataclass, field
from typing import Set, Tuple
from urllib.parse import urlparse
from urllib.request import url2pathname

from tribler_core.utilities.path_util import Path


def is_frozen():
    """
    Return whether we are running in a frozen environment
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        sys._MEIPASS
    except Exception:
        return False
    return True


def uri_to_path(uri):
    parsed = urlparse(uri)
    host = "{0}{0}{mnt}{0}".format(os.path.sep, mnt=parsed.netloc)
    return Path(host) / url2pathname(parsed.path)


fts_query_re = re.compile(r'\w+', re.UNICODE)
tags_re = re.compile(r'#[^\s^#]{3,50}(?=[#\s]|$)')


@dataclass
class Query:
    original_query: str
    tags: Set[str] = field(default_factory=set)
    fts_text: str = ''


def parse_query(query: str) -> Query:
    """
    The query structure:
        query = [tag1][tag2] text
                 ^           ^
                tags        fts query
    """
    if not query:
        return Query(original_query=query)

    tags, remaining_text = extract_tags(query)
    return Query(original_query=query, tags=tags, fts_text=remaining_text.strip())


def extract_tags(text: str) -> Tuple[Set[str], str]:
    if not text:
        return set(), ''

    tags = set()
    positions = [0]

    for m in tags_re.finditer(text):
        tags.add(m.group(0)[1:])
        positions.extend(itertools.chain.from_iterable(m.regs))
    positions.append(len(text))

    remaining_text = ''.join(text[positions[i] : positions[i + 1]] for i in range(0, len(positions) - 1, 2))
    return tags, remaining_text


def to_fts_query(text):
    if not text:
        return None

    words = [f'"{w}"' for w in fts_query_re.findall(text) if w]
    if not words:
        return None

    return ' '.join(words) + '*'


def show_system_popup(title, text):
    """
    Create a native pop-up without any third party dependency.

    :param title: the pop-up title
    :param text: the pop-up body
    """
    sep = "*" * 80

    # pylint: disable=import-outside-toplevel, import-error, broad-except
    print('\n'.join([sep, title, sep, text, sep]), file=sys.stderr)  # noqa: T001
    system = platform.system()
    try:
        if system == 'Windows':
            import win32api

            win32api.MessageBox(0, text, title)
        elif system == 'Linux':
            import subprocess

            subprocess.Popen(['xmessage', '-center', text])
        elif system == 'Darwin':
            import subprocess

            subprocess.Popen(['/usr/bin/osascript', '-e', text])
        else:
            print(f'cannot create native pop-up for system {system}')  # noqa: T001
    except Exception as exception:
        # Use base Exception, because code above can raise many
        # non-obvious types of exceptions:
        # (SubprocessError, ImportError, win32api.error, FileNotFoundError)
        print(f'Error while showing a message box: {exception}')  # noqa: T001
