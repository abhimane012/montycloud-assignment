import json
import base64
import boto3
import os
import pytest
from uuid import uuid4
from moto import mock_aws
from src import handlers

BUCKET_NAME = "test-bucket"
TABLE_NAME = "images-table"

@pytest.fixture(scope="function", autouse=True)
def aws_mock_env():
    os.environ['BUCKET_NAME'] = BUCKET_NAME
    os.environ['TABLE_NAME'] = TABLE_NAME

    with mock_aws():
        # Setup S3
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET_NAME)

        # Setup DynamoDB
        dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "image_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "image_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        yield


def test_upload_image():
    image_data = base64.b64encode(b"test-image").decode()
    metadata = {
        "tag": "sunset",
        "caption": "Beautiful beach sunset"
    }

    event = {
        "body": json.dumps({
            "image_data": image_data,
            **metadata
        })
    }

    response = handlers.upload_image(event, None)
    body = json.loads(response['body'])

    assert response['statusCode'] == 200
    assert 'image_id' in body


def test_list_images():
    # First, upload an image
    test_upload_image()

    event = {
        "queryStringParameters": {
            "tag": "sunset",
            "caption": "Beautiful beach sunset"
        }
    }

    response = handlers.list_images(event, None)
    body = json.loads(response['body'])

    assert response['statusCode'] == 200
    assert 'items' in body


def test_view_image():
    # First, upload an image
    image_data = base64.b64encode(b"another-image").decode()
    metadata = {
        "tag": "sunset",
        "caption": "Another caption"
    }

    event_upload = {
        "body": json.dumps({
            "image_data": image_data,
            "metadata": metadata
        })
    }

    upload_response = handlers.upload_image(event_upload, None)
    image_id = json.loads(upload_response['body'])['image_id']

    event = {
        "pathParameters": {
            "image_id": image_id
        }
    }

    response = handlers.view_image(event, None)
    body = json.loads(response['body'])

    assert response['statusCode'] == 200
    assert 'url' in body
    assert body['url'].startswith("https://")


def test_delete_image():
    # First, upload an image
    image_data = base64.b64encode(b"delete-me").decode()
    metadata = {
        "tag": "sunset",
        "caption": "To be deleted"
    }

    event_upload = {
        "body": json.dumps({
            "image_data": image_data,
            "metadata": metadata
        })
    }

    upload_response = handlers.upload_image(event_upload, None)
    image_id = json.loads(upload_response['body'])['image_id']

    event_delete = {
        "pathParameters": {
            "image_id": image_id
        }
    }

    response = handlers.delete_image(event_delete, None)
    body = json.loads(response['body'])

    assert response['statusCode'] == 200
    assert body['deleted'] == image_id
