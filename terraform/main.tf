locals {
  region_code = var.location
  rg_name     = var.resource_group_name != "" ? var.resource_group_name : "rg-${var.app_code}-${var.env}-${local.region_code}"

  sa_base = var.storage_account_name != "" ? var.storage_account_name : "st${var.app_code}${var.env}"
}

resource "random_string" "sa_suffix" {
  length  = 3
  lower   = true
  upper   = false
  numeric = true
  special = false
}

resource "azurerm_resource_group" "this" {
  name     = local.rg_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_storage_account" "this" {
  name                     = var.storage_account_name != "" ? var.storage_account_name : "${local.sa_base}${random_string.sa_suffix.result}"
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = var.storage_replication_type
  account_kind             = "StorageV2"

  blob_properties {
    versioning_enabled = var.enable_blob_versioning

    delete_retention_policy {
      days = var.blob_soft_delete_days
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "containers" {
  for_each              = toset(var.containers)
  name                  = each.value
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

resource "azurerm_storage_table" "tables" {
  for_each             = toset(var.tables)
  name                 = each.value
  storage_account_name = azurerm_storage_account.this.name
}
