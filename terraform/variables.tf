variable "subscription_id" {
  description = "Azure Subscription ID to deploy into"
  type        = string
  default     = ""
}

variable "tenant_id" {
  description = "Azure Tenant ID (AAD directory)"
  type        = string
  default     = ""
}

variable "app_code" {
  description = "Short code for the app (e.g., aru)"
  type        = string
}

variable "env" {
  description = "Environment (e.g., dev, stg, prd)"
  type        = string
}

variable "location" {
  description = "Azure location (e.g., eastus2)"
  type        = string
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

variable "resource_group_name" {
  description = "Optional explicit RG name; if empty, it will be derived"
  type        = string
  default     = ""
}

variable "storage_account_name" {
  description = "Optional explicit Storage Account name; if empty, it will be derived"
  type        = string
  default     = ""
}

variable "storage_replication_type" {
  description = "Replication type for the Storage Account (LRS, ZRS, GRS, RAGRS)"
  type        = string
  default     = "LRS"
}

variable "containers" {
  description = "List of blob containers to create"
  type        = list(string)
  default     = ["resumes", "logs"]
}

variable "tables" {
  description = "List of tables to create (alphanumeric only, must start with a letter)"
  type        = list(string)
  default     = ["Resumes"]
}

variable "enable_blob_versioning" {
  description = "Enable blob versioning"
  type        = bool
  default     = true
}

variable "blob_soft_delete_days" {
  description = "Retention days for blob soft delete"
  type        = number
  default     = 14
}