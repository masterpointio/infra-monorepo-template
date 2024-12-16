variable "length" {
  description = "The length of the random name"
  type        = number
  default     = 2
  validation {
    condition     = var.length > 0
    error_message = "The length must be a positive number."
  }
}
