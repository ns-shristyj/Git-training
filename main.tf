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

  # backend "s3" {
  #   bucket =  "seceng-terraform-state"
  #   key =     "[Remote State Bucket Key]"
  #   region =  "ap-northeast-2"
  # }
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

  tags = { Name = "NS-CQ-EC2INSTANCE-UBUNTU" }
}

resource "aws_vpc" "AWS-VPC" {
  cidr_block = "10.0.0.0/16"
  instance_tenancy = "dedicated"
  tags = { name = "NS-CQUINLAN-AWS-VPC" }
}
resource "aws_subnet" "AWS-SUBNET-1" {
  vpc_id = "temp id" // ${aws_vpc.AWS-VPC.id}
  // make sure the CIDR block falls within the VPC range
  cidr_block = "10.0.1.0/24"
  tags = { name = "NS-CQUINLAN-SUBNET" }
}