variable "subnet_ids" {
  type = list(string)
  default = ["subnet-0e9bb756b190aeda6"]
}

variable "security_group_ids" {
  type = list(string)
  default = ["sg-0564fef9413077c4b"]
}

variable "ecr_repo_name" {
  type    = string
  default = "medicare-app-repo"
}
