resource "azapi_resource" "project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name      = format("proj-%s", local.resource_suffix_kebabcase)
  location  = azurerm_resource_group.this.location
  parent_id = azapi_resource.ai_services.id
  tags      = local.tags_azapi

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {
      description = "AI Shop Project"
      displayName = "AI Shop"
    }
  }
}
