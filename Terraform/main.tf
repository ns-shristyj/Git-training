// For more about Terraform using EC2: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
// WARNING
// ALWAYS MAKE SURE TO DESTROY TERRAFORM AWS EC2 INSTANCE TO AVOID BILLING ISSUES
// WARNING
// WARNING
// ALWAYS MAKE SURE TO DESTROY TERRAFORM AWS EC2 INSTANCE TO AVOID BILLING ISSUES


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
    bucket =  "seceng-terraform-state"
    key =     "terraform.tfstate"
    region =  "ap-northeast-2"
  }
}

// Configure the AWS Provider with Credentials
provider "aws" {
    region = "ap-northeast-2"
}

// Create the VPC
resource "aws_vpc" "AWS-VPC" {
  cidr_block        = "10.0.0.0/16"
  instance_tenancy  = "default"
  tags              = { name = "NS-CQUINLAN-AWS-VPC" }
}
// Create a Internet Gateway
resource "aws_internet_gateway" "gw" {
  vpc_id = "${aws_vpc.AWS-VPC.id}"
  tags = { name = "CQUINLAN-GATEWAY"}
}

// Create a Custom Route Table 
resource "aws_route_table" "ns-cquinlan-route_table" {
  vpc_id              = "${aws_vpc.AWS-VPC.id}"
  route {
    cidr_block        = "0.0.0.0/0"
    gateway_id        = "${aws_internet_gateway.gw.id}" 
  }
  route {
    ipv6_cidr_block   = "::/0"
    gateway_id        = "${aws_internet_gateway.gw.id}"
  }
}

// Create a Subnet
resource "aws_subnet" "AWS-SUBNET-1" {
  vpc_id            = "${aws_vpc.AWS-VPC.id}"
  // Make sure the CIDR block falls within the VPC range
  cidr_block        = "10.0.1.0/24"
  availability_zone = "ap-northeast-2a"
  tags              = { name = "NS-CQUINLAN-SUBNET-1" }
}

// Associating the Subnet with the Route Table
resource "aws_route_table_association" "a" {
  subnet_id       = "${aws_subnet.AWS-SUBNET-1.id}"
  route_table_id  = "${aws_route_table.ns-cquinlan-route_table.id}"
}

// Create a Security Group
resource "aws_security_group" "allow_web" {
  name        = "allow_web_traffic"
  description = "Allow TLS inbound traffic and all outbound traffic"
  vpc_id      = aws_vpc.AWS-VPC.id
  tags = { Name = "allow_WEB" }
}

// IPv4 - Security Group
resource "aws_vpc_security_group_ingress_rule" "allow_web_ipv4-1" {
  description       = "HTTPS"
  security_group_id = aws_security_group.allow_web.id
  cidr_ipv4         = aws_vpc.AWS-VPC.cidr_block                   // this is responsible for which IP addresses can come into the Network
  from_port         = 443
  ip_protocol       = "tcp"
  to_port           = 443 
}
resource "aws_vpc_security_group_ingress_rule" "allow_web_ipv4-2" {
  description       = "ALT HTTPS"
  security_group_id = aws_security_group.allow_web.id
  cidr_ipv4         = aws_vpc.AWS-VPC.cidr_block                   // this is responsible for which IP addresses can come into the Network
  from_port         = 8443
  ip_protocol       = "tcp"
  to_port           = 8443 
}

// Egress - Security Group
resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.allow_web.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # semantically equivalent to all ports
}

// Create a Network Interface with an IP in the subnet
resource "aws_network_interface" "net_face" {
  subnet_id       = aws_subnet.AWS-SUBNET-1.id
  private_ips     = ["10.0.1.50"]
  security_groups = [aws_security_group.allow_web.id]
}

// Assigning a Elastic IP to the Network Interface
resource "aws_eip" "EIP-1" {
  network_interface         = "${aws_network_interface.net_face.id}"
  associate_with_private_ip = "10.0.1.50"
}

// Create Ubuntu Server and install Cobalt Strike
resource "aws_instance" "cobalt" {
  ami               = "ami-0f3a440bbcff3d043"
  instance_type     = "t2.medium"
  availability_zone = "ap-northeast-2a"
  key_name          = "conor-intern-key-pair"

  network_interface {
    device_index          = 0
    network_interface_id  = aws_network_interface.net_face.id
  }

// This needs to be changed to be right. Example run of commands below.
  # user_data = <<-EOF
  #             #!/bin/bash
  #             sudo apt update -y
  #             sudo apt install cobalt_strike -y
  #             sudo systelctl start cobalt_strike
  #             sudo bash -c 'echo your very first web server > /var/www/html/index.html'
  #             EOF
}

# Useful Commands:
output "server_public_ip" {
  value = aws_eip.EIP-1.public_ip
}
# Use: It can print out a value from a resource, this can print out all of the details we are concerned with. Only one value per output, but can have multiple outputs.
#
# variable "subnet_prefix" {
#   description = "cidr block for the subnet"
#   default // if this isnt filled out the AWS will automatically fill one out for us
#   type = String // or pass any arguement if not sure
# }
# Use: this lets us create a variable that can be referenced. Ex: var.subnet_prefix.id