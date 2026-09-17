# Security group for the ALB — allow inbound HTTP from anywhere
resource "aws_security_group" "alb" {
  name        = "ml-app-alb-sg"
  description = "Allow HTTP to the ALB"
  vpc_id      = aws_vpc.ml_app.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ml-app-alb-sg"
  }
}

# The ALB itself
resource "aws_lb" "ml_app" {
  name               = "ml-app-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

# Where traffic actually gets sent — targets the EKS node's IP + NodePort
resource "aws_lb_target_group" "ml_app" {
  name        = "ml-app-tg"
  port        = 30353
  protocol    = "HTTP"
  vpc_id      = aws_vpc.ml_app.id
  target_type = "ip"

  health_check {
    path                = "/healthz"
    port                = "30353"
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

# Register the EKS node as a target
resource "aws_lb_target_group_attachment" "ml_app_node" {
  target_group_arn = aws_lb_target_group.ml_app.arn
  target_id        = "172.18.0.4"
  port             = 30353
}

# The listener — "traffic on port 80 goes to the target group"
resource "aws_lb_listener" "ml_app" {
  load_balancer_arn = aws_lb.ml_app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ml_app.arn
  }
}

output "alb_dns_name" {
  value = aws_lb.ml_app.dns_name
}