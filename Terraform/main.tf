// For more about Terraform using EC2: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">=0.14.9"

  backend "s3" {
    bucket    = "seceng-terraform-state-storage"
    key       = "terraform.tfstate"
    region    = "us-west-1"
  }
}

// Configure the AWS Provider with Credentials
provider "aws" {
    region = "us-west-1"
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
  availability_zone = "us-west-1b"
  tags              = { name = "NS-CQUINLAN-SUBNET-1" }
}

// Associating the Subnet with the Route Table
resource "aws_route_table_association" "a" {
  subnet_id       = "${aws_subnet.AWS-SUBNET-1.id}"
  route_table_id  = "${aws_route_table.ns-cquinlan-route_table.id}"
}

// Create a Network Interface with an IP in the subnet
resource "aws_network_interface" "net_face" {
  subnet_id       = aws_subnet.AWS-SUBNET-1.id
  private_ips     = ["10.0.1.50"]
  security_groups = [aws_security_group.allow_web.id]
}
// Create a Security Group
resource "aws_security_group" "allow_web" {
  name        = "allow_web_traffic"
  description = "Allow TLS inbound traffic and all outbound traffic"
  vpc_id      = aws_vpc.AWS-VPC.id
  tags = { Name = "allow_WEB" }
}

// IPs Granted Access
variable "allowed_ips"{
    type = list(string)
    default = ["104.53.62.2/32", "35.197.82.112/32",
                "35.233.199.197/32", "35.230.57.233/32",
                "34.105.33.53/32", "34.83.158.21/32",
                "35.233.206.241/32", "35.247.6.21/32",
                "35.247.67.124/32"]
}

// IPv4 - Security Group
resource "aws_vpc_security_group_ingress_rule" "allow_web_ipv4-1" {
  description       = "HTTPS"
  security_group_id = aws_security_group.allow_web.id
  count             = length(var.allowed_ips)
  cidr_ipv4         = var.allowed_ips[count.index]
  from_port         = 443
  ip_protocol       = "tcp"
  to_port           = 443 
}
resource "aws_vpc_security_group_ingress_rule" "allow_web_ipv4-2" {
  description       = "ALT HTTPS"
  security_group_id = aws_security_group.allow_web.id
  count             = length(var.allowed_ips)
  cidr_ipv4         = var.allowed_ips[count.index]
  from_port         = 8443
  ip_protocol       = "tcp"
  to_port           = 8443 
}
resource "aws_vpc_security_group_ingress_rule" "allow_web_ipv4-3" {
  description       = "ALT HTTPS"
  security_group_id = aws_security_group.allow_web.id
  count             = length(var.allowed_ips)
  cidr_ipv4         = var.allowed_ips[count.index]
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22 
}

// Egress - Security Group
resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.allow_web.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # semantically equivalent to all ports
}

// Assigning a Elastic IP to the Network Interface
resource "aws_eip" "EIP-1" {
  network_interface         = "${aws_network_interface.net_face.id}"
  associate_with_private_ip = "10.0.1.50"
}

// Create Ubuntu Server and install Cobalt Strike
resource "aws_instance" "cobalt" {
  ami               = "ami-0ce2cb35386fc22e9"
  instance_type     = "t2.medium"
  availability_zone = "us-west-1b"
  key_name          = "seceng-intern-key-pair"

  network_interface {
    device_index          = 0
    network_interface_id  = aws_network_interface.net_face.id
  }
}

# Useful Commands-
output "server_public_ip" {
  value = aws_eip.EIP-1.public_ip
}