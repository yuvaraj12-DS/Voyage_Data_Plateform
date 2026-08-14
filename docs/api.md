# Voyage Booking API

The Voyage Booking API provides read access to the simulated
booking source system.

## Base URL

http://localhost:8000

## Authentication

Protected endpoints require:

X-API-Key: <API key>

## Health

GET /health

Checks both API and database availability.

## Tenants

GET /api/v1/tenants

Returns all tenants.

## Properties

GET /api/v1/properties

Optional:

tenant_id

## Customers

GET /api/v1/customers

Supports:

page
page_size
tenant_id

## Bookings

GET /api/v1/bookings

Supports:

page
page_size
tenant_id
status
updated_after

## Single Booking

GET /api/v1/bookings/{booking_id}

## Pagination

Booking and customer responses include page, page_size,
total_records and total_pages.

## Incremental Extraction

The updated_after parameter allows consumers to request only
records changed after a specified timestamp.