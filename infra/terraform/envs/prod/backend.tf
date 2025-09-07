terraform {
  backend "s3" {
    bucket         = "kris-tfstate-eu-west-2" # ← z bootstrapu
    key            = "prod/terraform.tfstate"
    region         = "eu-west-2"
    dynamodb_table = "tf-locks"
    encrypt        = true
  }
}
