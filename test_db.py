import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="tp_user",
        password="tp_password",
        database="transport_db"
    )
    print("✅ Connection successful!")
    conn.close()
except mysql.connector.Error as err:
    print("❌ Error:", err)
