// For more about Terraform using EC2: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
// This Terraform is responsible for starting a AWS Ec2 Instance
// Responsible for handling Credentials, S3 Backend, VPC, Internet Gateway, Custom Route Table
// Subnet, Associating that Subnet with a Route Table, a Network Interface with a IP in the subnet,
// Creating Security Groups [Mainly dealing with IPv4, Incoming and Outgoing Connections],
// Assigning a Elastic IP with a Network Interface and creating a Instance. 

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
  tags              = { name = "FLASK-AWS-VPC" }
}
// Create a Internet Gateway
resource "aws_internet_gateway" "gw" {
  vpc_id = "${aws_vpc.AWS-VPC.id}"
  tags = { name = "FLASK-GATEWAY"}
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
  tags              = { name = "FLASK-SUBNET-1" }
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
  description = "Allow web inbound traffic and all outbound traffic"
  vpc_id      = aws_vpc.AWS-VPC.id
  tags = { Name = "allow_WEB" }

  // IPv4 - Ingress Security Group dealing with Port 443
  // The IP's are allowing GitHub Runner's and, Netskope Client
  ingress {
    from_port = "443"
    to_port = "443"
    protocol = "TCP"
    cidr_blocks = ["104.53.62.2/32", "24.206.70.11/32", "35.233.199.197/32", "35.230.57.233/32", "34.105.33.53/32", "34.83.158.21/32", "35.233.206.241/32", "35.247.6.21/32", "35.247.67.124/32",
                "35.197.82.112/32", "24.206.84.11/32", "24.206.100.10/31", "24.206.101.10/31", "24.206.102.10/31", "24.206.112.10/31", "24.206.65.10/31", "24.206.67.10/31", "24.206.68.10/31",
                "24.206.72.10/31", "24.206.75.10/31", "24.206.78.10/31", "24.206.79.10/31", "24.206.80.10/31", "24.206.98.10/31", "24.239.128.10/31", "24.239.129.10/31", "24.239.131.10/31",
                "24.239.134.10/31", "24.239.135.10/31", "24.239.137.10/31", "24.239.138.10/31", "24.239.140.10/31", "24.239.144.10/31", "24.239.164.10/31", "24.206.106.10/31", "24.206.111.10/31",
                "24.206.119.10/31", "24.239.167.10/31", "24.206.69.10/31", "24.206.71.10/31", "24.206.74.10/31", "24.206.76.10/31", "24.206.84.10/31", "24.239.130.10/31", "24.239.141.10/31",
                "24.206.107.10/31", "24.206.108.10/31", "24.206.109.10/31", "24.206.110.10/31", "24.206.114.10/31", "24.206.118.10/31", "24.206.120.10/31", "24.206.103.10/31", "24.206.104.10/31",
                "24.206.105.10/31", "24.206.115.10/31", "24.206.66.10/31", "24.206.73.10/31", "24.206.77.10/31", "24.206.82.10/31", "24.206.99.0/31", "24.206.97.10/31", "24.206.70.10/31",
                "24.239.132.10/31", "24.239.145.10/31", "24.239.160.10/31", "24.239.161.10/31", "24.239.163.10/32", "24.239.165.10/31", "24.239.166.10/31", "24.239.133.10/31", "24.239.136.10/31", 
                "24.239.139.10/31", "24.239.162.10/31"]
  # Removed:
  # 24.206.110.11/32, "24.206.100.11/32", "24.206.101.11/32", "24.206.102.11/32", "24.206.112.11/32", "24.206.65.11/32", "24.206.67.11/32", "24.206.68.11/32", "24.206.70.11/32",
  # "24.206.72.11/32", "24.206.75.11/32", "24.206.78.11/32", "24.206.79.11/32", "24.206.80.11/32", "24.206.98.11/32", "24.239.128.11/32", "24.239.129.11/32", "24.239.131.11/32", "24.239.134.11/32",
  # "24.239.135.11/32", "24.239.137.11/32", "24.239.138.11/32", "24.239.140.11/32", "24.239.144.11/32", "24.239.164.11/32", "24.206.106.11/32",  "24.206.111.11/32", "24.206.119.11/32", "24.239.167.11/32",
  # "24.206.69.11/32", "24.206.71.11/32", "24.206.74.11/32", "24.206.76.11/32", "24.239.130.11/32", "24.239.141.11/32", "24.206.107.11/32", "24.206.108.11/32", "24.206.109.11/32", "24.206.114.11/32",
  # "24.206.120.11/32", "24.206.118.11/32", "24.206.103.11/32", "24.206.104.11/32", "24.206.105.11/32", "24.206.115.11/32", "24.206.66.11/32", "24.206.73.11/32", "24.206.77.11/32", "24.206.82.11/32",
  # "24.206.99.10/32", "24.206.97.11/32", "24.239.160.11/32", "24.239.161.11/32", "24.239.165.11/32", "24.239.166.11/32", "24.239.133.11/32", "24.239.136.11/32",

  }
  // IPv4 - Ingress Security Group dealing with Port 8443
  // The IP's are allowing GitHub Runner's and, Netskope Client
  # ingress {
  #   from_port = "8443"
  #   to_port = "8443"
  #   protocol = "TCP"
  #   cidr_blocks = ["104.53.62.2/32", "24.206.70.11/32",
  #               "35.233.199.197/32", "35.230.57.233/32",
  #               "34.105.33.53/32", "34.83.158.21/32",
  #               "35.233.206.241/32", "35.247.6.21/32",
  #               "35.247.67.124/32", "35.197.82.112/32",
  #               "24.206.84.11/32", "163.116.133.35/32", "71.14.75.168/32"]
  # }
  // IPv4 - Ingress Security Group dealing with Port 22
  // The IP's are allowing GitHub Runner's and, Netskope Client  
  // This is important for allowing SSH between the Client and Server
  ingress {
    from_port = "22"
    to_port = "22"
    protocol = "TCP"
    cidr_blocks = ["0.0.0.0/0"]
  }
  // IPv4 - Ingress Security Group dealing with Port 80
  // The IP's are allowing GitHub Runner's and, Netskope Client  
  // This is important for allowing SSH between the Client and Server
  # ingress {
  #   from_port = "80"
  #   to_port = "80"
  #   protocol = "TCP"
  #   cidr_blocks = ["104.53.62.2/32", "24.206.70.11/32",
  #               "35.233.199.197/32", "35.230.57.233/32",
  #               "34.105.33.53/32", "34.83.158.21/32",
  #               "35.233.206.241/32", "35.247.6.21/32",
  #               "35.247.67.124/32", "35.197.82.112/32",
  #               "24.206.84.11/32", "163.116.133.35/32", "71.14.75.168/32"]
  # }

  // IPv4 - Egress Security Group
  // This allows all IP's to leave.
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

// Assigning a Elastic IP to the Network Interface
resource "aws_eip" "EIP-1" {
  network_interface         = "${aws_network_interface.net_face.id}"
  associate_with_private_ip = "10.0.1.50"
}

// Create Ubuntu Server
resource "aws_instance" "flask" {
  ami               = "ami-0ce2cb35386fc22e9"
  instance_type     = "t2.medium"
  availability_zone = "us-west-1b"
  key_name          = "seceng-intern-key-pair"

  network_interface {
    device_index          = 0
    network_interface_id  = aws_network_interface.net_face.id
  }
}

# Useful for outputting the server's public IP
# Running a command similar to this will allow for different value's
# to be stored in GitHub Actions
output "server_public_ip" {
  value = aws_eip.EIP-1.public_ip
}