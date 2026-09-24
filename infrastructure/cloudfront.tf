resource "aws_cloudfront_origin_access_identity" "confluence_backup" {
  comment = "Confluence Backup static website"
}

resource "aws_cloudfront_function" "access" {
  name    = "vpn-office-access"
  runtime = "cloudfront-js-2.0"
  comment = "The function to restrict access to VPN and offices only"
  publish = true
  code    = templatefile("${path.module}/files/cf-function.tmpl", {cidr_list=flatten(["0.0.0.0/0"])}) # setup your whitelist here
}

resource "aws_cloudfront_distribution" "confluence_backup" {
  origin {
    domain_name = aws_s3_bucket.confluence_backup.bucket_regional_domain_name
    origin_id   = local.s3_origin_id

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.confluence_backup.cloudfront_access_identity_path
    }
  }

  enabled                  = true
  is_ipv6_enabled          = false
  comment                  = "Confluence Backup static website"
  default_root_object      = "index.html"
  price_class              = "PriceClass_100"

  aliases = [local.dns_record]

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = local.s3_origin_id
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.access.arn
    }
  }

  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.confluence_backup.arn
    ssl_support_method  = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
      locations        = []
    }
  }

  tags = {
    Name = "Confluence Mirror"
  }
}
