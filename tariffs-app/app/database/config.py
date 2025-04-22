import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import time
import datetime

# Load environment variables from .env file if present
load_dotenv()

# Get database config from environment variables or use defaults
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "tariffs_exemptions")

# Set to True to enable query logging
QUERY_LOGGING = True

def log_query(query, params=None, time_taken=None, rows_affected=None):
    """Log query details to terminal"""
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
    """
    Create a database connection to MySQL
    Returns connection object or None on error
    """
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
    """Close the database connection"""
    if connection and connection.is_connected():
        connection.close()

def ensure_activity_log_table_exists():
    """Create activity_log table if it doesn't exist"""
    connection = get_db_connection()
    if not connection:
        print("Error: Could not connect to database to create activity_log table")
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        
        # Create activity_log table if it doesn't exist
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
    """
    Execute a query on the database
    
    Args:
        query (str): SQL query to execute
        params (tuple, optional): Parameters for the SQL query
        fetch (bool): Whether to fetch results or not (for INSERT/UPDATE/DELETE)
        
    Returns:
        list of dicts if fetch=True, dict with affected_rows if fetch=False
    """
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
                # Explicitly get the last insert ID if this was an insert
                last_id = None
                if query.lower().strip().startswith("insert"):
                    last_id = cursor.lastrowid
                    # If lastrowid is not available, try to get it with a separate query
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
    """
    Helper function to insert a record into a table
    
    Args:
        table (str): Table name
        data (dict): Dictionary with column:value pairs
        returning_id (bool): Whether to return the inserted ID
        
    Returns:
        int: ID of inserted record if successful and returning_id=True
        bool: True if successful and returning_id=False
    """
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