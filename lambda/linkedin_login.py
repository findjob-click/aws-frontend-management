import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('linkedin_users')

def lambda_handler(event, context):
    name = "Test User"
    linkedin_id = "test-123"

    # Save to DynamoDB (mocked for now)
    table.put_item(Item={"id": linkedin_id, "name": name})

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": f"<html><body><h1>Hello {name}, welcome to findjob.click!</h1></body></html>"
    }
