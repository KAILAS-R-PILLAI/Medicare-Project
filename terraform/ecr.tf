resource "aws_ecr_repository" "app_repo" {
  name = var.ecr_repo_name
}
