# Create the bucket (without website block)
resource "aws_s3_bucket" "website" {
  bucket         = "findjob.click"
  force_destroy  = true
}

# Add new website config
resource "aws_s3_bucket_website_configuration" "website_config" {
  bucket = aws_s3_bucket.website.id

  index_document {
    suffix = "index.html"
  }
}

# Ownership controls
resource "aws_s3_bucket_ownership_controls" "website" {
  bucket = aws_s3_bucket.website.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Public access settings
resource "aws_s3_bucket_public_access_block" "website" {
  bucket                  = aws_s3_bucket.website.id
  block_public_acls       = false
  block_public_policy     = false
  restrict_public_buckets = false
  ignore_public_acls      = false
}

# Upload the file
resource "aws_s3_object" "index_html" {
  bucket       = aws_s3_bucket.website.id
  key          = "index.html"
  source       = "${path.module}/index.html"
  content_type = "text/html"
}
