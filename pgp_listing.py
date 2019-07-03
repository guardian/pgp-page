import os
import shutil
import pgp_manager

from pgp_manager import Entry
from jinja2 import Environment, FileSystemLoader, select_autoescape
from urllib import parse

from typing import Dict, List


class Group:
    def __init__(self, heading, entries):
        self.heading = heading
        self.entries = entries

    def __eq__(self, other):
        if not isinstance(other, Group):
            return NotImplemented

        return self.heading == other.heading and self.entries == other.entries

    def __hash__(self):
        # Make class instances usable as items in hashable collections
        return hash((self.heading, self.entries))


def parse_fingerprint(raw_fingerprint: str) -> str:
    split_str = raw_fingerprint.split('Key fingerprint = ', 1)
    if len(split_str) > 1:
        return split_str[1][:50]


def enhance_entry(entry: Entry) -> Entry:
    contact_name = entry.name.title()
    key_url = parse.quote(entry.publickey)
    fingerprint = parse_fingerprint(entry.fingerprint)
    return Entry(contact_name, key_url, fingerprint)


def sort_entries(entries: List[Entry]) -> Dict[str, List[Entry]]:
    groups = {}
    for entry in entries:
        group = entry.name.split(' ', 1)
        if len(group) > 1:
            grouping = group[1][0].upper()
            groups.setdefault(grouping, []).append(entry)
    return groups


def create_groups(entries: Dict[str, List[Entry]]) -> List[Group]:
    for key in entries:
        yield Group(key, entries[key])


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(
    loader=FileSystemLoader(THIS_DIR + '/templates/public'),
    trim_blocks=True,
    autoescape=select_autoescape(['html', 'xml'])
)


def render_page(groups: List[Group]):
    root_template = env.get_template('pgp-listing.html')
    return root_template.render(groups=groups)


if __name__ == '__main__':

    session = pgp_manager.create_session()

    all_entries = pgp_manager.get_all_entries(session)

    enhanced_entries = [enhance_entry(entry) for entry in all_entries]
    all_groups = create_groups(sort_entries(enhanced_entries))

    if os.path.exists('./build'):
        print('removing old build file')
        shutil.rmtree('./build')

    print('copying static assets')
    shutil.copytree('./static', './build/static')

    print('Creating templates')
    text_file = open("build/index.html", "w")
    text_file.write(render_page(all_groups))
    text_file.close()

    print('Done!')