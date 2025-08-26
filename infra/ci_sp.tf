// Service principal for CI to call Azure AI Foundry APIs

// App registration
resource "azuread_application" "ci" {
  display_name = format("gh-ci-%s", local.resource_suffix_kebabcase)
  owners       = [data.azurerm_client_config.current.object_id]
  tags         = ["github-actions", var.environment]
}

// Enterprise application (service principal)
resource "azuread_service_principal" "ci" {
  client_id = azuread_application.ci.client_id
  owners    = [data.azurerm_client_config.current.object_id]
  tags      = ["github-actions", var.environment]
}

// Client secret used by GitHub Actions
resource "azuread_application_password" "ci" {
  application_id = azuread_application.ci.id
  display_name   = "github-actions-ci"
  rotate_when_changed = {
    rotation = timestamp()
  }
  end_date = timeadd(timestamp(), "17520h") // ~2 years
}

// Grant minimal role to call Foundry (Azure AI User on the AI Services account)
resource "azurerm_role_assignment" "ci_ai_user" {
  scope                = azapi_resource.ai_services.id
  role_definition_name = "Azure AI User"
  principal_id         = azuread_service_principal.ci.object_id
}

// Output creds JSON for azure/login@v2
output "ci_azure_credentials" {
  description = "JSON for AZURE_CREDENTIALS GitHub secret"
  sensitive   = true
  value = jsonencode({
    clientId       = azuread_application.ci.client_id,
    clientSecret   = azuread_application_password.ci.value,
    subscriptionId = data.azurerm_client_config.current.subscription_id,
    tenantId       = data.azurerm_client_config.current.tenant_id
  })
}
