resource "aws_secretsmanager_secret" "confluence_backup" {
  name        = "confluence-backup"
  description = "The Confluence API token for backuping MYSPACE space"
}

data "aws_eks_cluster" "cluster" {
  name = "my-cluster"
}

data "aws_iam_openid_connect_provider" "cluster" {
  url = data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer
}

module "confluence_backup_eso" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts"
  version = "~> 6.0"

  name            = "confluence-backup-eso"
  use_name_prefix = false

  oidc_providers = {
    cluster = {
      provider_arn               = data.aws_iam_openid_connect_provider.cluster.arn
      namespace_service_accounts = ["confluence-backup:confluence-backup-eso"]
    }
  }
}

resource "aws_iam_role_policy" "confluence_backup_eso" {
  name   = "access-to-secret"
  role   = module.confluence_backup_eso.name
  policy = data.aws_iam_policy_document.confluence_backup_eso.json
}

data "aws_iam_policy_document" "confluence_backup_eso" {
  statement {
    actions = [
      "secretsmanager:GetResourcePolicy",
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:ListSecretVersionIds"
    ]
    resources = [
      aws_secretsmanager_secret.confluence_backup.arn,
    ]
  }
}

output "confluence_backup_eso" {
  value = module.confluence_backup_eso.arn
}

module "confluence_backup_s3" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts"
  version = "~> 6.0"

  name            = "confluence-backup-s3"
  use_name_prefix = false

  oidc_providers = {
    cluster = {
      provider_arn               = data.aws_iam_openid_connect_provider.cluster.arn
      namespace_service_accounts = ["confluence-backup:confluence-backup"]
    }
  }
}

resource "aws_iam_role_policy" "confluence_backup_s3" {
  name   = "access-to-s3"
  role   = module.confluence_backup_s3.name
  policy = data.aws_iam_policy_document.confluence_backup_s3.json
}

data "aws_iam_policy_document" "confluence_backup_s3" {
  statement {
    actions = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:PutObjectAcl",
        "s3:GetObjectAttributes"
    ]
    resources = ["${aws_s3_bucket.confluence_backup.arn}/*"]
  }
  statement {
    actions = [
        "s3:ListBucket"
    ]
    resources = [aws_s3_bucket.confluence_backup.arn]
  }
}

resource "aws_iam_role_policy" "confluence_backup_cf" {
  name   = "access-to-cloudfront"
  role   = module.confluence_backup_s3.name
  policy = data.aws_iam_policy_document.confluence_backup_cf.json
}

data "aws_iam_policy_document" "confluence_backup_cf" {
  statement {
    actions = [
        "cloudfront:CreateInvalidation"
    ]
    resources = [aws_cloudfront_distribution.confluence_backup.arn]
  }
}

output "confluence_backup_s3" {
  value = module.confluence_backup_s3.arn
}