variable "linkedin_client_id" {
  type      = string
  sensitive = true
  default   = "78n0h1d7apeeua"  # for testing; remove default in production
}

variable "linkedin_client_secret" {
  type      = string
  sensitive = true
}

variable "redirect_uri" {
  type = string
}