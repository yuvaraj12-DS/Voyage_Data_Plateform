CREATE TABLE tenants (
    tenant_id VARCHAR(50) PRIMARY KEY,
    tenant_name VARCHAR(200) NOT NULL,
    country VARCHAR(3) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT tenants_country_check
        CHECK (char_length(country) BETWEEN 2 AND 3),

    CONSTRAINT tenants_currency_check
        CHECK (char_length(currency) = 3)
);


CREATE TABLE properties (
    property_id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    property_name VARCHAR(200) NOT NULL,
    property_type VARCHAR(50) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT properties_tenant_fk
        FOREIGN KEY (tenant_id)
        REFERENCES tenants(tenant_id)
);


CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    country VARCHAR(3),
    customer_type VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT customers_tenant_fk
        FOREIGN KEY (tenant_id)
        REFERENCES tenants(tenant_id),

    CONSTRAINT customers_country_check
        CHECK (country IS NULL OR char_length(country) BETWEEN 2 AND 3)
);


CREATE TABLE bookings (
    booking_id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    property_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    booking_date DATE NOT NULL,
    arrival_date DATE NOT NULL,
    departure_date DATE NOT NULL,
    adults INTEGER NOT NULL,
    children INTEGER NOT NULL DEFAULT 0,
    room_nights INTEGER NOT NULL,
    adr NUMERIC(12, 2) NOT NULL,
    market_segment VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT bookings_tenant_fk
        FOREIGN KEY (tenant_id)
        REFERENCES tenants(tenant_id),

    CONSTRAINT bookings_property_fk
        FOREIGN KEY (property_id)
        REFERENCES properties(property_id),

    CONSTRAINT bookings_customer_fk
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    CONSTRAINT bookings_adults_check
        CHECK (adults >= 0),

    CONSTRAINT bookings_children_check
        CHECK (children >= 0),

    CONSTRAINT bookings_room_nights_check
        CHECK (room_nights >= 0),

    CONSTRAINT bookings_adr_check
        CHECK (adr >= 0),

    CONSTRAINT bookings_dates_check
        CHECK (departure_date >= arrival_date),

    CONSTRAINT bookings_status_check
        CHECK (
            status IN (
                'CONFIRMED',
                'CANCELLED',
                'COMPLETED'
            )
        )
);