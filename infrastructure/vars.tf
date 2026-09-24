variable "account" {}
variable "role_name" {}
variable "region" {}

variable "tags" {
  type = map(string)
  default = {
    environment = "production"
  }
}
