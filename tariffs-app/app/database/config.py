import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import time
import datetime

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "tariffs_exemptions")

QUERY_LOGGING = True

def log_query(query, params=None, time_taken=None, rows_affected=None):
    if not QUERY_LOGGING:
        return
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] SQL QUERY:")
    print("-" * 80)
    print(f"QUERY: {query}")
    
    if params:
        print(f"PARAMS: {params}")
    
    if time_taken is not None:
        print(f"TIME: {time_taken:.4f} seconds")
    
    if rows_affected is not None:
        if isinstance(rows_affected, int):
            print(f"ROWS AFFECTED: {rows_affected}")
        elif isinstance(rows_affected, list):
            print(f"ROWS RETURNED: {len(rows_affected)}")
    
    print("-" * 80)

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD,
            database=DB_NAME
        )
        
        if connection.is_connected():
            if QUERY_LOGGING:
                db_info = connection.get_server_info()
                print(f"Connected to MySQL Server version {db_info}")
            return connection
            
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def close_connection(connection):
    if connection and connection.is_connected():
        connection.close()

def ensure_activity_log_table_exists():
    connection = get_db_connection()
    if not connection:
        print("Error: Could not connect to database to create activity_log table")
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS activity_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            activity_type VARCHAR(50) NOT NULL,
            description TEXT,
            entity_id INT,
            entity_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_table_query)
        connection.commit()
        print("Activity log table created or already exists.")
        return True
        
    except Error as e:
        print(f"Error creating activity_log table: {e}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        close_connection(connection)

def execute_query(query, params=None, fetch=True):
    connection = get_db_connection()
    cursor = None
    result = None
    start_time = time.time()
    
    try:
        if connection:
            cursor = connection.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                result = cursor.fetchall()
                log_query(query, params, time.time() - start_time, result)
            else:
                connection.commit()
                last_id = None
                if query.lower().strip().startswith("insert"):
                    last_id = cursor.lastrowid
                    if last_id is None or last_id == 0:
                        try:
                            cursor.execute("SELECT LAST_INSERT_ID()")
                            last_id_result = cursor.fetchone()
                            if last_id_result and "LAST_INSERT_ID()" in last_id_result:
                                last_id = last_id_result["LAST_INSERT_ID()"]
                        except Error as e:
                            print(f"Error getting last insert ID: {e}")
                
                result = {"affected_rows": cursor.rowcount, "last_insert_id": last_id}
                log_query(query, params, time.time() - start_time, cursor.rowcount)
                
    except Error as e:
        print(f"Error executing query: {e}")
        print(f"Query: {query}")
        if params:
            print(f"Params: {params}")
            
    finally:
        if cursor:
            cursor.close()
        close_connection(connection)
        
    return result

def insert_record(table, data, returning_id=True):
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    values = tuple(data.values())
    
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    result = execute_query(query, values, fetch=False)
    
    if result and result["affected_rows"] > 0:
        if returning_id:
            return result["last_insert_id"]
        return True
    
    return False