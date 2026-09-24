data "aws_route53_zone" "zone" {
  name         = "confluence.backup.com."
  private_zone = false
}

resource "aws_route53_record" "confluence_backup" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = local.dns_record
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.confluence_backup.domain_name
    zone_id                = aws_cloudfront_distribution.confluence_backup.hosted_zone_id
    evaluate_target_health = false
  }
}
