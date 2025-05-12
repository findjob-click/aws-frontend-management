import json
import os
import boto3
import requests

# Environment variables
CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('linkedin_users')


def lambda_handler(event, context):
    print("=== Lambda Invocation ===")
    print("Full Event:", json.dumps(event))

    try:
        # Parse query parameters
        query = event.get('queryStringParameters', {}) or {}
        print("Query Parameters:", query)

        code = query.get("code")
        if not code:
            return {
                "statusCode": 400,
                "body": "Missing 'code' parameter from LinkedIn."
            }

        print("Received code:", code)
        print("Using redirect URI:", REDIRECT_URI)

        # Exchange code for access token
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        print("ENV: CLIENT_ID =", CLIENT_ID)
        print("ENV: CLIENT_SECRET =", CLIENT_SECRET[:4] + "...")
        print("ENV: REDIRECT_URI =", REDIRECT_URI)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        print("Sending token request to LinkedIn...")
        token_res = requests.post(token_url, data=payload, headers=headers)
        print("Token response status:", token_res.status_code)

        if token_res.status_code != 200:
            print("Token response body:", token_res.text)
            return {
                "statusCode": 401,
                "body": f"Token request failed: {token_res.text}"
            }

        token_data = token_res.json()
        print("Token data:", token_data)

        access_token = token_data.get("access_token")
        if not access_token:
            return {
                "statusCode": 401,
                "body": f"Access token missing in response: {token_data}"
            }

        # Fetch profile and email from LinkedIn
        profile_url = "https://api.linkedin.com/v2/me"
        email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        profile_res = requests.get(profile_url, headers=auth_headers)
        profile_data = profile_res.json()
        print("Profile data:", profile_data)

        email_res = requests.get(email_url, headers=auth_headers)
        email_data = email_res.json()
        print("Email data:", email_data)

        linkedin_id = profile_data.get("id")
        first_name = profile_data.get("localizedFirstName", "User")
        email = email_data["elements"][0]["handle~"]["emailAddress"]

        # Store in DynamoDB
        table.put_item(Item={
            "id": linkedin_id,
            "name": first_name,
            "email": email
        })

        # Return a personalized HTML response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": f"<html><body><h1>Hello {first_name}, welcome to findjob.click!</h1></body></html>"
        }

    except Exception as e:
        print("Exception occurred:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
    