output "ecr_repo_name" {
  value = aws_ecr_repository.app_repo.name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.app_cluster.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app_service.name
}
