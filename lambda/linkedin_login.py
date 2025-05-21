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
    code   = params.get("code")
    state  = params.get("state")
    print("Query parameters:", params)

    if not code:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'code' parameter"})
        }

    try:
        # 1️⃣ Exchange authorization code for tokens
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

        # 2️⃣ Try extracting profile from id_token
        if id_token:
            claims      = parse_jwt(id_token)
            linkedin_id = claims.get("sub")
            first_name  = claims.get("given_name", "")
            last_name   = claims.get("family_name", "")
            full_name   = claims.get("name", f"{first_name} {last_name}".strip())
            email       = claims.get("email")
            email_verified = claims.get("email_verified", False)
            picture_url = claims.get("picture")
            locale      = claims.get("locale")

        else:
            # 3️⃣ Fallback: call the UserInfo endpoint
            userinfo_res = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            userinfo_res.raise_for_status()
            user = userinfo_res.json()
            print("UserInfo:", user)

            linkedin_id    = user.get("sub")
            first_name     = user.get("given_name", "")
            last_name      = user.get("family_name", "")
            full_name      = user.get("name", f"{first_name} {last_name}".strip())
            email          = user.get("email")
            email_verified = user.get("email_verified", False)
            picture_url    = user.get("picture")
            locale         = user.get("locale")

        # 4️⃣ Store into DynamoDB (schemaless)
        table.put_item(Item={
            "id":             linkedin_id,
            "first_name":     first_name,
            "last_name":      last_name,
            "full_name":      full_name,
            "email":          email,
            "email_verified": email_verified,
            "picture_url":    picture_url,
            "locale":         locale
        })

        # 5️⃣ Render full HTML welcome page
        html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8"/>
    <title>Welcome!</title>
  </head>
  <body>
    <h1>Welcome, {full_name}!</h1>
    <img src="{picture_url}" alt="Profile Picture" width="100"/><br/>
    <p><strong>ID:</strong> {linkedin_id}</p>
    <p><strong>First Name:</strong> {first_name}</p>
    <p><strong>Last Name:</strong> {last_name}</p>
    <p><strong>Email:</strong> {email} {'(verified)' if email_verified else '(unverified)'}</p>
    <p><strong>Locale:</strong> {locale}</p>
  </body>
</html>"""

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": html
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
