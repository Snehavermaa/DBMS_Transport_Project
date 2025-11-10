-- =====================================================
-- PUBLIC TRANSPORT DATABASE MANAGEMENT SYSTEM (PTDMS)
-- COMPLETE SQL SCRIPT (DDL, DML, TRIGGER, PROCEDURE, SAMPLE QUERIES)
-- =====================================================

CREATE DATABASE IF NOT EXISTS transport_db;
USE transport_db;

-- =====================================================
-- 1. TABLE DEFINITIONS (DDL)
-- =====================================================

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(256),
    role ENUM('admin','operator') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drivers (
    driver_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    license_no VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    salary DECIMAL(10,2),
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS routes (
    route_id INT AUTO_INCREMENT PRIMARY KEY,
    route_name VARCHAR(200),
    source VARCHAR(200),
    destination VARCHAR(200),
    distance_km FLOAT
);

CREATE TABLE IF NOT EXISTS stops (
    stop_id INT AUTO_INCREMENT PRIMARY KEY,
    stop_name VARCHAR(200),
    location VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS buses (
    bus_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_no VARCHAR(100) UNIQUE,
    bus_name VARCHAR(200),
    type VARCHAR(100),
    capacity INT,
    fare_id INT,
    route_id INT,
    ac BOOLEAN DEFAULT FALSE,
    status ENUM('active','maintenance','inactive') DEFAULT 'active',
    FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS route_stops (
    route_id INT,
    stop_order INT,
    stop_id INT,
    PRIMARY KEY (route_id, stop_order),
    FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE,
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id INT AUTO_INCREMENT PRIMARY KEY,
    route_id INT,
    bus_id INT,
    driver_id INT,
    start_time DATETIME,
    end_time DATETIME,
    frequency VARCHAR(100),
    status ENUM('scheduled','ongoing','completed','cancelled') DEFAULT 'scheduled',
    FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE SET NULL,
    FOREIGN KEY (bus_id) REFERENCES buses(bus_id) ON DELETE SET NULL,
    FOREIGN KEY (driver_id) REFERENCES drivers(driver_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS passengers (
    passenger_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200),
    address VARCHAR(300),
    contact_no VARCHAR(20),
    email_id VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id INT,
    passenger_id INT,
    boarding_stop_id INT,
    dropping_stop_id INT,
    seat_no VARCHAR(10),
    fare DECIMAL(10,2),
    gender ENUM('male','female','other') DEFAULT 'other',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE SET NULL,
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE SET NULL,
    FOREIGN KEY (boarding_stop_id) REFERENCES stops(stop_id) ON DELETE SET NULL,
    FOREIGN KEY (dropping_stop_id) REFERENCES stops(stop_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ticket_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT,
    trip_id INT,
    log_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(50),
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
);

-- =====================================================
-- 2. TRIGGER
-- =====================================================
DELIMITER //
CREATE TRIGGER after_ticket_insert
AFTER INSERT ON tickets
FOR EACH ROW
BEGIN
    INSERT INTO ticket_log (ticket_id, trip_id, action)
    VALUES (NEW.ticket_id, NEW.trip_id, 'Ticket Issued');
END //
DELIMITER ;

-- =====================================================
-- 3. STORED PROCEDURE
-- =====================================================
DELIMITER //
CREATE PROCEDURE GetTripRevenue(IN tripID INT)
BEGIN
    SELECT t.trip_id, COALESCE(r.route_name,'-') AS route_name, 
           COALESCE(SUM(tk.fare), 0) AS total_revenue
    FROM trips t
    LEFT JOIN routes r ON t.route_id = r.route_id
    LEFT JOIN tickets tk ON t.trip_id = tk.trip_id
    WHERE t.trip_id = tripID
    GROUP BY t.trip_id, r.route_name;
END //
DELIMITER ;

-- =====================================================
-- 4. SAMPLE DATA (INSERT STATEMENTS)
-- =====================================================
INSERT INTO users (username, password_hash, role) VALUES
('admin', SHA2('admin123', 256), 'admin'),
('operator1', SHA2('oper123', 256), 'operator');

INSERT INTO routes (route_name, source, destination, distance_km) VALUES
('R1 Central-Airport', 'Central Station', 'Airport', 15.0),
('R2 Central-University', 'Central Station', 'University', 8.5);

INSERT INTO stops (stop_name, location) VALUES
('Central Station', 'City Center'),
('Airport', 'Airport Road'),
('University', 'Campus Area');

INSERT INTO drivers (first_name, last_name, license_no, phone, salary, address, is_active) VALUES
('Raj', 'Kumar', 'LIC1001', '9999990001', 30000, 'Central City', TRUE),
('Anita', 'Sharma', 'LIC1002', '9999990002', 32000, 'North Block', TRUE);

INSERT INTO buses (bus_no, bus_name, type, capacity, fare_id, route_id, ac, status) VALUES
('BUS100', 'City Rapid', 'AC', 50, NULL, 1, TRUE, 'active'),
('BUS101', 'Metro Shuttle', 'Mini', 30, NULL, 2, FALSE, 'active');

INSERT INTO trips (route_id, bus_id, driver_id, start_time, end_time, frequency, status) VALUES
(1, 1, 1, NOW(), NOW() + INTERVAL 1 HOUR, 'daily', 'scheduled'),
(2, 2, 2, NOW() + INTERVAL 2 HOUR, NOW() + INTERVAL 3 HOUR, 'daily', 'scheduled');

INSERT INTO passengers (name, address, contact_no, email_id) VALUES
('Sneha Verma', 'College Road', '8888888888', 'sneha@example.com'),
('Aman Singh', 'North Lane', '7777777777', 'aman@example.com');

INSERT INTO tickets (trip_id, passenger_id, boarding_stop_id, dropping_stop_id, seat_no, fare, gender) VALUES
(1, 1, 1, 2, 'A1', 45.00, 'female'),
(2, 2, 3, 2, 'A2', 35.00, 'male');

-- =====================================================
-- 5. NESTED QUERY
-- =====================================================
SELECT name, contact_no 
FROM passengers 
WHERE passenger_id IN (
    SELECT passenger_id FROM tickets WHERE fare > 30
);

-- =====================================================
-- 6. JOIN QUERY
-- =====================================================
SELECT tk.ticket_id, p.name AS passenger_name, r.route_name, b.bus_no, tk.fare
FROM tickets tk
JOIN trips t ON tk.trip_id = t.trip_id
JOIN routes r ON t.route_id = r.route_id
JOIN buses b ON t.bus_id = b.bus_id
JOIN passengers p ON tk.passenger_id = p.passenger_id;

-- =====================================================
-- 7. AGGREGATE QUERY
-- =====================================================
SELECT r.route_name, COUNT(tk.ticket_id) AS total_tickets, SUM(tk.fare) AS total_revenue
FROM routes r
JOIN trips t ON r.route_id = t.route_id
LEFT JOIN tickets tk ON t.trip_id = tk.trip_id
GROUP BY r.route_name;
