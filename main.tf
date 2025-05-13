data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name        = "LambdaDynamoDBPolicy"
  description = "Allow Lambda to write to DynamoDB"
  policy      = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "dynamodb:PutItem"
        ],
        Effect   = "Allow",
        Resource = aws_dynamodb_table.users.arn
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "lambda_dynamodb_access" {
  name       = "lambda-dynamodb-access"
  roles      = [aws_iam_role.lambda_exec.name]
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

resource "aws_lambda_function" "linkedin_login" {
  filename         = "${path.module}/lambda/lambda.zip"
  function_name    = "linkedin_login"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "linkedin_login.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = filebase64sha256("${path.module}/lambda/lambda.zip")
  environment {
  variables = {
    LINKEDIN_CLIENT_ID     = var.linkedin_client_id
    LINKEDIN_CLIENT_SECRET = var.linkedin_client_secret
    REDIRECT_URI           = "https://ki1y9x9avk.execute-api.us-east-1.amazonaws.com"
  }
}
}

resource "aws_apigatewayv2_api" "http_api" {
  name          = "linkedin-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id             = aws_apigatewayv2_api.http_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.linkedin_login.invoke_arn
  integration_method = "POST"
  payload_format_version = "2.0"
}

# api gateway route (clearly explicit)
resource "aws_apigatewayv2_route" "linkedin_callback" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /linkedin/callback"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.linkedin_login.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

resource "aws_dynamodb_table" "users" {
  name           = "linkedin_users"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }
}
