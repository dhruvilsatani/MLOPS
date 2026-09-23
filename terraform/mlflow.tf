variable "mlflow_db_password" {
  type      = string
  sensitive = true
}

resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "ml-app-mlflow-artifacts"
}

resource "aws_s3_bucket_versioning" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_db_subnet_group" "mlflow" {
  name       = "mlflow-db-subnets"
  subnet_ids = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

resource "aws_security_group" "mlflow_db" {
  name   = "mlflow-db"
  vpc_id = aws_vpc.ml_app.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_db_instance" "mlflow" {
  identifier             = "mlflow-db"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  db_name                = "mlflow"
  username               = "mlflow"
  password               = var.mlflow_db_password
  db_subnet_group_name   = aws_db_subnet_group.mlflow.name
  vpc_security_group_ids = [aws_security_group.mlflow_db.id]
  skip_final_snapshot    = true
}

output "mlflow_db_endpoint" {
  value = aws_db_instance.mlflow.endpoint
}