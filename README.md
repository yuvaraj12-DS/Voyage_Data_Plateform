# VoyageData — Travel Marketing Data Platform

## Project Overview

VoyageData is a production-style travel marketing data platform
designed to unify marketing, booking, and website analytics data.

The platform will ingest data from multiple source systems,
store raw data in AWS S3, process data using Databricks,
transform analytical models using dbt, and orchestrate the
end-to-end workflow using Airflow.

## Business Problem

Travel companies often have marketing, booking, and website
data distributed across different systems.

The objective of this project is to build a reliable platform
that allows the business to analyze marketing spend, bookings,
revenue, conversion rates, and ROAS in a unified analytical layer.

## Status

Phase 1 — Project Foundation

## Current Status

Phase 2 — Source System

Completed:

- PostgreSQL source database
- Operational booking schema
- Synthetic tenants and properties
- Booking data loader
- Source-data validation
- Rejected-record handling
- FastAPI REST API
- API-key authentication
- Pagination
- Tenant filtering
- Incremental timestamp filtering
- API tests