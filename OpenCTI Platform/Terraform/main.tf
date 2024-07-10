// First, authenticate with GCP. The easiest way to do this is to run gcloud auth application-default login
provider "google" {
  project = "ns-ciso-asa-automation"
  region  = "us-west1"
  zone    = "us-west1-b"
  credentials = file("~/.config/gcloud/application_default_credentials.json")
}

// Bucket to store Website
# resource "google_storage_bucket" "opencti-storage" {
#   name = "opencti-storage"
#   location = "us-west1"
# }

resource "google_compute_network" "opencti-network" {
  name = "opencti-network"
}

# resource "google_compute_subnetwork" "opencti-subnet" {
#   name = "opencti-subnet"
#   network = google_compute_network.opencti-network.id
#   ip_cidr_range = "10.0.0.0/24"
#   region = "us-west1"
# }

# resource "google_compute_firewall" "opencti-firewall" {
#   name = "opencti-firewall"
#   network = google_compute_network.opencti-network.name

#   allow {
#     protocol = "tcp"
#     ports = ["80", "443", "22"]
#   }

#   source_ranges = ["0.0.0.0/0"]
# }

resource "google_compute_instance_template" "opencti-template" {
  name          = "opencti-template"
  machine_type  = "n1-standard-1"

  disk {
    source_image = "debian-cloud/debian-11"
    auto_delete = true
    boot = true
  }

  network_interface {
    network =  google_compute_network.opencti-network.id
    subnetwork = google_compute_subnetwork.opencti-subnet.id
  }

  tags = ["opencti"]
}

resource "google_compute_instance_group_manager" "opencti-instance-group" {
  name = "opencti-instance-group"
  base_instance_name = "opencti-instance"
  zone = "us-west1-b"
  target_size = 1

  version {
    instance_template = google_compute_instance_template.opencti-template.self_link
  }

}

resource "google_compute_backend_service" "opencti_backend" {
  name = "opencti-backend"
  port_name = "http"
  protocol = "HTTP"
  timeout_sec = 10

  backend {
    group = google_compute_instance_group_manager.opencti-instance-group.instance_group
  }
}

resource "google_compute_url_map" "opencti_url_map" {
    name = "opencti-url-map"
    default_service = google_compute_backend_service.opencti_backend.self_link
}

resource "google_compute_target_http_proxy" "opencti_http_proxy" {
  name = "opencti-http-proxy"
  url_map = google_compute_url_map.opencti_url_map.self_link
}

resource "google_compute_global_forwarding_rule" "opencti_forwarding_rule" {
  name = "opencti-forwarding-rule"
  port_range = "80"
  target = google_compute_target_http_proxy.opencti_http_proxy.self_link
}

# resource "google_compute_health_check" "default" {
#   name = "opencti-health-check"
#   check_interval_sec = 5
#   timeout_sec = 5

#   http_health_check {
#     port = "80"
#   }
# }

output "instance_ip" {
  value = google_compute_global_forwarding_rule.opencti_forwarding_rule
}