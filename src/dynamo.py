import decimal
import json
import numbers
import time
from collections.abc import Iterable, Mapping, ByteString, Set
from typing import Dict, List

from boto3.dynamodb.conditions import Attr


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


# For types that involve numbers, it is recommended that Decimal
# objects are used to be able to round-trip the Python type...
# We are using a lightweight serializer from author of Bloop:
# https://github.com/boto/boto3/issues/369#issuecomment-330136042
def dump_to_dynamodb(item):
    context = decimal.Context(
        Emin=-128, Emax=126, rounding=None, prec=38,
        traps=[decimal.Clamped, decimal.Overflow, decimal.Underflow]
    )

    # don't catch str/bytes with Iterable check below;
    # don't catch bool with numbers.Number
    if isinstance(item, (str, ByteString, bool)):
        return item

    # ignore inexact, rounding errors
    if isinstance(item, numbers.Number):
        return context.create_decimal(item)

    elif isinstance(item, Dict):
        for key, value in item.items():
            item[key] = dump_to_dynamodb(value)
        return item

    # mappings are also Iterable
    elif isinstance(item, Mapping):
        return {
            key: dump_to_dynamodb(value)
            for key, value in item.values()
        }

    # dynamodb.TypeSerializer checks isinstance(o, Set)
    # so we cannot handle this as a list
    elif isinstance(item, Set):
        return set(map(dump_to_dynamodb, item))

    # may not be a literal instance of List
    elif isinstance(item, Iterable):
        return list(map(dump_to_dynamodb, item))

    # datetime, custom object, None
    return item


def write_to_database(dynamodb, table_name: str, item: Dict[str, str]):
    # TTL attributes must be in seconds and use the epoch time format
    # Return the time in seconds since the epoch as a floating point number
    monitor_table = dynamodb.Table(table_name)
    monitor_table.put_item(Item=dump_to_dynamodb(item))


def read_from_database(dynamodb, table_name: str) -> List[Dict[str, str]]:
    table = dynamodb.Table(table_name)
    current_time = int(time.time())
    cutoff_time = current_time - 6000
    filter_expression = Attr('CheckTime').between(cutoff_time, current_time)

    response = table.scan(
        FilterExpression=filter_expression,
        Limit=10
    )
    return response['Items']
