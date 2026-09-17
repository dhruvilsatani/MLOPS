resource "aws_ecr_repository" "ml_app" {
  name                 = "ml-app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }
}