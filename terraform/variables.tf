variable "instance_type" {
  description = "Small x86 demo server. Choose t3.small where t3a is unavailable, or medium for more memory."
  type        = string
  default     = "t3a.small"
  validation {
    condition     = contains(["t3a.small", "t3.small", "t3a.medium", "t3.medium"], var.instance_type)
    error_message = "Choose t3a.small, t3.small, t3a.medium or t3.medium. ARM images are not supported."
  }
}
