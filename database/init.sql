-- Database initialization script
-- This script runs automatically when the PostgreSQL container starts for the first time

-- Create the base_readings table for tracking starting points
CREATE TABLE IF NOT EXISTS base_readings (
    id SERIAL PRIMARY KEY,
    meter1_base INTEGER NOT NULL,
    meter2_base INTEGER NOT NULL,
    meter3_base INTEGER NOT NULL,
    base_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the meter_readings table with consumption tracking
CREATE TABLE IF NOT EXISTS meter_readings (
    id SERIAL PRIMARY KEY,
    reading_date DATE NOT NULL,
    meter1_current INTEGER NOT NULL,
    meter2_current INTEGER NOT NULL,
    meter3_current INTEGER NOT NULL,
    meter1_consumption INTEGER DEFAULT 0,
    meter2_consumption INTEGER DEFAULT 0,
    meter3_consumption INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_base_readings_date ON base_readings(base_date);
CREATE INDEX IF NOT EXISTS idx_meter_readings_date ON meter_readings(reading_date);
CREATE INDEX IF NOT EXISTS idx_meter_readings_timestamp ON meter_readings(timestamp);

-- Sample data for development/testing (commented out by default)
-- Uncomment the following lines to add sample data for development:

-- INSERT INTO base_readings (meter1_base, meter2_base, meter3_base, base_date) VALUES
--     (1000, 2000, 1500, '2024-01-01')
-- ON CONFLICT DO NOTHING;

-- INSERT INTO meter_readings (reading_date, meter1_current, meter2_current, meter3_current, meter1_consumption, meter2_consumption, meter3_consumption) VALUES
--     ('2024-01-01', 1000, 2000, 1500, 0, 0, 0),
--     ('2024-01-02', 1005, 2007, 1503, 5, 7, 3),
--     ('2024-01-03', 1012, 2015, 1508, 12, 15, 8),
--     ('2024-01-04', 1018, 2022, 1512, 18, 22, 12)
-- ON CONFLICT DO NOTHING;