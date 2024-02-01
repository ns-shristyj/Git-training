// Create a Security Group
resource "aws_security_group" "allow_web" {
  name        = "allow_web_traffic"
  description = "Allow TLS inbound traffic and all outbound traffic"
  vpc_id      = aws_vpc.AWS-VPC.id
  tags = { Name = "allow_WEB" }
}

// IPs Granted Access
variable "allowed_ips"{
    type = list
    default = ["104.53.62.2/32", "24.206.70.11/32",
                "35.233.199.197/32", "35.230.57.233/32",
                "34.105.33.53/32", "34.83.158.21/32",
                "35.233.206.241/32", "35.247.6.21/32",
                "35.247.67.124/32", "35.197.82.112/32"]
}

// IPv4 - Security Group
resource "aws_vpc_security_group_ingress_rule" "allow_web_ipv4-1" {
  description       = "HTTPS"
  security_group_id = aws_security_group.allow_web.id
  cidr_ipv4         = allowed_ips
  from_port         = 443
  ip_protocol       = "tcp"
  to_port           = 443 
}
resource "aws_vpc_security_group_ingress_rule" "allow_web_ipv4-2" {
  description       = "ALT HTTPS"
  security_group_id = aws_security_group.allow_web.id
  cidr_ipv4         = "104.53.62.2/32"                  // this is responsible for which IP addresses can come into the Network
  from_port         = 8443
  ip_protocol       = "tcp"
  to_port           = 8443 
}
resource "aws_vpc_security_group_ingress_rule" "allow_web_ipv4-3" {
  description       = "ALT HTTPS"
  security_group_id = aws_security_group.allow_web.id
  cidr_ipv4         = "104.53.62.2/32"                  // this is responsible for which IP addresses can come into the Network
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