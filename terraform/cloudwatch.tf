resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/medicare-task"
  #retention_in_days = 7
}
