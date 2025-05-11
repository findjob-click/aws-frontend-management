#!/bin/bash
set -e

echo "📦 Creating fresh Lambda package..."

# Clean previous temp
rm -rf lambda_temp
mkdir -p lambda_temp/python

# Install dependencies
pip install requests -t lambda_temp/python > /dev/null

# Copy Lambda function
cp lambda/linkedin_login.py lambda_temp/python/

# Zip it
cd lambda_temp
zip -r ../lambda/lambda.zip . > /dev/null
cd ..

# Clean up temp folder
rm -rf lambda_temp

echo "✅ Lambda zip updated at lambda/lambda.zip"
