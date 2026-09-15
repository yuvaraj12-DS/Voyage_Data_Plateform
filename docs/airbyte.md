Voyage Booking API
        |
        +-- bookings
        |     Incremental / updated_at
        |
        +-- customers
        |     Incremental / updated_at
        |
        +-- properties
        |     Full Refresh
        |
        +-- tenants
              Full Refresh
        |
        v
Airbyte
        |
        v
AWS S3 Raw
JSONL + GZIP

Bookings:
119,389 initial records
Incremental tests passed

Customers:
100 initial records
Incremental tests passed

Properties:
2 records

Tenants:
2 records