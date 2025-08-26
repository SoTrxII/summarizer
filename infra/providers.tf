terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=4.36.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "3.6.3"
    }

    azapi = {
      source  = "Azure/azapi"
      version = "2.4.0"
    }

    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.50"
    }
  }

  # backend "local" {}
  # backend "azurerm" {}
}

provider "azurerm" {
  features {}
}

provider "azapi" {
  # Configuration options
}

provider "azuread" {
  # Uses the same authentication as azurerm by default
}
