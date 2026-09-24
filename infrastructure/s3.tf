resource "aws_s3_bucket" "confluence_backup" {
  bucket = "my-confluence-backup"

  tags = var.tags
}

resource "aws_s3_bucket_policy" "confluence_backup" {
  bucket = aws_s3_bucket.confluence_backup.id

  policy = data.aws_iam_policy_document.confluence_backup.json
}

data "aws_iam_policy_document" "confluence_backup" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.confluence_backup.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = [aws_cloudfront_origin_access_identity.confluence_backup.iam_arn]
    }
  }

  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.confluence_backup.arn]

    principals {
      type        = "AWS"
      identifiers = [aws_cloudfront_origin_access_identity.confluence_backup.iam_arn]
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "confluence_backup" {
  bucket = aws_s3_bucket.confluence_backup.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}
