# 🚌 Public Transport Management System

A **DBMS-based college project** that manages and organizes public transport operations such as buses, routes, schedules, drivers, and passenger bookings. This project demonstrates the use of **MySQL** with a properly designed schema and backend integration.

---

## 📌 Features

* 👤 **User Management** – Admin & Passenger accounts
* 🚌 **Bus Management** – Add, update, and manage buses
* 📍 **Route & Schedule Management** – Define routes, stops, and timings
* 👨‍✈️ **Driver Management** – Assign drivers to buses
* 🎫 **Ticket Booking System** – Passengers can search and book tickets
* 🗄️ **Database Integration** – Normalized MySQL schema for efficient data handling

---

## 🗄️ Database Schema

### Entities

* **Users** – Passenger/Admin details
* **Buses** – Bus information (bus_no, capacity, type)
* **Routes** – Source, destination, stops, and distance
* **Schedules** – Timings of buses on specific routes
* **Drivers** – Driver details (name, license_no, contact)
* **Bookings** – Ticket booking records (user_id, bus_id, seat_no, date)

### ER Diagram

```
Users ---< Bookings >--- Buses ---< Schedules >--- Routes  
Drivers ---< Assigned_To >--- Buses
```

---

## ⚙️ Tech Stack

* **Frontend**: HTML, CSS
* **Backend**: Python
* **Database**: MySQL

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Snehavermaa/DBMS_Transport_Project.git
cd DBMS_Transport_Project
```

### 2. Setup Database

* Open MySQL Workbench / CLI
* Create a new database:

```sql
CREATE DATABASE transport_db;
```

* Import the provided `schema.sql` file:

```sql
USE transport_db;
SOURCE schema.sql;
```

### 3. Run the Backend Code

* Configure your database connection (username, password, db_name) inside the backend code
* Start the server

### 4. Access the System

* Open the frontend in your browser OR test via API endpoints

---

## 📂 Project Structure

```
📦 public-transport-management  
 ┣ 📂 src/              # Backend source code  
 ┣ 📂 frontend/         # Web pages (if applicable)  
 ┣ 📂 sql/              # Database schema & queries  
 ┣ 📜 schema.sql        # SQL schema file  
 ┣ 📜 README.md         # Documentation  
```

---

## 📝 Future Enhancements

* Online payment integration for ticket booking
* Real-time bus tracking
* Role-based authentication (Admin, Driver, Passenger)
* Mobile app interface

---

## 👨‍💻 Authors

This project was created as part of a **DBMS College Project** by:

*SNEHA VERMA
*SWATHI D

---

✨ Feel free to **fork** this repo and build upon it!

---

👉 Do you want me to also **write the `schema.sql` file** (with table creation queries for Users, Buses, Routes, etc.) so you can directly include it in your repo?
