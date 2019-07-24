import os
import shutil
import json
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


def lambda_handler(event, context) -> None:
    DATA_BUCKET_NAME = os.getenv('DATA_BUCKET_NAME')
    PUBLIC_BUCKET_NAME = os.getenv('PUBLIC_BUCKET_NAME')

    session = pgp_manager.create_session()
    all_entries = pgp_manager.get_all_entries(session, DATA_BUCKET_NAME, PUBLIC_BUCKET_NAME)
    enhanced_entries = [enhance_entry(entry) for entry in all_entries]
    all_groups = create_groups(sort_entries(enhanced_entries))
    index_page = render_page(all_groups)

    pgp_manager.upload_files(session, PUBLIC_BUCKET_NAME, './static')
    pgp_manager.upload_html(session, PUBLIC_BUCKET_NAME, 'index.html', index_page)


if __name__ == '__main__':

    if os.getenv('STAGE'):
        DATA_BUCKET_NAME = os.getenv('DATA_BUCKET_NAME')
        PUBLIC_BUCKET_NAME = os.getenv('PUBLIC_BUCKET_NAME')
        AWS_PROFILE = os.getenv('AWS_PROFILE')
    else:
        config_path = os.path.expanduser('~/.gu/secure-contact.json')
        config = json.load(open(config_path))
        DATA_BUCKET_NAME = config['DATA_BUCKET_NAME']
        PUBLIC_BUCKET_NAME = config['PUBLIC_BUCKET_NAME']
        AWS_PROFILE = config['AWS_PROFILE']

    session = pgp_manager.create_session(AWS_PROFILE)
    all_entries = pgp_manager.get_all_entries(session, DATA_BUCKET_NAME, PUBLIC_BUCKET_NAME)

    enhanced_entries = [enhance_entry(entry) for entry in all_entries]
    all_groups = create_groups(sort_entries(enhanced_entries))

    if os.path.exists('./build'):
        print('Build: removing old build file')
        shutil.rmtree('./build')

    print('Build: copying static assets')
    shutil.copytree('./static', './build/static')

    print('Build: creating templates')
    text_file = open("build/index.html", "w")
    text_file.write(render_page(all_groups))
    text_file.close()

    print('Build: Done!')

    pgp_manager.upload_files(session, PUBLIC_BUCKET_NAME, './build')

    print('Upload: Done!')