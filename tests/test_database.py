import unittest
import boto3
import time

from src.monitor import create_item
from src.dynamo import write_to_database, read_from_database

# !! ~~ Only use this module for local testing ~~ !!


# Use the provided CloudFormation template to create the table in AWS environments.
# If you update this then be sure to also update the CloudFormation definition.
def create_table(client, table_name: str):
    if table_name not in client.list_tables().get('TableNames'):
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'CheckTime',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'Outcome',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'CheckTime',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'Outcome',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )


def update_ttl(client, table_name: str):
    ttl_status = client.describe_time_to_live(TableName=table_name)\
        .get('TimeToLiveDescription')\
        .get('TimeToLiveStatus')

    # AWS returns an error if you try to enable ttl if it is already enabled.
    # We therefore need to check the status before trying to enable it... >.<
    if ttl_status != 'ENABLED':
        client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'AttributeName': 'ExpirationTime',
                'Enabled': True
            }
        )


def delete_table(client, table_name: str):
    client.delete_table(TableName=table_name)


def get_table_status(dynamodb, table_name: str):
    table_status = dynamodb.describe_table(TableName=table_name).get('Table').get('TableStatus')
    print("Table status:", table_status)


# If an item that has the same primary key as the new item already exists in the
# specified table then the new item completely replaces the existing item.
def create_records(dynamodb, table_name: str):
    current_time = int(time.time())
    monitor_table = dynamodb.Table(table_name)
    monitor_table.put_item(Item=create_item(current_time - 9100, True))
    monitor_table.put_item(Item=create_item(current_time - 6100, True))
    monitor_table.put_item(Item=create_item(current_time - 3100, True))
    monitor_table.put_item(Item=create_item(current_time - 900, True))
    monitor_table.put_item(Item=create_item(current_time - 600, True))
    monitor_table.put_item(Item=create_item(current_time - 300, True))


# !! ~~ Only use this module for local testing ~~ !!
# Comment out the line below then run the suite to create local DynamoDB tables
@unittest.skip('these tests are for DEV only and require local dynamodb to be running')
class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self.table_name = 'MonitorHistory-DEV'
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-west-1', endpoint_url="http://localhost:8000")
        self.client = boto3.client('dynamodb', region_name='eu-west-1', endpoint_url="http://localhost:8000")

        # !! ~~ DELETING THE TABLE ~~ !!
        # Comment out the line below to retain the table
        delete_table(self.client, self.table_name)

        # !! ~~ CREATING THE TABLE ~~ !!
        # DEV table based on CFN template with sample records
        create_table(self.client, self.table_name)
        update_ttl(self.client, self.table_name)
        create_records(self.dynamodb, self.table_name)

    def tearDown(self) -> None:
        pass

    def test_read_and_write(self):
        first_result = read_from_database(self.dynamodb, self.table_name)
        self.assertEqual(6, first_result.get('ScannedCount'))
        self.assertEqual(4, len(first_result.get('Items')))

        new_item = create_item(int(time.time()), True)
        write_to_database(self.dynamodb, self.table_name, new_item)

        second_result = read_from_database(self.dynamodb, self.table_name)
        self.assertEqual(7, second_result.get('ScannedCount'))
        self.assertEqual(5, len(second_result.get('Items')))


if __name__ == '__main__':
    unittest.main()
