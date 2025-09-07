variable "region" {
  type    = string
  default = "eu-west-2"
}

variable "tfstate_bucket_name" {
  type = string
}

variable "lock_table_name" {
  type    = string
  default = "tf-locks"
}
