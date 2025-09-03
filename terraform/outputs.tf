output "resource_group_name" {
  value       = azurerm_resource_group.this.name
  description = "Resource Group name"
}

output "storage_account_name" {
  value       = azurerm_storage_account.this.name
  description = "Storage Account name"
}

output "storage_account_id" {
  value       = azurerm_storage_account.this.id
  description = "Storage Account resource ID"
}

output "primary_connection_string" {
  value       = azurerm_storage_account.this.primary_connection_string
  sensitive   = true
  description = "Connection string for the storage account (for setup/testing; prefer Managed Identity for apps)"
}