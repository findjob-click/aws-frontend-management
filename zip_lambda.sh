#!/bin/bash
set -e

echo "📦 Creating fresh Lambda package..."

# Clean previous temp
rm -rf lambda_temp
mkdir -p lambda_temp

# Install requests and dependencies directly into lambda_temp
pip install requests -t lambda_temp/ > /dev/null

# Copy Lambda function to the same root
cp lambda/linkedin_login.py lambda_temp/

# Zip everything inside lambda_temp
cd lambda_temp
zip -r ../lambda/lambda.zip . > /dev/null
cd ..

# Clean up
rm -rf lambda_temp

echo "✅ Lambda zip created at lambda/lambda.zip"
