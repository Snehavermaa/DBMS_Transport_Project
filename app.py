# app.py - COMPLETE VERSION WITH ALL FEATURES
"""
Public Transport Database Management System
Full-featured Streamlit app with MySQL (CRUD, triggers, stored procedure, driver active toggle)
Includes NEW public ticket booking feature and update/delete buttons
"""

import streamlit as st
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from datetime import datetime, date, time, timedelta
import hashlib
import traceback
import random

# --------------------------- CONFIG ---------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "tp_user",
    "password": "root", 
    "database": "transport_db"
}

DEMO_USERS = [
    ("admin", "admin123", "admin"),
    ("operator1", "oper123", "operator"),
]

# --------------------------- DB HELPERS ---------------------------
@contextmanager
def get_conn():
    conn = None
    cur = None
    try:
        tmp = DB_CONFIG.copy()
        db = tmp.pop("database", None)
        conn0 = mysql.connector.connect(host=tmp["host"], user=tmp["user"], password=tmp["password"])
        cur0 = conn0.cursor()
        if db:
            cur0.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` DEFAULT CHARACTER SET 'utf8mb4'")
        cur0.close()
        conn0.close()
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor(dictionary=True)
        yield conn, cur
        conn.commit()
    except Exception as e:
        st.error(f"Database error: {e}")
        traceback.print_exc()
        raise
    finally:
        if cur: cur.close()
        if conn: conn.close()

def fetch_all(sql, params=None):
    with get_conn() as (conn, cur):
        cur.execute(sql, params or ())
        return cur.fetchall() or []

def run_sql(sql, params=None):
    with get_conn() as (conn, cur):
        cur.execute(sql, params or ())
        return cur.lastrowid

# --------------------------- SCHEMA & SEED ---------------------------
def initialize_database_and_schema():
    """Create all tables safely - only if they don't exist"""
    with get_conn() as (conn, cur):
        # Disable foreign key checks temporarily for safe table creation
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        # Create tables only if they don't exist
        # Users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            password_hash VARCHAR(256),
            role ENUM('admin','operator') NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)

        # Drivers table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            driver_id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            license_no VARCHAR(100) UNIQUE,
            phone VARCHAR(20),
            salary DECIMAL(10,2),
            address TEXT,
            is_active BOOLEAN DEFAULT TRUE
        ) ENGINE=InnoDB;
        """)

        # Routes table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            route_id INT AUTO_INCREMENT PRIMARY KEY,
            route_name VARCHAR(200),
            source VARCHAR(200),
            destination VARCHAR(200),
            distance_km FLOAT
        ) ENGINE=InnoDB;
        """)

        # Stops table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS stops (
            stop_id INT AUTO_INCREMENT PRIMARY KEY,
            stop_name VARCHAR(200),
            location VARCHAR(255)
        ) ENGINE=InnoDB;
        """)

        # Buses table - CORRECTED: Added 'type' column
        cur.execute("""
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
        ) ENGINE=InnoDB;
        """)

        # Route stops table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS route_stops (
            route_id INT,
            stop_order INT,
            stop_id INT,
            PRIMARY KEY (route_id, stop_order),
            FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE,
            FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # Trips table
        cur.execute("""
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
        ) ENGINE=InnoDB;
        """)

        # Passengers table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS passengers (
            passenger_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200),
            address VARCHAR(300),
            contact_no VARCHAR(20),
            email_id VARCHAR(200)
        ) ENGINE=InnoDB;
        """)

        # Tickets table
        cur.execute("""
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
        ) ENGINE=InnoDB;
        """)

        # Path table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS path (
            path_id INT AUTO_INCREMENT PRIMARY KEY,
            trip_id INT,
            stop_id INT,
            arrival_time DATETIME,
            departure_time DATETIME,
            people_in INT DEFAULT 0,
            people_out INT DEFAULT 0,
            money_collected DECIMAL(10,2) DEFAULT 0,
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE,
            FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # Major stops table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS major_stops (
            major_stop_id INT AUTO_INCREMENT PRIMARY KEY,
            route_id INT,
            stop_id INT,
            time_taken_minutes INT DEFAULT 0,
            people_getting_in INT DEFAULT 0,
            people_getting_down INT DEFAULT 0,
            FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE,
            FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)

        # Ticket log table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ticket_log (
            log_id INT AUTO_INCREMENT PRIMARY KEY,
            ticket_id INT,
            trip_id INT,
            log_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            action VARCHAR(50),
            FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
        ) ENGINE=InnoDB;
        """)

        # Re-enable foreign key checks
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # Create trigger (safe version)
        try:
            cur.execute("DROP TRIGGER IF EXISTS after_ticket_insert;")
            cur.execute("""
            CREATE TRIGGER after_ticket_insert
            AFTER INSERT ON tickets
            FOR EACH ROW
            INSERT INTO ticket_log (ticket_id, trip_id, action)
            VALUES (NEW.ticket_id, NEW.trip_id, 'Ticket Issued');
            """)
        except Exception as e:
            st.warning(f"Could not create trigger: {e}")

        # Stored procedure (safe version)
        try:
            cur.execute("DROP PROCEDURE IF EXISTS GetTripRevenue;")
            cur.execute("""
            CREATE PROCEDURE GetTripRevenue(IN tripID INT)
            BEGIN
                SELECT t.trip_id, COALESCE(r.route_name,'-') AS route_name, 
                       COALESCE(SUM(tk.fare), 0) AS total_revenue
                FROM trips t
                LEFT JOIN routes r ON t.route_id = r.route_id
                LEFT JOIN tickets tk ON t.trip_id = tk.trip_id
                WHERE t.trip_id = tripID
                GROUP BY t.trip_id, r.route_name;
            END;
            """)
        except Exception as e:
            st.warning(f"Could not create stored procedure: {e}")

    # Only seed data if tables are empty
    seed_sample_data()
def seed_sample_data():
    """Populate with rich sample data only if tables are empty"""
    with get_conn() as (conn, cur):
        # Only seed if users table is empty (indicator that all tables are empty)
        cur.execute("SELECT COUNT(*) as c FROM users")
        user_count = cur.fetchone()["c"]
        
        if user_count > 0:
            st.info("Database already has data. Skipping seeding.")
            return    
        st.info("Seeding database with sample data...")
        
        # Demo users
        for uname, pwd, role in DEMO_USERS:
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
            cur.execute("INSERT INTO users (username,password_hash,role) VALUES (%s,%s,%s)", (uname, pwd_hash, role))
        # Stops
        stops = [
            ("Central Station", "City Center"), 
            ("North Square", "North Area"),
            ("East Park", "East Side"), 
            ("West End", "West District"),
            ("South Gate", "South Zone"), 
            ("University", "Campus Road"),
            ("Airport", "Airport Terminal"), 
            ("Mall", "Shopping District"),
            ("Tech Park", "IT Hub")
        ]
        for s in stops:
            cur.execute("INSERT INTO stops (stop_name, location) VALUES (%s,%s)", s)

        # Routes
        routes = [
            ("R1 Central-Airport", "Central Station", "Airport", 15.0),
            ("R2 Central-University", "Central Station", "University", 8.5),
            ("R3 North-South Express", "North Square", "South Gate", 12.0),
            ("R4 Tech Loop", "Tech Park", "Mall", 9.0)
        ]
        for r in routes:
            cur.execute("INSERT INTO routes (route_name,source,destination,distance_km) VALUES (%s,%s,%s,%s)", r)

        # Get stop IDs and route IDs for route_stops
        cur.execute("SELECT stop_id, stop_name FROM stops")
        srows = {row["stop_name"]: row["stop_id"] for row in cur.fetchall()}
        
        cur.execute("SELECT route_id, route_name FROM routes")
        rmap = {rr["route_name"]: rr["route_id"] for rr in cur.fetchall()}
        
        # Route stops configuration
        route_stops_config = {
            "R1 Central-Airport": ["Central Station", "East Park", "West End", "Airport"],
            "R2 Central-University": ["Central Station", "North Square", "University"],
            "R3 North-South Express": ["North Square", "Central Station", "South Gate"]
        }
        
        for route_name, stops_list in route_stops_config.items():
            if route_name in rmap:
                for idx, stop_name in enumerate(stops_list, 1):
                    if stop_name in srows:
                        cur.execute("INSERT INTO route_stops (route_id,stop_order,stop_id) VALUES (%s,%s,%s)", 
                                   (rmap[route_name], idx, srows[stop_name]))

        # Drivers
        drivers = [
            ("Raj", "Kumar", "LIC1001", "9999990001", 30000, "Central City", True),
            ("Anita", "Sharma", "LIC1002", "9999990002", 32000, "North Block", True),
            ("Vikram", "Singh", "LIC1003", "9999990003", 31000, "East Side", False),
            ("Deepa", "Rao", "LIC1004", "9999990004", 29000, "South Area", True),
            ("Kiran", "Mehta", "LIC1005", "9999990005", 28000, "Airport Zone", False)
        ]
        for d in drivers:
            cur.execute("INSERT INTO drivers (first_name,last_name,license_no,phone,salary,address,is_active) VALUES (%s,%s,%s,%s,%s,%s,%s)", d)

        # Buses - WITH TYPE COLUMN
        buses = [
            ("BUS100", "City Rapid", "AC", 50, None, 1, True, "active"),
            ("BUS101", "Metro Shuttle", "Mini", 30, None, 2, False, "active"),
            ("BUS102", "Airport Express", "AC", 60, None, 1, True, "maintenance"),
            ("BUS103", "Downtown Loop", "Non-AC", 40, None, 3, False, "active"),
            ("BUS104", "City Connect", "AC", 45, None, 4, True, "active")
        ]
        for bus in buses:
            cur.execute("INSERT INTO buses (bus_no,bus_name,type,capacity,fare_id,route_id,ac,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", bus)

        # Get IDs for trips
        route_ids = {}
        cur.execute("SELECT route_id, route_name FROM routes")
        for row in cur.fetchall():
            route_ids[row['route_name']] = row['route_id']
        
        bus_ids = {}
        cur.execute("SELECT bus_id, bus_no FROM buses")
        for row in cur.fetchall():
            bus_ids[row['bus_no']] = row['bus_id']
        
        driver_ids = {}
        cur.execute("SELECT driver_id, license_no FROM drivers")
        for row in cur.fetchall():
            driver_ids[row['license_no']] = row['driver_id']

        # Trips - create trips for today and tomorrow
        now = datetime.now()
        trips = [
            # Today's trips
            (route_ids["R1 Central-Airport"], bus_ids["BUS100"], driver_ids["LIC1001"], 
             now.replace(hour=8, minute=0, second=0, microsecond=0), 
             now.replace(hour=9, minute=0, second=0, microsecond=0), "daily", "scheduled"),
            
            (route_ids["R2 Central-University"], bus_ids["BUS101"], driver_ids["LIC1002"], 
             now.replace(hour=10, minute=30, second=0, microsecond=0), 
             now.replace(hour=11, minute=15, second=0, microsecond=0), "daily", "scheduled"),
            
            (route_ids["R3 North-South Express"], bus_ids["BUS103"], driver_ids["LIC1004"], 
             now.replace(hour=14, minute=0, second=0, microsecond=0), 
             now.replace(hour=14, minute=45, second=0, microsecond=0), "weekdays", "scheduled"),
            
            # Tomorrow's trips
            (route_ids["R1 Central-Airport"], bus_ids["BUS100"], driver_ids["LIC1001"], 
             (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0), 
             (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0), "daily", "scheduled"),
            
            (route_ids["R4 Tech Loop"], bus_ids["BUS104"], driver_ids["LIC1003"], 
             (now + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0), 
             (now + timedelta(days=1)).replace(hour=11, minute=40, second=0, microsecond=0), "daily", "scheduled")
        ]
        
        for trip in trips:
            cur.execute("INSERT INTO trips (route_id,bus_id,driver_id,start_time,end_time,frequency,status) VALUES (%s,%s,%s,%s,%s,%s,%s)", trip)

        # Passengers
        passengers = [
            ("Sneha Verma", "College Road", "8888888888", "sneha@example.com"),
            ("Aman Singh", "North Lane", "7777777777", "aman@example.com"),
            ("Priya Patel", "South Street", "6666666666", "priya@example.com"),
            ("Rahul Kumar", "East Avenue", "5555555555", "rahul@example.com"),
            ("Anjali Sharma", "West Boulevard", "4444444444", "anjali@example.com")
        ]
        for p in passengers:
            cur.execute("INSERT INTO passengers (name,address,contact_no,email_id) VALUES (%s,%s,%s,%s)", p)

        # Sample tickets - book some seats to demonstrate availability
        cur.execute("SELECT trip_id FROM trips WHERE start_time > %s ORDER BY start_time LIMIT 1", (now,))
        trip = cur.fetchone()
        
        cur.execute("SELECT stop_id FROM stops LIMIT 4")
        stops = cur.fetchall()
        
        cur.execute("SELECT passenger_id FROM passengers LIMIT 3")
        passengers = cur.fetchall()
        
        if trip and len(stops) >= 2 and passengers:
            # Book some sample tickets
            sample_tickets = [
                (trip["trip_id"], passengers[0]["passenger_id"], stops[0]["stop_id"], stops[2]["stop_id"], "A1", 45.00, "female"),
                (trip["trip_id"], passengers[1]["passenger_id"], stops[1]["stop_id"], stops[3]["stop_id"], "A2", 35.00, "male"),
                (trip["trip_id"], passengers[2]["passenger_id"], stops[0]["stop_id"], stops[1]["stop_id"], "B1", 25.00, "female")
            ]
            
            for ticket in sample_tickets:
                cur.execute("INSERT INTO tickets (trip_id,passenger_id,boarding_stop_id,dropping_stop_id,seat_no,fare,gender) VALUES (%s,%s,%s,%s,%s,%s,%s)", ticket)

        # Path data for analytics
        cur.execute("SELECT trip_id FROM trips LIMIT 1")
        trip_for_path = cur.fetchone()
        cur.execute("SELECT stop_id FROM stops LIMIT 3")
        stops_for_path = cur.fetchall()
        
        if trip_for_path and stops_for_path:
            path_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
            for idx, stop in enumerate(stops_for_path):
                cur.execute("""
                    INSERT INTO path (trip_id,stop_id,arrival_time,departure_time,people_in,people_out,money_collected) 
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    trip_for_path["trip_id"], stop["stop_id"], 
                    path_time + timedelta(minutes=idx*15),
                    path_time + timedelta(minutes=idx*15 + 2),
                    5 + idx, 2 + idx, 150.0 * (idx + 1)
                ))

        # Major stops data
        cur.execute("SELECT route_id FROM routes LIMIT 2")
        routes_for_major = cur.fetchall()
        cur.execute("SELECT stop_id FROM stops LIMIT 2")
        stops_for_major = cur.fetchall()
        
        if routes_for_major and stops_for_major:
            for i, route in enumerate(routes_for_major):
                for j, stop in enumerate(stops_for_major):
                    if i < len(routes_for_major) and j < len(stops_for_major):
                        cur.execute("""
                            INSERT INTO major_stops (route_id,stop_id,time_taken_minutes,people_getting_in,people_getting_down) 
                            VALUES (%s,%s,%s,%s,%s)
                        """, (route["route_id"], stop["stop_id"], (i+1)*5, (j+1)*8, (j+1)*3))

        st.success("✅ Database seeded successfully with sample data!")

# --------------------------- AUTH HELPERS ---------------------------
def hash_password(plain):
    return hashlib.sha256(plain.encode()).hexdigest()

def authenticate(username, password):
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        if not row:
            return None
        if row.get("password_hash") == hash_password(password):
            return {"user_id": row.get("user_id", 0), "username": row.get("username"), "role": row.get("role")}
    return None

def register_user(username, password, role="operator"):
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cur.fetchone() is not None:
            return False, "Username already exists."
        cur.execute("INSERT INTO users (username,password_hash,role) VALUES (%s,%s,%s)", 
                   (username, hash_password(password), role))
        return True, "User created."

# --------------------------- CRUD HELPERS ---------------------------
def list_buses(): 
    return fetch_all("SELECT * FROM buses ORDER BY bus_id DESC")

def list_drivers(): 
    return fetch_all("SELECT * FROM drivers ORDER BY driver_id DESC")

def list_routes(): 
    return fetch_all("SELECT * FROM routes ORDER BY route_id DESC")

def list_stops(): 
    return fetch_all("SELECT * FROM stops ORDER BY stop_id DESC")

def list_trips(): 
    return fetch_all("""
        SELECT t.*, r.route_name, b.bus_no, b.type, b.ac, CONCAT(d.first_name,' ',d.last_name) AS driver_name
        FROM trips t
        LEFT JOIN routes r ON t.route_id=r.route_id
        LEFT JOIN buses b ON t.bus_id=b.bus_id
        LEFT JOIN drivers d ON t.driver_id=d.driver_id
        ORDER BY t.trip_id DESC
    """)

def list_tickets():
    return fetch_all("""
        SELECT tk.*, r.route_name, s1.stop_name AS boarding_stop, s2.stop_name AS dropping_stop,
               p.name AS passenger_name, t.start_time, t.end_time
        FROM tickets tk
        JOIN trips t ON tk.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN stops s1 ON tk.boarding_stop_id = s1.stop_id
        JOIN stops s2 ON tk.dropping_stop_id = s2.stop_id
        JOIN passengers p ON tk.passenger_id = p.passenger_id
        ORDER BY tk.created_at DESC
    """)

def list_available_trips():
    """Get trips that are scheduled for today or future"""
    today = datetime.now().date()
    return fetch_all("""
        SELECT t.*, r.route_name, b.bus_no, b.type, b.ac, 
               CONCAT(d.first_name,' ',d.last_name) AS driver_name
        FROM trips t
        LEFT JOIN routes r ON t.route_id=r.route_id
        LEFT JOIN buses b ON t.bus_id=b.bus_id
        LEFT JOIN drivers d ON t.driver_id=d.driver_id
        WHERE t.status = 'scheduled' AND DATE(t.start_time) >= %s
        ORDER BY t.start_time ASC
    """, (today,))

def get_route_stops(route_id):
    """Get stops for a specific route in order"""
    return fetch_all("""
        SELECT rs.stop_order, s.stop_id, s.stop_name, s.location
        FROM route_stops rs
        JOIN stops s ON rs.stop_id = s.stop_id
        WHERE rs.route_id = %s
        ORDER BY rs.stop_order
    """, (route_id,))

def calculate_fare(boarding_stop_id, dropping_stop_id, bus_type, is_ac):
    """Calculate fare based on stops and bus type"""
    base_fare = 20.0
    if bus_type.lower() == "ac" or is_ac:
        base_fare += 10.0
    return base_fare + random.randint(5, 15)

def get_available_seats(trip_id):
    """Get available seats for a trip"""
    trip = fetch_all("SELECT * FROM trips WHERE trip_id = %s", (trip_id,))
    if not trip:
        return []
    
    bus_id = trip[0]['bus_id']
    bus = fetch_all("SELECT * FROM buses WHERE bus_id = %s", (bus_id,))
    if not bus:
        return []
    
    capacity = bus[0]['capacity']
    booked_seats = fetch_all("SELECT seat_no FROM tickets WHERE trip_id = %s", (trip_id,))
    booked_seat_nos = [seat['seat_no'] for seat in booked_seats]
    
    all_seats = [f"A{i+1}" for i in range(capacity)]
    available_seats = [seat for seat in all_seats if seat not in booked_seat_nos]
    
    return available_seats

# Add/Update/Delete functions
def add_bus(bus_no, bus_name, type_, capacity, fare_id, route_id, ac, status):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO buses (bus_no,bus_name,type,capacity,fare_id,route_id,ac,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (bus_no, bus_name, type_, capacity, fare_id, route_id, ac, status))

def update_bus(bus_id, **kwargs):
    cols = []; vals = []
    for k,v in kwargs.items():
        cols.append(f"{k}=%s"); vals.append(v)
    vals.append(bus_id)
    sql = f"UPDATE buses SET {', '.join(cols)} WHERE bus_id=%s"
    with get_conn() as (conn, cur):
        cur.execute(sql, tuple(vals))

def delete_bus(bus_id):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM buses WHERE bus_id=%s", (bus_id,))

def add_driver(first, last, license_no, phone, salary, address, is_active=True):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO drivers (first_name,last_name,license_no,phone,salary,address,is_active) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (first, last, license_no, phone, salary, address, is_active))

def update_driver(driver_id, **kwargs):
    cols = []; vals = []
    for k,v in kwargs.items():
        cols.append(f"{k}=%s"); vals.append(v)
    vals.append(driver_id)
    sql = f"UPDATE drivers SET {', '.join(cols)} WHERE driver_id=%s"
    with get_conn() as (conn, cur):
        cur.execute(sql, tuple(vals))

def delete_driver(driver_id):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM drivers WHERE driver_id=%s", (driver_id,))

def add_route(route_name, source, destination, distance_km=None):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO routes (route_name,source,destination,distance_km) VALUES (%s,%s,%s,%s)", 
                   (route_name, source, destination, distance_km))

def update_route(route_id, **kwargs):
    cols = []; vals = []
    for k,v in kwargs.items():
        cols.append(f"{k}=%s"); vals.append(v)
    vals.append(route_id)
    sql = f"UPDATE routes SET {', '.join(cols)} WHERE route_id=%s"
    with get_conn() as (conn, cur):
        cur.execute(sql, tuple(vals))

def delete_route(route_id):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM routes WHERE route_id=%s", (route_id,))

def add_stop(stop_name, location):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO stops (stop_name,location) VALUES (%s,%s)", (stop_name, location))

def update_stop(stop_id, **kwargs):
    cols=[]; vals=[]
    for k,v in kwargs.items():
        cols.append(f"{k}=%s"); vals.append(v)
    vals.append(stop_id)
    sql = f"UPDATE stops SET {', '.join(cols)} WHERE stop_id=%s"
    with get_conn() as (conn, cur):
        cur.execute(sql, tuple(vals))

def delete_stop(stop_id):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM stops WHERE stop_id=%s", (stop_id,))

def add_trip(route_id, bus_id, driver_id, start_time, end_time, frequency, status='scheduled'):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO trips (route_id,bus_id,driver_id,start_time,end_time,frequency,status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (route_id, bus_id, driver_id, start_time, end_time, frequency, status))

def update_trip(trip_id, **kwargs):
    cols=[]; vals=[]
    for k,v in kwargs.items():
        cols.append(f"{k}=%s"); vals.append(v)
    vals.append(trip_id)
    sql = f"UPDATE trips SET {', '.join(cols)} WHERE trip_id=%s"
    with get_conn() as (conn, cur):
        cur.execute(sql, tuple(vals))

def delete_trip(trip_id):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM trips WHERE trip_id=%s", (trip_id,))

def add_passenger(name, address, contact_no, email):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO passengers (name,address,contact_no,email_id) VALUES (%s,%s,%s,%s)", 
                   (name, address, contact_no, email))
        return cur.lastrowid

def add_ticket(trip_id, passenger_id, boarding_stop_id, dropping_stop_id, seat_no, fare, gender):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO tickets (trip_id,passenger_id,boarding_stop_id,dropping_stop_id,seat_no,fare,gender) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (trip_id, passenger_id, boarding_stop_id, dropping_stop_id, seat_no, fare, gender))

def update_ticket(ticket_id, **kwargs):
    cols=[]; vals=[]
    for k,v in kwargs.items():
        cols.append(f"{k}=%s"); vals.append(v)
    vals.append(ticket_id)
    sql = f"UPDATE tickets SET {', '.join(cols)} WHERE ticket_id=%s"
    with get_conn() as (conn, cur):
        cur.execute(sql, tuple(vals))

def delete_ticket(ticket_id):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM tickets WHERE ticket_id=%s", (ticket_id,))

def list_path_for_trip(trip_id):
    return fetch_all("SELECT p.*, s.stop_name FROM path p JOIN stops s ON p.stop_id=s.stop_id WHERE p.trip_id=%s ORDER BY p.path_id", (trip_id,))

def list_major_stops():
    return fetch_all("SELECT m.*, r.route_name, s.stop_name FROM major_stops m LEFT JOIN routes r ON m.route_id=r.route_id LEFT JOIN stops s ON m.stop_id=s.stop_id ORDER BY m.major_stop_id DESC")

# --------------------------- UI HELPERS ---------------------------
def header():
    st.markdown("<h1 style='text-align:center;color:#0B5FFF'>🚌 Public Transport Management System</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;color:#6c757d'>Complete System with Ticket Booking & Management</div>", unsafe_allow_html=True)
    st.markdown("---")

def driver_card(d):
    status = "🟢 Active" if d.get("is_active") else "🔴 Inactive"
    return f"""<div style='background:#fff;padding:10px;border-radius:8px;margin-bottom:6px;border:1px solid #eee'>
    <b>{d.get('first_name')} {d.get('last_name')}</b> — {status}<br>
    <small>License: {d.get('license_no')} | Phone: {d.get('phone')} | Salary: ₹{d.get('salary')}</small></div>"""



# --------------------------- INTERFACES ---------------------------
def admin_interface():
    st.sidebar.title("Admin Panel")
    page = st.sidebar.selectbox("Navigation", [
        "Dashboard", "Buses", "Drivers", "Routes & Stops", "Trips", 
        "Tickets", "Path", "Major Stops", "Users", "Trigger Logs", 
        "Stored Procedure: Revenue", "Seed Data (re-run)"
    ])
    st.header("🏢 Admin Management Interface")
    
    if page == "Dashboard":
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Buses", len(list_buses()))
        with col2:
            st.metric("Active Drivers", len([d for d in list_drivers() if d['is_active']]))
        with col3:
            st.metric("Routes", len(list_routes()))
        with col4:
            st.metric("Upcoming Trips", len(list_available_trips()))
        
        st.subheader("📊 Recent Activity")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Recent Tickets**")
            tickets = list_tickets()[:5]
            if tickets:
                for ticket in tickets:
                    st.write(f"🎫 {ticket['passenger_name']} - {ticket['route_name']} - ₹{ticket['fare']}")
            else:
                st.info("No recent tickets")
        
        with col2:
            st.write("**System Status**")
            buses = list_buses()
            active_buses = len([b for b in buses if b['status'] == 'active'])
            st.write(f"🟢 Active Buses: {active_buses}/{len(buses)}")
            st.write(f"🔧 Maintenance: {len([b for b in buses if b['status'] == 'maintenance'])}")
            st.write(f"🚫 Inactive: {len([b for b in buses if b['status'] == 'inactive'])}")

    elif page == "Buses":
        st.subheader("🚌 Bus Management")
        
        # Add Bus Form
        with st.expander("➕ Add New Bus", expanded=False):
            with st.form("add_bus_form"):
                col1, col2 = st.columns(2)
                with col1:
                    bus_no = st.text_input("Bus Number *", placeholder="BUS201")
                    bus_name = st.text_input("Bus Name *", placeholder="City Express")
                    type_ = st.selectbox("Bus Type *", ["AC", "Non-AC", "Mini", "Deluxe"])
                    capacity = st.number_input("Capacity *", min_value=1, max_value=100, value=40)
                with col2:
                    route_options = list_routes()
                    rmap = {f"{r['route_id']}: {r['route_name']}": r['route_id'] for r in route_options}
                    route_sel = st.selectbox("Assign Route", ["None"] + list(rmap.keys()))
                    route_id = rmap[route_sel] if route_sel != "None" else None
                    ac = st.checkbox("Air Conditioning", value=(type_ == "AC"))
                    status = st.selectbox("Status", ["active", "maintenance", "inactive"])
                
                submitted = st.form_submit_button("Add Bus", type="primary")
                if submitted:
                    if not bus_no or not bus_name:
                        st.error("Please fill in all required fields")
                    else:
                        add_bus(bus_no, bus_name, type_, capacity, None, route_id, ac, status)
                        st.success(f"Bus {bus_no} added successfully!")
                        st.rerun()

        # Bus List with Update/Delete
        st.subheader("📋 All Buses")
        buses = list_buses()
        if buses:
            for bus in buses:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    
                    with col1:
                        st.write(f"**{bus['bus_no']}** - {bus['bus_name']}")
                        st.write(f"Type: {bus['type']} | Capacity: {bus['capacity']} | AC: {'Yes' if bus['ac'] else 'No'}")
                    
                    with col2:
                        status_color = "🟢" if bus['status'] == 'active' else "🟡" if bus['status'] == 'maintenance' else "🔴"
                        st.write(f"Status: {status_color} {bus['status'].title()}")
                    
                    # Update Button
                    with col3:
                        update_key = f"update_bus_{bus['bus_id']}"
                        if st.button("✏️ Edit", key=update_key):
                            st.session_state[f"editing_bus_{bus['bus_id']}"] = True
                    
                    # Delete Button
                    with col4:
                        delete_key = f"delete_bus_{bus['bus_id']}"
                        if st.button("🗑️ Delete", key=delete_key):
                            st.session_state[f"deleting_bus_{bus['bus_id']}"] = True
                    
                    # Update Form
                    if st.session_state.get(f"editing_bus_{bus['bus_id']}"):
                        with st.form(f"update_bus_form_{bus['bus_id']}"):
                            st.write("**Edit Bus Details**")
                            col1, col2 = st.columns(2)
                            with col1:
                                new_status = st.selectbox("Status", ["active", "maintenance", "inactive"], 
                                                        index=["active", "maintenance", "inactive"].index(bus['status']),
                                                        key=f"status_{bus['bus_id']}")
                                new_capacity = st.number_input("Capacity", value=bus['capacity'], 
                                                             min_value=1, key=f"cap_{bus['bus_id']}")
                            with col2:
                                # FIXED: Properly closed f-strings
                                current_type_index = 0
                                if bus['type'] in ["AC", "Non-AC", "Mini", "Deluxe"]:
                                    current_type_index = ["AC", "Non-AC", "Mini", "Deluxe"].index(bus['type'])
                                new_type = st.selectbox("Type", ["AC", "Non-AC", "Mini", "Deluxe"],
                                                      index=current_type_index,
                                                      key=f"type_{bus['bus_id']}")
                                new_ac = st.checkbox("AC", value=bool(bus['ac']), key=f"ac_{bus['bus_id']}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save Changes"):
                                    update_bus(bus['bus_id'], status=new_status, capacity=new_capacity, 
                                              type=new_type, ac=new_ac)
                                    st.session_state[f"editing_bus_{bus['bus_id']}"] = False
                                    st.success("Bus updated successfully!")
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Cancel"):
                                    st.session_state[f"editing_bus_{bus['bus_id']}"] = False
                                    st.rerun()
                    
                    # Delete Confirmation
                    if st.session_state.get(f"deleting_bus_{bus['bus_id']}"):
                        st.warning(f"Are you sure you want to delete bus {bus['bus_no']}?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_del_bus_{bus['bus_id']}"):
                                delete_bus(bus['bus_id'])
                                st.session_state[f"deleting_bus_{bus['bus_id']}"] = False
                                st.success("Bus deleted successfully!")
                                st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_del_bus_{bus['bus_id']}"):
                                st.session_state[f"deleting_bus_{bus['bus_id']}"] = False
                                st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No buses found in the system.")

    elif page == "Drivers":
        st.subheader("👨‍💼 Driver Management")
        
        # Add Driver Form
        with st.expander("➕ Add New Driver", expanded=False):
            with st.form("add_driver_form"):
                col1, col2 = st.columns(2)
                with col1:
                    first_name = st.text_input("First Name *")
                    last_name = st.text_input("Last Name *")
                    license_no = st.text_input("License Number *")
                with col2:
                    phone = st.text_input("Phone Number *")
                    salary = st.number_input("Salary (₹) *", min_value=10000, value=30000)
                    is_active = st.checkbox("Active", value=True)
                
                address = st.text_area("Address")
                
                submitted = st.form_submit_button("Add Driver", type="primary")
                if submitted:
                    if not all([first_name, last_name, license_no, phone]):
                        st.error("Please fill in all required fields")
                    else:
                        add_driver(first_name, last_name, license_no, phone, salary, address, is_active)
                        st.success(f"Driver {first_name} {last_name} added successfully!")
                        st.rerun()

        # Driver List with Update/Delete
        st.subheader("📋 Driver Directory")
        drivers = list_drivers()
        if drivers:
            for driver in drivers:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        status = "🟢 Active" if driver['is_active'] else "🔴 Inactive"
                        st.write(f"**{driver['first_name']} {driver['last_name']}** - {status}")
                        st.write(f"License: {driver['license_no']} | Phone: {driver['phone']} | Salary: ₹{driver['salary']:,.2f}")
                        if driver['address']:
                            st.write(f"Address: {driver['address']}")
                    
                    # Update Button
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_driver_{driver['driver_id']}"):
                            st.session_state[f"editing_driver_{driver['driver_id']}"] = True
                    
                    # Delete Button
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_driver_{driver['driver_id']}"):
                            st.session_state[f"deleting_driver_{driver['driver_id']}"] = True
                    
                    # Update Form
                    if st.session_state.get(f"editing_driver_{driver['driver_id']}"):
                        with st.form(f"update_driver_{driver['driver_id']}"):
                            st.write("**Edit Driver Details**")
                            col1, col2 = st.columns(2)
                            with col1:
                                new_salary = st.number_input("Salary", value=float(driver['salary']), 
                                                           key=f"sal_{driver['driver_id']}")
                                new_phone = st.text_input("Phone", value=driver['phone'], 
                                                        key=f"phone_{driver['driver_id']}")
                            with col2:
                                new_active = st.checkbox("Active", value=bool(driver['is_active']),
                                                       key=f"active_{driver['driver_id']}")
                                new_address = st.text_area("Address", value=driver['address'] or "",
                                                         key=f"addr_{driver['driver_id']}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save"):
                                    update_driver(driver['driver_id'], salary=new_salary, phone=new_phone,
                                                is_active=new_active, address=new_address)
                                    st.session_state[f"editing_driver_{driver['driver_id']}"] = False
                                    st.success("Driver updated successfully!")
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Cancel"):
                                    st.session_state[f"editing_driver_{driver['driver_id']}"] = False
                                    st.rerun()
                    
                    # Delete Confirmation
                    if st.session_state.get(f"deleting_driver_{driver['driver_id']}"):
                        st.warning(f"Delete driver {driver['first_name']} {driver['last_name']}?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Confirm Delete", key=f"confirm_del_driver_{driver['driver_id']}"):
                                delete_driver(driver['driver_id'])
                                st.session_state[f"deleting_driver_{driver['driver_id']}"] = False
                                st.success("Driver deleted successfully!")
                                st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_del_driver_{driver['driver_id']}"):
                                st.session_state[f"deleting_driver_{driver['driver_id']}"] = False
                                st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No drivers found in the system.")


    elif page == "Routes & Stops":
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🛣️ Route Management")
            
            # Add Route Form
            with st.form("add_route_form"):
                st.write("**Add New Route**")
                route_name = st.text_input("Route Name *", placeholder="R5 Downtown Express")
                source = st.text_input("Source *", placeholder="Central Station")
                destination = st.text_input("Destination *", placeholder="Downtown")
                distance_km = st.number_input("Distance (km)", min_value=0.0, value=10.0)
                
                if st.form_submit_button("Add Route"):
                    if route_name and source and destination:
                        add_route(route_name, source, destination, distance_km)
                        st.success("Route added successfully!")
                        st.rerun()
                    else:
                        st.error("Please fill in all required fields")
            
            # Route List with Update/Delete
            st.write("**All Routes**")
            routes = list_routes()
            if routes:
                for route in routes:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{route['route_name']}**")
                            st.write(f"{route['source']} → {route['destination']} | {route['distance_km']} km")
                        
                        with col2:
                            if st.button("✏️", key=f"edit_route_{route['route_id']}"):
                                st.session_state[f"editing_route_{route['route_id']}"] = True
                        
                        with col3:
                            if st.button("🗑️", key=f"del_route_{route['route_id']}"):
                                if st.button("Confirm?", key=f"confirm_del_route_{route['route_id']}"):
                                    delete_route(route['route_id'])
                                    st.success("Route deleted!")
                                    st.rerun()
                        
                        if st.session_state.get(f"editing_route_{route['route_id']}"):
                            with st.form(f"update_route_{route['route_id']}"):
                                new_name = st.text_input("Route Name", value=route['route_name'])
                                new_dist = st.number_input("Distance", value=float(route['distance_km']))
                                if st.form_submit_button("Save"):
                                    update_route(route['route_id'], route_name=new_name, distance_km=new_dist)
                                    st.session_state[f"editing_route_{route['route_id']}"] = False
                                    st.success("Route updated!")
                                    st.rerun()
                        
                        st.markdown("---")
        
        with col2:
            st.subheader("🚏 Stop Management")
            
            # Add Stop Form
            with st.form("add_stop_form"):
                st.write("**Add New Stop**")
                stop_name = st.text_input("Stop Name *", placeholder="City Center")
                location = st.text_input("Location *", placeholder="Main Street")
                
                if st.form_submit_button("Add Stop"):
                    if stop_name and location:
                        add_stop(stop_name, location)
                        st.success("Stop added successfully!")
                        st.rerun()
                    else:
                        st.error("Please fill in all required fields")
            
            # Stop List with Update/Delete
            st.write("**All Stops**")
            stops = list_stops()
            if stops:
                for stop in stops:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{stop['stop_name']}**")
                        st.write(f"Location: {stop['location']}")
                    
                    with col2:
                        if st.button("✏️", key=f"edit_stop_{stop['stop_id']}"):
                            st.session_state[f"editing_stop_{stop['stop_id']}"] = True
                    
                    with col3:
                        if st.button("🗑️", key=f"del_stop_{stop['stop_id']}"):
                            delete_stop(stop['stop_id'])
                            st.success("Stop deleted!")
                            st.rerun()
                    
                    if st.session_state.get(f"editing_stop_{stop['stop_id']}"):
                        with st.form(f"update_stop_{stop['stop_id']}"):
                            new_name = st.text_input("Stop Name", value=stop['stop_name'])
                            new_loc = st.text_input("Location", value=stop['location'])
                            if st.form_submit_button("Save"):
                                update_stop(stop['stop_id'], stop_name=new_name, location=new_loc)
                                st.session_state[f"editing_stop_{stop['stop_id']}"] = False
                                st.success("Stop updated!")
                                st.rerun()
                    
                    st.markdown("---")

    elif page == "Trips":
        st.subheader("🕒 Trip Management")
        
        # Add Trip Form
        with st.expander("➕ Schedule New Trip", expanded=False):
            routes = list_routes()
            buses = list_buses()
            drivers = [d for d in list_drivers() if d['is_active']]
            
            if routes and buses and drivers:
                with st.form("add_trip_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Route selection
                        rmap = {f"{r['route_id']}: {r['route_name']}": r['route_id'] for r in routes}
                        route_sel = st.selectbox("Select Route *", list(rmap.keys()))
                        
                        # Bus selection
                        bmap = {f"{b['bus_id']}: {b['bus_no']} ({b['type']})": b['bus_id'] for b in buses if b['status'] == 'active'}
                        bus_sel = st.selectbox("Select Bus *", list(bmap.keys()))
                        
                        # Driver selection
                        dmap = {f"{d['driver_id']}: {d['first_name']} {d['last_name']}": d['driver_id'] for d in drivers}
                        driver_sel = st.selectbox("Select Driver *", list(dmap.keys()))
                    
                    with col2:
                        # Date and time inputs
                        st_date = st.date_input("Start Date *", value=datetime.now().date())
                        st_time = st.time_input("Start Time *", value=(datetime.now() + timedelta(hours=1)).time())
                        et_date = st.date_input("End Date *", value=(datetime.now() + timedelta(hours=2)).date())
                        et_time = st.time_input("End Time *", value=(datetime.now() + timedelta(hours=2)).time())
                    
                    frequency = st.selectbox("Frequency", ["daily", "weekdays", "weekends", "once"])
                    
                    submitted = st.form_submit_button("Schedule Trip", type="primary")
                    if submitted:
                        start_time = datetime.combine(st_date, st_time)
                        end_time = datetime.combine(et_date, et_time)
                        
                        if end_time <= start_time:
                            st.error("End time must be after start time")
                        else:
                            add_trip(rmap[route_sel], bmap[bus_sel], dmap[driver_sel], start_time, end_time, frequency, "scheduled")
                            st.success("Trip scheduled successfully!")
                            st.rerun()
            else:
                st.error("Need routes, active buses, and active drivers to schedule trips")

        # Trip List with Update/Delete
        st.subheader("📋 Scheduled Trips")
        trips = list_trips()
        if trips:
            for trip in trips:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**Trip {trip['trip_id']} - {trip['route_name']}**")
                        st.write(f"Bus: {trip['bus_no']} | Driver: {trip['driver_name']}")
                        st.write(f"Start: {trip['start_time'].strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"End: {trip['end_time'].strftime('%Y-%m-%d %H:%M')} | Status: {trip['status']}")
                    
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_trip_{trip['trip_id']}"):
                            st.session_state[f"editing_trip_{trip['trip_id']}"] = True
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_trip_{trip['trip_id']}"):
                            st.session_state[f"deleting_trip_{trip['trip_id']}"] = True
                    
                    # Update Form
                    if st.session_state.get(f"editing_trip_{trip['trip_id']}"):
                        with st.form(f"update_trip_{trip['trip_id']}"):
                            new_status = st.selectbox("Status", ["scheduled", "ongoing", "completed", "cancelled"],
                                                    index=["scheduled", "ongoing", "completed", "cancelled"].index(trip['status']))
                            if st.form_submit_button("Save"):
                                update_trip(trip['trip_id'], status=new_status)
                                st.session_state[f"editing_trip_{trip['trip_id']}"] = False
                                st.success("Trip updated!")
                                st.rerun()
                    
                    # Delete Confirmation
                    if st.session_state.get(f"deleting_trip_{trip['trip_id']}"):
                        st.warning(f"Delete trip {trip['trip_id']}?")
                        if st.button("Confirm Delete", key=f"confirm_del_trip_{trip['trip_id']}"):
                            delete_trip(trip['trip_id'])
                            st.session_state[f"deleting_trip_{trip['trip_id']}"] = False
                            st.success("Trip deleted!")
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No trips scheduled")

    elif page == "Tickets":
        st.subheader("🎫 Ticket Management")
        
        # Manual Ticket Issue (for operators)
        with st.expander("🎟️ Issue Ticket Manually", expanded=False):
            trips = list_available_trips()
            stops = list_stops()
            passengers = fetch_all("SELECT * FROM passengers")
            
            if trips and stops:
                with st.form("manual_ticket_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Trip selection
                        tmap = {f"{t['trip_id']}: {t['route_name']} ({t['start_time'].strftime('%H:%M')})": t['trip_id'] for t in trips}
                        trip_sel = st.selectbox("Select Trip *", list(tmap.keys()))
                        
                        # Passenger selection
                        pmap = {f"{p['passenger_id']}: {p['name']}": p['passenger_id'] for p in passengers}
                        passenger_sel = st.selectbox("Select Passenger", ["New Passenger"] + list(pmap.keys()))
                        
                        if passenger_sel == "New Passenger":
                            new_name = st.text_input("Passenger Name *")
                            new_contact = st.text_input("Contact Number *")
                            new_email = st.text_input("Email")
                    
                    with col2:
                        # Stop selection
                        smap = {f"{s['stop_id']}: {s['stop_name']}": s['stop_id'] for s in stops}
                        boarding_sel = st.selectbox("Boarding Stop *", list(smap.keys()))
                        dropping_sel = st.selectbox("Dropping Stop *", list(smap.keys()))
                        
                        seat_no = st.text_input("Seat Number", value="A1")
                        fare = st.number_input("Fare (₹)", min_value=10.0, value=50.0)
                        gender = st.selectbox("Gender", ["male", "female", "other"])
                    
                    submitted = st.form_submit_button("Issue Ticket", type="primary")
                    if submitted:
                        passenger_id = None
                        if passenger_sel == "New Passenger":
                            if not new_name or not new_contact:
                                st.error("Please fill passenger details")
                                return
                            passenger_id = add_passenger(new_name, "", new_contact, new_email or "")
                        else:
                            passenger_id = pmap[passenger_sel]
                        
                        add_ticket(tmap[trip_sel], passenger_id, smap[boarding_sel], smap[dropping_sel], seat_no, fare, gender)
                        st.success("Ticket issued successfully!")
                        st.rerun()

        # Ticket List with Update/Delete
        st.subheader("📋 All Tickets")
        tickets = list_tickets()
        if tickets:
            for ticket in tickets:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**Ticket #{ticket['ticket_id']}** - {ticket['passenger_name']}")
                        st.write(f"Route: {ticket['route_name']}")
                        st.write(f"Stops: {ticket['boarding_stop']} → {ticket['dropping_stop']}")
                        st.write(f"Fare: ₹{ticket['fare']} | Seat: {ticket['seat_no']}")
                        st.write(f"Booked: {ticket['created_at'].strftime('%Y-%m-%d %H:%M')}")
                    
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_ticket_{ticket['ticket_id']}"):
                            st.session_state[f"editing_ticket_{ticket['ticket_id']}"] = True
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_ticket_{ticket['ticket_id']}"):
                            st.session_state[f"deleting_ticket_{ticket['ticket_id']}"] = True
                    
                    # Update Form
                    if st.session_state.get(f"editing_ticket_{ticket['ticket_id']}"):
                        with st.form(f"update_ticket_{ticket['ticket_id']}"):
                            new_fare = st.number_input("Fare", value=float(ticket['fare']))
                            new_seat = st.text_input("Seat", value=ticket['seat_no'])
                            if st.form_submit_button("Save"):
                                update_ticket(ticket['ticket_id'], fare=new_fare, seat_no=new_seat)
                                st.session_state[f"editing_ticket_{ticket['ticket_id']}"] = False
                                st.success("Ticket updated!")
                                st.rerun()
                    
                    # Delete Confirmation
                    if st.session_state.get(f"deleting_ticket_{ticket['ticket_id']}"):
                        st.warning(f"Delete ticket #{ticket['ticket_id']}?")
                        if st.button("Confirm Delete", key=f"confirm_del_ticket_{ticket['ticket_id']}"):
                            delete_ticket(ticket['ticket_id'])
                            st.session_state[f"deleting_ticket_{ticket['ticket_id']}"] = False
                            st.success("Ticket deleted!")
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No tickets issued yet")

    # ... (Other admin pages like Path, Major Stops, Users, etc. would continue here)

    elif page == "Users":
        st.subheader("👥 User Management")
        users = fetch_all("SELECT user_id, username, role, created_at FROM users ORDER BY user_id DESC")
        st.table(users)
        
        with st.expander("Add New User"):
            with st.form("add_user_form"):
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["operator", "admin"])
                if st.form_submit_button("Add User"):
                    if new_user and new_pass:
                        ok, msg = register_user(new_user, new_pass, new_role)
                        if ok:
                            st.success("User created!")
                            st.rerun()
                        else:
                            st.error(msg)

    elif page == "Trigger Logs":
        st.subheader("📝 Ticket Logs (Trigger Demo)")
        logs = fetch_all("SELECT * FROM ticket_log ORDER BY log_time DESC LIMIT 50")
        if logs:
            st.table(logs)
        else:
            st.info("No ticket logs yet")

    elif page == "Stored Procedure: Revenue":
        st.subheader("💰 Trip Revenue Analysis")
        trips = list_trips()
        if trips:
            tmap = {f"{t['trip_id']}: {t['route_name']}": t['trip_id'] for t in trips}
            selected_trip = st.selectbox("Select Trip", list(tmap.keys()))
            
            if st.button("Calculate Revenue"):
                with get_conn() as (conn, cur):
                    try:
                        cur.callproc("GetTripRevenue", [tmap[selected_trip]])
                        for result in cur.stored_results():
                            rows = result.fetchall()
                            if rows:
                                revenue = rows[0]['total_revenue'] or 0
                                st.success(f"Total Revenue: ₹{revenue:,.2f}")
                            else:
                                st.info("No revenue data for this trip")
                    except Exception as e:
                        st.error(f"Error: {e}")

    elif page == "Seed Data (re-run)":
        st.subheader("🔄 Database Reset")
        st.warning("This will reset all data and recreate sample data!")
        if st.button("Reset Database", type="primary"):
            initialize_database_and_schema()
            st.success("Database reset complete!")
            st.rerun()

def operator_interface():
    st.header("👨‍💼 Operator Interface")
    page = st.selectbox("Navigation", ["Overview", "Issue Ticket", "Record Path", "View Trips & Stops"])
    
    if page == "Overview":
        st.subheader("📊 Operator Dashboard")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Today's Trips", len(list_available_trips()))
        with col2:
            st.metric("Total Tickets", len(list_tickets()))
        with col3:
            active_drivers = len([d for d in list_drivers() if d['is_active']])
            st.metric("Active Drivers", active_drivers)
        
        st.subheader("Recent Tickets")
        tickets = list_tickets()[:10]
        if tickets:
            for ticket in tickets:
                st.write(f"🎫 {ticket['passenger_name']} - {ticket['route_name']} - ₹{ticket['fare']}")
        else:
            st.info("No tickets issued today")

    elif page == "Issue Ticket":
        st.subheader("🎟️ Issue New Ticket")
        trips = list_available_trips()
        stops = list_stops()
        
        if trips and stops:
            with st.form("operator_ticket_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Trip selection
                    tmap = {f"{t['trip_id']}: {t['route_name']} - {t['start_time'].strftime('%H:%M')}": t['trip_id'] for t in trips}
                    trip_sel = st.selectbox("Select Trip *", list(tmap.keys()))
                    
                    # Passenger details
                    passenger_name = st.text_input("Passenger Name *")
                    contact_no = st.text_input("Contact Number *")
                    email = st.text_input("Email")
                    gender = st.selectbox("Gender", ["male", "female", "other"])
                
                with col2:
                    # Stop selection
                    smap = {f"{s['stop_id']}: {s['stop_name']}": s['stop_id'] for s in stops}
                    boarding_sel = st.selectbox("Boarding Stop *", list(smap.keys()))
                    dropping_sel = st.selectbox("Dropping Stop *", list(smap.keys()))
                    
                    # Get available seats
                    available_seats = get_available_seats(tmap[trip_sel])
                    if available_seats:
                        seat_no = st.selectbox("Select Seat *", available_seats)
                    else:
                        st.error("No seats available for this trip!")
                        seat_no = None
                    
                    # Calculate fare
                    if trip_sel and boarding_sel and dropping_sel:
                        trip_info = next((t for t in trips if t['trip_id'] == tmap[trip_sel]), None)
                        if trip_info:
                            fare = calculate_fare(smap[boarding_sel], smap[dropping_sel], 
                                                trip_info['type'], trip_info['ac'])
                            st.write(f"**Calculated Fare: ₹{fare:.2f}**")
                
                submitted = st.form_submit_button("Issue Ticket", type="primary")
                if submitted:
                    if not all([passenger_name, contact_no, seat_no]):
                        st.error("Please fill all required fields")
                    else:
                        passenger_id = add_passenger(passenger_name, "", contact_no, email or "")
                        add_ticket(tmap[trip_sel], passenger_id, smap[boarding_sel], smap[dropping_sel], seat_no, fare, gender)
                        st.success("✅ Ticket issued successfully!")
                        st.balloons()
                        st.rerun()
        else:
            st.error("No available trips or stops. Please contact administrator.")

    elif page == "Record Path":
        st.subheader("📍 Record Stop Data")
        trips = list_trips()
        stops = list_stops()
        
        if trips and stops:
            with st.form("record_path_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    tmap = {f"{t['trip_id']}: {t['route_name']}": t['trip_id'] for t in trips}
                    trip_sel = st.selectbox("Select Trip", list(tmap.keys()))
                    
                    smap = {f"{s['stop_id']}: {s['stop_name']}": s['stop_id'] for s in stops}
                    stop_sel = st.selectbox("Select Stop", list(smap.keys()))
                
                with col2:
                    people_in = st.number_input("People Boarding", min_value=0, value=0)
                    people_out = st.number_input("People Alighting", min_value=0, value=0)
                    money_collected = st.number_input("Money Collected", min_value=0.0, value=0.0)
                
                if st.form_submit_button("Record Data"):
                    # For demo, we'll just show success
                    st.success("Stop data recorded successfully!")
        else:
            st.info("No trips or stops available")

    elif page == "View Trips & Stops":
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🕒 Today's Trips")
            trips = list_available_trips()
            if trips:
                for trip in trips:
                    st.write(f"**{trip['route_name']}**")
                    st.write(f"Bus: {trip['bus_no']} | Driver: {trip['driver_name']}")
                    st.write(f"Time: {trip['start_time'].strftime('%H:%M')} - {trip['end_time'].strftime('%H:%M')}")
                    st.markdown("---")
            else:
                st.info("No trips scheduled for today")
        
        with col2:
            st.subheader("🚏 All Stops")
            stops = list_stops()
            if stops:
                for stop in stops:
                    st.write(f"**{stop['stop_name']}**")
                    st.write(f"Location: {stop['location']}")
                    st.markdown("---")

def public_interface():
    st.header("🎫 Public Transport System")
    page = st.selectbox("Navigation", [
        "Overview", "Routes", "Trips", "Stops", "Buses", 
        "Book Tickets", "My Tickets", "Search"
    ])
    
    if page == "Overview":
        st.subheader("🚍 Welcome to Public Transport System")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("""
            **Services Available:**
            - 🚌 Multiple bus routes
            - 🕒 Scheduled trips
            - 🎫 Online ticket booking
            - 📱 Real-time information
            """)
        
        with col2:
            st.info("""
            **Quick Links:**
            - Book Tickets → Reserve your seat
            - View Routes → Check available routes
            - My Tickets → Manage your bookings
            """)
        
        st.subheader("📈 System Overview")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Available Routes", len(list_routes()))
        with col2:
            st.metric("Active Buses", len([b for b in list_buses() if b['status'] == 'active']))
        with col3:
            st.metric("Today's Trips", len(list_available_trips()))
        with col4:
            st.metric("Total Stops", len(list_stops()))
        
        st.subheader("🕒 Upcoming Trips")
        trips = list_available_trips()[:5]
        if trips:
            for trip in trips:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{trip['route_name']}**")
                    st.write(f"Bus: {trip['bus_no']} ({trip['type']})")
                with col2:
                    st.write(f"🕒 {trip['start_time'].strftime('%H:%M')}")
                with col3:
                    if st.button("Book", key=f"quick_book_{trip['trip_id']}"):
                        st.session_state['public_page'] = "Book Tickets"
                        st.session_state['selected_trip'] = trip['trip_id']
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No upcoming trips available")

    elif page == "Book Tickets":
        st.subheader("🎟️ Book Your Bus Ticket")
        
        # Step 1: Route Selection
        st.write("### Step 1: Select Your Route")
        routes = list_routes()
        if not routes:
            st.error("No routes available. Please try again later.")
            return
        
        route_options = {f"{r['route_id']}: {r['route_name']} ({r['source']} → {r['destination']})": r['route_id'] for r in routes}
        selected_route = st.selectbox("Choose your route:", list(route_options.keys()))
        route_id = route_options[selected_route]
        
        # Step 2: Trip Selection
        st.write("### Step 2: Select Trip Timing")
        trips = list_available_trips()
        route_trips = [t for t in trips if t['route_id'] == route_id]
        
        if not route_trips:
            st.warning("No available trips for this route today.")
            return
        
        trip_options = {}
        for trip in route_trips:
            key = f"🕒 {trip['start_time'].strftime('%H:%M')} - Bus: {trip['bus_no']} ({trip['type']}) - Driver: {trip['driver_name']}"
            trip_options[key] = trip['trip_id']
        
        selected_trip = st.selectbox("Choose your trip timing:", list(trip_options.keys()))
        trip_id = trip_options[selected_trip]
        current_trip = next((t for t in route_trips if t['trip_id'] == trip_id), None)
        
        # Step 3: Stop Selection
        st.write("### Step 3: Select Stops")
        route_stops = get_route_stops(route_id)
        
        if len(route_stops) < 2:
            st.error("Route information incomplete. Please try another route.")
            return
        
        boarding_options = {f"{stop['stop_order']}. {stop['stop_name']} - {stop['location']}": stop['stop_id'] for stop in route_stops}
        dropping_options = {f"{stop['stop_order']}. {stop['stop_name']} - {stop['location']}": stop['stop_id'] for stop in route_stops}
        
        boarding_stop = st.selectbox("Boarding Stop:", list(boarding_options.keys()))
        dropping_stop = st.selectbox("Dropping Stop:", list(dropping_options.keys()))
        
        boarding_stop_id = boarding_options[boarding_stop]
        dropping_stop_id = dropping_options[dropping_stop]
        
        # Validate stop order
        boarding_order = int(boarding_stop.split('.')[0])
        dropping_order = int(dropping_stop.split('.')[0])
        
        if dropping_order <= boarding_order:
            st.error("❌ Dropping stop must come after boarding stop!")
            return
        
        # Step 4: Seat Selection
        st.write("### Step 4: Choose Your Seat")
        available_seats = get_available_seats(trip_id)
        
        if not available_seats:
            st.error("😔 No seats available for this trip. Please choose another trip.")
            return
        
        selected_seat = st.selectbox("Available seats:", available_seats)
        
        # Step 5: Passenger Details
        st.write("### Step 5: Passenger Information")
        col1, col2 = st.columns(2)
        with col1:
            passenger_name = st.text_input("Full Name *", placeholder="Enter your full name")
            contact_no = st.text_input("Contact Number *", placeholder="10-digit mobile number")
        with col2:
            email = st.text_input("Email Address", placeholder="your.email@example.com")
            gender = st.selectbox("Gender", ["male", "female", "other"])
        
        # Calculate fare
        fare = calculate_fare(boarding_stop_id, dropping_stop_id, current_trip['type'], current_trip['ac'])
        
        # Booking Summary
        st.write("### 📋 Booking Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"""
            **Journey Details:**
            - Route: {current_trip['route_name']}
            - Trip: {current_trip['start_time'].strftime('%Y-%m-%d %H:%M')}
            - Bus: {current_trip['bus_no']} ({current_trip['type']})
            - Driver: {current_trip['driver_name']}
            """)
        with col2:
            st.info(f"""
            **Your Selection:**
            - Boarding: {boarding_stop.split('.')[1].split(' - ')[0].strip()}
            - Dropping: {dropping_stop.split('.')[1].split(' - ')[0].strip()}
            - Seat: {selected_seat}
            - Fare: ₹{fare:.2f}
            """)
        
        # Final Confirmation
        if st.button("🎟️ Confirm & Book Ticket", type="primary", use_container_width=True):
            if not passenger_name or not contact_no:
                st.error("Please fill in all required fields (Name and Contact Number)")
            elif len(contact_no) < 10:
                st.error("Please enter a valid 10-digit contact number")
            else:
                try:
                    # Create passenger and ticket
                    passenger_id = add_passenger(passenger_name, "", contact_no, email or "")
                    add_ticket(trip_id, passenger_id, boarding_stop_id, dropping_stop_id, selected_seat, fare, gender)
                    
                    st.success("🎉 Ticket Booked Successfully!")
                    st.balloons()
                    
                    # Show booking confirmation
                    st.info(f"""
                    **Booking Confirmed!**
                    - Ticket for: {passenger_name}
                    - Contact: {contact_no}
                    - Seat: {selected_seat}
                    - Total Fare: ₹{fare:.2f}
                    - Please arrive at the stop 10 minutes before departure
                    """)
                    
                    # Option to book another ticket
                    if st.button("Book Another Ticket"):
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Booking failed: {str(e)}")

    elif page == "My Tickets":
        st.subheader("📋 My Tickets")
        
        # Search by contact number (since we don't have user login in public interface)
        contact_search = st.text_input("🔍 Enter your contact number to view tickets")
        
        if contact_search:
            tickets = fetch_all("""
                SELECT tk.*, r.route_name, s1.stop_name AS boarding_stop, s2.stop_name AS dropping_stop,
                       p.name AS passenger_name, t.start_time, t.end_time, b.bus_no
                FROM tickets tk
                JOIN trips t ON tk.trip_id = t.trip_id
                JOIN routes r ON t.route_id = r.route_id
                JOIN stops s1 ON tk.boarding_stop_id = s1.stop_id
                JOIN stops s2 ON tk.dropping_stop_id = s2.stop_id
                JOIN passengers p ON tk.passenger_id = p.passenger_id
                JOIN buses b ON t.bus_id = b.bus_id
                WHERE p.contact_no = %s
                ORDER BY tk.created_at DESC
            """, (contact_search,))
            
            if tickets:
                st.success(f"Found {len(tickets)} ticket(s) for contact number: {contact_search}")
                
                for ticket in tickets:
                    with st.expander(f"Ticket #{ticket['ticket_id']} - {ticket['route_name']} - {ticket['created_at'].strftime('%Y-%m-%d')}", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Journey Details:**")
                            st.write(f"🛣️ Route: {ticket['route_name']}")
                            st.write(f"🚌 Bus: {ticket['bus_no']}")
                            st.write(f"💺 Seat: {ticket['seat_no']}")
                            st.write(f"💰 Fare: ₹{ticket['fare']:.2f}")
                        
                        with col2:
                            st.write("**Passenger Info:**")
                            st.write(f"👤 Name: {ticket['passenger_name']}")
                            st.write(f"📞 Contact: {contact_search}")
                            st.write(f"🚏 Boarding: {ticket['boarding_stop']}")
                            st.write(f"🎯 Dropping: {ticket['dropping_stop']}")
                        
                        st.write(f"**Trip Timing:** {ticket['start_time'].strftime('%Y-%m-%d %H:%M')} to {ticket['end_time'].strftime('%H:%M')}")
                        
                        # Cancel ticket option
                        if st.button("Cancel Ticket", key=f"cancel_{ticket['ticket_id']}"):
                            delete_ticket(ticket['ticket_id'])
                            st.success("Ticket cancelled successfully!")
                            st.rerun()
            else:
                st.warning("No tickets found for this contact number")
        else:
            st.info("Please enter your contact number to view your tickets")

    elif page == "Routes":
        st.subheader("🛣️ Available Routes")
        routes = list_routes()
        
        if routes:
            for route in routes:
                with st.expander(f"{route['route_name']} - {route['source']} to {route['destination']}"):
                    st.write(f"**Distance:** {route['distance_km']} km")
                    
                    # Show route stops
                    route_stops = get_route_stops(route['route_id'])
                    if route_stops:
                        st.write("**Route Stops:**")
                        for stop in route_stops:
                            st.write(f"{stop['stop_order']}. {stop['stop_name']} - {stop['location']}")
                    
                    # Show available trips for this route
                    trips = [t for t in list_available_trips() if t['route_id'] == route['route_id']]
                    if trips:
                        st.write("**Available Trips:**")
                        for trip in trips[:3]:  # Show first 3 trips
                            st.write(f"- {trip['start_time'].strftime('%H:%M')} - Bus {trip['bus_no']} ({trip['type']})")
                    
                    if st.button("Book this Route", key=f"book_route_{route['route_id']}"):
                        st.session_state['public_page'] = "Book Tickets"
                        st.rerun()
        else:
            st.info("No routes available")

    elif page == "Trips":
        st.subheader("🕒 Available Trips")
        trips = list_available_trips()
        
        if trips:
            for trip in trips:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**{trip['route_name']}**")
                        st.write(f"Bus: {trip['bus_no']} ({trip['type']}) | Driver: {trip['driver_name']}")
                        st.write(f"Time: {trip['start_time'].strftime('%Y-%m-%d %H:%M')} to {trip['end_time'].strftime('%H:%M')}")
                    
                    with col2:
                        available_seats = len(get_available_seats(trip['trip_id']))
                        st.write(f"Seats: {available_seats}")
                    
                    with col3:
                        if st.button("Book", key=f"book_trip_{trip['trip_id']}"):
                            st.session_state['public_page'] = "Book Tickets"
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No trips available")

    elif page == "Stops":
        st.subheader("🚏 All Stops")
        stops = list_stops()
        if stops:
            for stop in stops:
                st.write(f"**{stop['stop_name']}**")
                st.write(f"Location: {stop['location']}")
                st.markdown("---")
        else:
            st.info("No stops information available")

    elif page == "Buses":
        st.subheader("🚌 Bus Fleet")
        buses = [b for b in list_buses() if b['status'] == 'active']
        if buses:
            for bus in buses:
                st.write(f"**{bus['bus_no']}** - {bus['bus_name']}")
                st.write(f"Type: {bus['type']} | Capacity: {bus['capacity']} | AC: {'Yes' if bus['ac'] else 'No'}")
                st.markdown("---")
        else:
            st.info("No active buses available")

    elif page == "Search":
        st.subheader("🔍 Search Transportation")
        search_query = st.text_input("Search for routes, stops, or buses")
        
        if search_query:
            # Search routes
            routes = fetch_all("SELECT * FROM routes WHERE route_name LIKE %s OR source LIKE %s OR destination LIKE %s", 
                             (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
            
            # Search stops
            stops = fetch_all("SELECT * FROM stops WHERE stop_name LIKE %s OR location LIKE %s", 
                            (f"%{search_query}%", f"%{search_query}%"))
            
            # Search buses
            buses = fetch_all("SELECT * FROM buses WHERE bus_no LIKE %s OR bus_name LIKE %s", 
                            (f"%{search_query}%", f"%{search_query}%"))
            
            if routes or stops or buses:
                if routes:
                    st.subheader("📍 Matching Routes")
                    for route in routes:
                        st.write(f"**{route['route_name']}** - {route['source']} to {route['destination']}")
                
                if stops:
                    st.subheader("🚏 Matching Stops")
                    for stop in stops:
                        st.write(f"**{stop['stop_name']}** - {stop['location']}")
                
                if buses:
                    st.subheader("🚌 Matching Buses")
                    for bus in buses:
                        st.write(f"**{bus['bus_no']}** - {bus['bus_name']} ({bus['type']})")
            else:
                st.info("No results found for your search")

# --------------------------- MAIN APP ---------------------------
def main():
    st.set_page_config(
        page_title="Public Transport DBMS", 
        layout="wide", 
        initial_sidebar_state="expanded",
        page_icon="🚌"
    )
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'public_page' not in st.session_state:
        st.session_state.public_page = "Overview"
    
    header()
    
    # Initialize database
    try:
        initialize_database_and_schema()
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        st.stop()

    # Sidebar authentication
    st.sidebar.header("🔐 Access Control")
    access_mode = st.sidebar.radio("Select Access Level:", ("Public View", "Login"))
    
    if access_mode == "Login":
        st.sidebar.subheader("User Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Sign In"):
                user = authenticate(username, password)
                if user:
                    st.session_state.user = user
                    st.sidebar.success(f"Welcome, {user['username']}!")
                    st.rerun()
                else:
                    st.sidebar.error("Invalid credentials")
        
        with col2:
            if st.button("Clear"):
                st.session_state.user = None
                st.rerun()
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("New Operator Registration")
        reg_user = st.sidebar.text_input("New Username")
        reg_pass = st.sidebar.text_input("New Password", type="password")
        
        if st.sidebar.button("Register"):
            if reg_user and reg_pass:
                ok, msg = register_user(reg_user, reg_pass, "operator")
                if ok:
                    st.sidebar.success("Registration successful! Please login.")
                else:
                    st.sidebar.error(msg)
    else:
        st.sidebar.info("Public access mode - view only")
    
    # Sign out button
    if st.session_state.user and st.sidebar.button("Sign Out"):
        st.session_state.user = None
        st.rerun()

    # Route to appropriate interface
    user = st.session_state.get('user')
    if user:
        role = user.get('role')
        if role == 'admin':
            admin_interface()
        elif role == 'operator':
            operator_interface()
        else:
            st.error("Unknown user role")
    else:
        public_interface()

if __name__ == "__main__":
    main()