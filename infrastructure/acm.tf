resource "aws_acm_certificate" "confluence_backup" {
  provider          = aws.us_east_1
  domain_name       = local.dns_record
  validation_method = "DNS"
}

resource "aws_route53_record" "confluence_backup_validation" {
  for_each = {
    for dvo in aws_acm_certificate.confluence_backup.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.zone.zone_id
}

resource "aws_acm_certificate_validation" "confluence_backup" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.confluence_backup.arn
  validation_record_fqdns = [for record in aws_route53_record.confluence_backup_validation : record.fqdn]
}
