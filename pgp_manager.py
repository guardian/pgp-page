import boto3
import os
import json

from urllib import parse
from typing import Dict, List, Any


class Entry:
    def __init__(self, name, publickey, fingerprint):
        self.name = name
        self.publickey = publickey
        self.fingerprint = fingerprint

    def __str__(self):
        return f'{str(self.__class__)}: {str(self.__dict__)}'

    def __eq__(self, other):
        if not isinstance(other, Entry):
            return NotImplemented

        return self.name == other.name and self.publickey == other.publickey and self.fingerprint == other.fingerprint

    def __hash__(self):
        # Make class instances usable as items in hashable collections
        return hash((self.name, self.publickey, self.fingerprint))


# assumes the uploaded public key is named after the contact
def parse_name(key: str) -> str:
    return key.replace('PublicKeys/', '').replace('.pub.txt', '')


def fetch_fingerprint(s3_client, bucket: str, name: str) -> str:
    key = f'Fingerprints/{name}.fpr.txt'
    s3_obj = s3_client.get_object(Bucket=bucket, Key=key)
    return s3_obj['Body'].read()


def generate_entry(s3_client, bucket: str, key: str) -> Entry:
    contact_name = parse_name(key)
    key_url = parse.quote(key)
    fingerprint = fetch_fingerprint(s3_client, bucket, contact_name)
    return Entry(contact_name.title(), key_url, fingerprint)


def create_s3_client(profile):
    session = boto3.Session(profile_name=profile)
    return session.client('s3')


def get_matching_s3_objects(s3_client, bucket: str, prefix: str) -> List[Dict[str, Any]]:
    kwargs = {'Bucket': bucket}

    while True:
        # The S3 API response is a large blob of metadata.
        # 'Contents' contains information about the listed objects.
        resp = s3_client.list_objects_v2(**kwargs)

        try:
            contents = resp['Contents']
        except KeyError:
            return

        for obj in contents:
            key = obj['Key']
            if key.startswith(prefix):
                yield obj

        # The S3 API is paginated, returning up to 1000 keys at a time.
        # Pass the continuation token into the next response, until we
        # reach the final page (where this field will be missing).
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break


def get_matching_s3_keys(s3_client, bucket: str, prefix: str) -> List[str]:
    for obj in get_matching_s3_objects(s3_client, bucket, prefix):
        yield obj['Key']


# should copy a list of s3 objects from one bucket to another, preserving the directory structure
def copy_keys_to_public_bucket(s3_client, source_bucket: str, destination_bucket: str, public_keys: List[str]) -> None:
    # should also set public read on the object
    # could we set a lifecycle on the bucket to deal with old keys?
    for key in public_keys:
        copy_source = {
            'Bucket': source_bucket,
            'Key': key
        }
        s3_client.copy(copy_source, destination_bucket, key)


# fetch all of the required data from S3 and return a List containing an Entry for each contact
def main() -> List[Entry]:
    config_path = os.path.expanduser('~/.gu/secure-contact.json')
    config = json.load(open(config_path))

    DATA_BUCKET_NAME = config['DATA_BUCKET_NAME']
    PUBLIC_BUCKET_NAME = config['PUBLIC_BUCKET_NAME']
    AWS_PROFILE = config['AWS_PROFILE']

    # create the client that we will use to access AWS S3
    client = create_s3_client(AWS_PROFILE)
    public_keys = list(get_matching_s3_keys(client, DATA_BUCKET_NAME, 'PublicKeys'))

    copy_keys_to_public_bucket(client, DATA_BUCKET_NAME, PUBLIC_BUCKET_NAME, public_keys)
    return [generate_entry(client, DATA_BUCKET_NAME, key) for key in public_keys]


if __name__ == "__main__":
    main()
