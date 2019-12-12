import json
import logging.handlers
from typing import Dict

import requests
from boto3 import Session
from botocore.exceptions import ClientError
from requests.exceptions import RequestException

CHARSET = "UTF-8"


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M'
                    )

logger = logging.getLogger('securecontact.notifications')


def generate_text(heading: str, text: str) -> str:
    return f"""
    {heading}\r\n
    {text}\n
    This email was sent by the Secure Contact application
    """


def generate_html(heading: str, text: str) -> str:
    return f"""<html>
    <head></head>
    <body>
    <h1>{heading}</h1>
    <p>{text}</p>
    <p>This email was sent by the Secure Contact application using <a href='https://aws.amazon.com/ses/'>AWS SES</a></p>
    </body>
    </html>"""


def create_message(subject: str, heading: str, text: str):
    body_html = generate_html(heading, text)
    body_text = generate_text(heading, text)
    return {
        'Body': {
            'Html': {
                'Charset': CHARSET,
                'Data': body_html,
            },
            'Text': {
                'Charset': CHARSET,
                'Data': body_text,
            },
        },
        'Subject': {
            'Charset': CHARSET,
            'Data': subject,
        },
    }


def send_email(session: Session, config: Dict[str, str], message: Dict):
    ses_client = session.client('ses')
    sender = config['PRODMON_SENDER']
    recipient = config['PRODMON_RECIPIENT']
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message=message,
            Source=f'SecureDrop Monitor <{sender}>',
        )
    # TODO: use logging library instead and send logs somewhere sensible
    except ClientError as e:
        logger.error(e.response['Error']['Message'])
    else:
        logger.info('Email sent! Message ID:')
        logger.info(response['MessageId'])


def generate_card(title: str, subtitle: str) -> Dict:
    return {
        "cards": [
            {
                "header": {
                    "title": title,
                    "subtitle": subtitle
                }
            }
        ]
    }


def send_message(config: Dict[str, str], passed: bool):
    # TODO: message @all to notify when healthcheck fails
    headers = {'Content-Type': 'application/json; charset=UTF-8'}

    status = 'Status: 💚💚💚' if passed else 'Status: 💔💔💔'
    card = json.dumps(generate_card('SecureDrop Monitor', status))

    try:
        response = requests.post(url=config['PRODMON_WEBHOOK'], headers=headers, data=card)
        logger.info(f'Message sent to Hangouts Chat!')
        logger.info(f'Status code {response.status_code} returned from chat.googleapis.com')
    except RequestException as err:
        logger.error(err)
