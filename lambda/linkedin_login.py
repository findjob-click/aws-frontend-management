import json
import os
import boto3
import requests

# Environment variables
CLIENT_ID = os.environ["LINKEDIN_CLIENT_ID"]
CLIENT_SECRET = os.environ["LINKEDIN_CLIENT_SECRET"]
REDIRECT_URI = os.environ["REDIRECT_URI"]

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('linkedin_users')

def lambda_handler(event, context):
    print("=== Lambda Invocation ===")
    print("Event:", json.dumps(event))

    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        code = query_params.get("code")

        if not code:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing OAuth code parameter from LinkedIn."})
            }

        # Exchange authorization code for access token
        token_response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            }
        )

        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")

        if not access_token:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Failed to retrieve access token from LinkedIn."})
            }

        headers = {"Authorization": f"Bearer {access_token}"}

        # Fetch LinkedIn profile
        profile_response = requests.get("https://api.linkedin.com/v2/me", headers=headers)
        profile_response.raise_for_status()
        profile_data = profile_response.json()

        # Fetch email from LinkedIn
        email_response = requests.get(
            "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
            headers=headers
        )
        email_response.raise_for_status()
        email_data = email_response.json()

        # Extract user information
        linkedin_id = profile_data.get("id")
        first_name = profile_data.get("localizedFirstName", "User")
        email = email_data["elements"][0]["handle~"]["emailAddress"]

        # Store user data in DynamoDB
        table.put_item(Item={
            "id": linkedin_id,
            "name": first_name,
            "email": email
        })

        # Personalized HTML response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": f"<html><body><h1>Hello {first_name}, welcome to findjob.click!</h1></body></html>"
        }

    except requests.HTTPError as http_err:
        print("HTTP error occurred:", str(http_err))
        return {
            "statusCode": http_err.response.status_code,
            "body": json.dumps({"error": str(http_err), "details": http_err.response.text})
        }

    except Exception as e:
        print("General exception occurred:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)})
        }
