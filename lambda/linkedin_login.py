import json
import os
import base64
import boto3
import requests

# Environment variables (set via Terraform)
CLIENT_ID     = os.environ["LINKEDIN_CLIENT_ID"]
CLIENT_SECRET = os.environ["LINKEDIN_CLIENT_SECRET"]
REDIRECT_URI  = os.environ["REDIRECT_URI"]

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
table    = dynamodb.Table("linkedin_users")

def parse_jwt(token: str) -> dict:
    """Decode a JWT without verifying signature to extract payload claims."""
    payload = token.split(".")[1]
    # Pad base64 if needed
    padding = "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload + padding)
    return json.loads(decoded)

def lambda_handler(event, context):
    print("=== Lambda Invocation ===")
    print(json.dumps(event, indent=2))

    # Debug environment
    print(f">> ENV CLIENT_ID: '{CLIENT_ID}'")
    print(f">> ENV REDIRECT_URI: '{REDIRECT_URI}'")

    params = event.get("queryStringParameters") or {}
    code  = params.get("code")
    state = params.get("state")
    print("Query parameters:", params)

    if not code:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'code' parameter"})
        }

    try:
        # Exchange authorization code for tokens
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
        tokens = token_res.json()
        print("Token response:", tokens)

        id_token     = tokens.get("id_token")
        access_token = tokens.get("access_token")

        # Extract user info from id_token if present
        if id_token:
            claims       = parse_jwt(id_token)
            linkedin_id  = claims.get("sub")
            first_name   = claims.get("given_name", "User")
            email        = claims.get("email")
        else:
            # Fallback to REST v2 endpoints if id_token not provided
            headers = {"Authorization": f"Bearer {access_token}"}

            profile_res = requests.get("https://api.linkedin.com/v2/me", headers=headers)
            profile_res.raise_for_status()
            profile = profile_res.json()

            email_res = requests.get(
                "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                headers=headers
            )
            email_res.raise_for_status()
            email_data = email_res.json()

            linkedin_id = profile.get("id")
            first_name  = profile.get("localizedFirstName", "User")
            email       = email_data["elements"][0]["handle~"]["emailAddress"]

        # Store or update user record in DynamoDB
        table.put_item(Item={
            "id":    linkedin_id,
            "name":  first_name,
            "email": email
        })

        # Return a simple HTML response
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

    except requests.HTTPError as err:
        print("HTTPError:", err, err.response.text)
        return {
            "statusCode": err.response.status_code,
            "body": json.dumps({"error": str(err), "details": err.response.text})
        }

    except Exception as e:
        print("Exception:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)})
        }
