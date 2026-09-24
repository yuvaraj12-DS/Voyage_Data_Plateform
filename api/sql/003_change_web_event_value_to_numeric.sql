-- Preserve existing numeric event values while aligning PostgreSQL with the ORM model.
ALTER TABLE web_events
    ALTER COLUMN event_value TYPE NUMERIC(10, 2)
    USING NULLIF(BTRIM(event_value), '')::NUMERIC(10, 2);

ALTER TABLE web_events
    ADD CONSTRAINT web_events_event_value_check
    CHECK (event_value IS NULL OR event_value >= 0);
