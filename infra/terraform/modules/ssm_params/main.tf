resource "aws_ssm_parameter" "secret" {
  for_each = var.secrets
  name     = "${var.path_prefix}/${each.key}"
  type     = "SecureString"
  value    = each.value
}
