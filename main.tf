// For more about Terraform using EC2: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
// Maybe one of the github actions could be terraform init so it can download AWS Ec2?

// Terraform block used to configure some high-level behaviors of Terraform
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">=0.14.9"

  backend "s3" {
    bucket =  "[Remote State Bucket Name]"
    key =     "[Remote State Bucket Key]"
    region =  "ap-northeast-2"
  }
}

// Configure the AWS Provider with Credentials
provider "aws" {
    region = "ap-northeast-2"
    access_key = ""                             // Needs to be changed
    secret_key = ""                             // Needs to be changed
}


resource "aws_instance" "my-first-server" {
  ami           = data.aws_ami.ubuntu.id        // Needs to be changed, might be something like "ami-239842dafklfh832"
  instance_type = "t3.micro"                    // Needs to be changed

  tags = { Name = "NS-CQ-EC2INSTANCE" }
}