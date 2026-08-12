# Multi-Tenancy Design

The platform is designed to support multiple travel business
customers.

Each tenant receives a unique tenant_id.

Example tenants:

TENANT001 - Mallorca Charters
TENANT002 - Ibiza Tours
TENANT003 - Barcelona Hotels

Business tables will contain tenant_id where appropriate.

The tenant identifier will allow data to be logically isolated
and will support future workspace-level access controls.