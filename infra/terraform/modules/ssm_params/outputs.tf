output "param_names" {
  value = [for k, _ in aws_ssm_parameter.secret : k]
}
