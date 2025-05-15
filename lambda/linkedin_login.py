import json
import os
import boto3
import requests

# Environment variables
CLIENT_ID     = os.environ["LINKEDIN_CLIENT_ID"]
CLIENT_SECRET = os.environ["LINKEDIN_CLIENT_SECRET"]
REDIRECT_URI  = os.environ["REDIRECT_URI"]

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table("linkedin_users")

def lambda_handler(event, context):
    print("=== Lambda Invocation ===")
    print("Event:", json.dumps(event, indent=2))

    # Debug env
    print(f">> ENV CLIENT_ID: '{CLIENT_ID}' <END>")
    print(f">> ENV REDIRECT_URI: '{REDIRECT_URI}' <END>")

    try:
        # Extract query parameters
        params = event.get("queryStringParameters") or {}
        code  = params.get("code")
        state = params.get("state")
        print("Query params:", params)

        if not code:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'code' in query string"})
            }

        # (Optional) verify state here if you’re persisting it

        # Exchange code for access token
        token_res = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  REDIRECT_URI,
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET
            }
        )
        token_res.raise_for_status()
        token_json = token_res.json()
        access_token = token_json.get("access_token")
        print("Token response:", token_json)

        if not access_token:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "No access_token in LinkedIn response"})
            }

        # Fetch profile
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_res = requests.get("https://api.linkedin.com/v2/me", headers=headers)
        profile_res.raise_for_status()
        profile = profile_res.json()
        print("Profile data:", profile)

        # Fetch email
        email_res = requests.get(
            "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
            headers=headers
        )
        email_res.raise_for_status()
        email_data = email_res.json()
        print("Email data:", email_data)

        linkedin_id = profile.get("id")
        first_name  = profile.get("localizedFirstName", "User")
        email       = email_data["elements"][0]["handle~"]["emailAddress"]

        # Store in DynamoDB
        table.put_item(Item={
            "id":    linkedin_id,
            "name":  first_name,
            "email": email
        })

        # Return HTML
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": (
                "<!DOCTYPE html>"
                "<html><body>"
                f"<h1>Hello {first_name}, welcome to FindJob.click!</h1>"
                "</body></html>"
            )
        }

    except requests.HTTPError as http_err:
        print("HTTPError:", http_err, http_err.response.text)
        return {
            "statusCode": http_err.response.status_code,
            "body": json.dumps({"error": str(http_err), "details": http_err.response.text})
        }

    except Exception as e:
        print("Exception:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)})
        }
