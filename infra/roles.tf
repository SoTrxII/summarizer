resource "azurerm_role_assignment" "azure_ai_user" {
  scope                = azapi_resource.ai_services.id
  role_definition_name = "Azure AI User"
  principal_id         = data.azurerm_client_config.current.object_id
}