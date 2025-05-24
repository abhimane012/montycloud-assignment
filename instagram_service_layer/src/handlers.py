import os
import json
import uuid
import boto3
from boto3.dynamodb.conditions import Attr

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ.get('BUCKET_NAME')
TABLE_NAME = os.environ.get('TABLE_NAME')

def upload_image(event, context):
    body = json.loads(event['body'])
    image_data = body['image_data']
    metadata = body['metadata']
    image_id = str(uuid.uuid4())

    s3.put_object(Bucket=BUCKET_NAME, Key=image_id, Body=image_data)
    image_url = f"s3://{BUCKET_NAME}/{image_id}"
    metadata['image_url'] = image_url

    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item={**metadata, 'image_id': image_id})

    return {
        'statusCode': 200,
        'body': json.dumps({'image_id': image_id})
    }

def list_images(event, context):
    body = json.loads(event['body'])
    last_evaluated_key = body['last_evaluated_key']
    params = event.get('queryStringParameters') or {}
    table = dynamodb.Table(TABLE_NAME)
    tag = params.get('tag', None)
    caption = params.get('caption', None)
    filter_expression = None

    if tag and caption:
        filter_expression = Attr('tags').eq(tag) & Attr('caption').eq(caption)
    elif tag:
        filter_expression = Attr('tags').eq(tag)
    elif caption:
        filter_expression = Attr('caption').eq(caption)

    scan_kwargs = {
        'Limit': 15
    }

    if filter_expression:
        scan_kwargs['FilterExpression'] = filter_expression

    if last_evaluated_key:
        scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

    response = table.scan(**scan_kwargs)
    
    result = {
        'items': response.get('Items', []),
        'last_evaluated_key': response.get('LastEvaluatedKey')
    }

    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }

def view_image(event, context):
    image_id = event['pathParameters']['image_id']
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': image_id},
        ExpiresIn=3600
    )
    return {
        'statusCode': 200,
        'body': json.dumps({'url': url})
    }

def delete_image(event, context):
    image_id = event['pathParameters']['image_id']

    s3.delete_object(Bucket=BUCKET_NAME, Key=image_id)
    table = dynamodb.Table(TABLE_NAME)
    table.delete_item(Key={'image_id': image_id})

    return {
        'statusCode': 200,
        'body': json.dumps({'deleted': image_id})
    }
