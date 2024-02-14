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

// Create S3 Bucket
resource "aws_s3_bucket" "ns-bucket" {
  bucket = "seceng-terraform-state-storage"
}
resource "aws_s3_bucket_ownership_controls" "ownership" {
  bucket = aws_s3_bucket.ns-bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}
resource "aws_s3_bucket_public_access_block" "public-access" {
  bucket = aws_s3_bucket.ns-bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
resource "aws_s3_bucket_acl" "acl" {
  depends_on = [
    aws_s3_bucket_ownership_controls.ownership,
    aws_s3_bucket_public_access_block.public-access,
  ]
  bucket = aws_s3_bucket.ns-bucket.id
  acl    = "public-read"
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

// Assigning a Elastic IP to the Network Interface
resource "aws_eip" "EIP-1" {
  network_interface         = "${aws_network_interface.net_face.id}"
  associate_with_private_ip = "10.0.1.50"
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
    cidr_blocks = ["104.53.62.2/32", "24.206.70.11/32",
                "35.233.199.197/32", "35.230.57.233/32",
                "34.105.33.53/32", "34.83.158.21/32",
                "35.233.206.241/32", "35.247.6.21/32",
                "35.247.67.124/32", "35.197.82.112/32",
                "24.206.84.11/32"]
  }
  // IPv4 - Ingress Security Group dealing with Port 8443
  // The IP's are allowing GitHub Runner's and, Netskope Client
  ingress {
    from_port = "8443"
    to_port = "8443"
    protocol = "TCP"
    cidr_blocks = ["104.53.62.2/32", "24.206.70.11/32",
                "35.233.199.197/32", "35.230.57.233/32",
                "34.105.33.53/32", "34.83.158.21/32",
                "35.233.206.241/32", "35.247.6.21/32",
                "35.247.67.124/32", "35.197.82.112/32",
                "24.206.84.11/32"]
  }
  // IPv4 - Ingress Security Group dealing with Port 22
  // The IP's are allowing GitHub Runner's and, Netskope Client  
  // This is important for allowing SSH between the Client and Server
  ingress {
    from_port = "22"
    to_port = "22"
    protocol = "TCP"
    cidr_blocks = ["104.53.62.2/32", "24.206.70.11/32",
                "35.233.199.197/32", "35.230.57.233/32",
                "34.105.33.53/32", "34.83.158.21/32",
                "35.233.206.241/32", "35.247.6.21/32",
                "35.247.67.124/32", "35.197.82.112/32",
                "24.206.84.11/32"] # " 0.0.0.0/0"
  }
  // IPv4 - Ingress Security Group dealing with Port 50050
  // The IP's are allowing GitHub Runner's and, Netskope Client  
  // This is important for allowing Cobalt Strike Team Server to Accept Connections
  ingress {
    from_port = "50050"
    to_port = "50050"
    protocol = "TCP"
    cidr_blocks = ["104.53.62.2/32", "24.206.70.11/32",
                "35.233.199.197/32", "35.230.57.233/32",
                "34.105.33.53/32", "34.83.158.21/32",
                "35.233.206.241/32", "35.247.6.21/32",
                "35.247.67.124/32", "35.197.82.112/32",
                "24.206.84.11/32"] # " 0.0.0.0/0"
  }
  // IPv4 - Egress Security Group
  // This allows all IP's to leave.
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
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

// Enable VPC Endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id =  aws_vpc.AWS-VPC.id
  service_name = "com.amazonecs.us-west-1b.s3"
}

# Useful for outputting the server's public IP
# Running a command similar to this will allow for different value's
# to be stored in GitHub Actions
output "server_public_ip" {
  value = aws_eip.EIP-1.public_ip
}