# terraform/aws_ec2_example.tf
# Basic example - not production hardened. Use AWS provider v4+.
# Replace variables and add provider configuration.

resource "aws_instance" "n8n" {
  ami           = "ami-0abcdef1234567890" # Example - replace with Ubuntu AMI for your region
  instance_type = "t3.medium"
  tags = {
    Name = "n8n-server"
  }
  # Add security groups, key_name, and user_data to install docker & docker-compose
}
