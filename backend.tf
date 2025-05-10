terraform {
  backend "remote" {
    organization = "your-terraform-cloud-org-name"
    workspaces {
      name = "aws-frontend-management"
    }
  }
}
