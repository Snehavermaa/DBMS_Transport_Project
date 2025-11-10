import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="tp_user",
        password="tp_password",
        database="transport_db"
    )
