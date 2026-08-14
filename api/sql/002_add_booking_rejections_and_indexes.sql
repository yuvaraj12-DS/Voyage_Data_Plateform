CREATE TABLE IF NOT EXISTS booking_rejections (
    rejection_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_file VARCHAR(255) NOT NULL,
    source_row_number INTEGER NOT NULL,
    booking_id VARCHAR(50) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    raw_adr NUMERIC(12, 2),
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_booking_rejections_source_row
    ON booking_rejections(source_row_number);


CREATE INDEX IF NOT EXISTS idx_bookings_updated_at
    ON bookings(updated_at, booking_id);


CREATE INDEX IF NOT EXISTS idx_bookings_tenant_updated_at
    ON bookings(tenant_id, updated_at, booking_id);


CREATE INDEX IF NOT EXISTS idx_bookings_property_id
    ON bookings(property_id);


CREATE INDEX IF NOT EXISTS idx_bookings_customer_id
    ON bookings(customer_id);


CREATE INDEX IF NOT EXISTS idx_properties_tenant_id
    ON properties(tenant_id);


CREATE INDEX IF NOT EXISTS idx_customers_tenant_id
    ON customers(tenant_id);