import psycopg2
from psycopg2 import OperationalError

# Define a custom exception for better error handling context
class ConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass

def connect_to_db(host, port, dbname, user, password):
    """
    Establishes a connection to the PostgreSQL database.

    Args:
        host (str): Database host address.
        port (str): Database port number.
        dbname (str): Database name.
        user (str): Username for authentication.
        password (str): Password for authentication.

    Returns:
        psycopg2.connection: The connection object if successful.

    Raises:
        ConnectionError: If the connection fails for any reason.
    """
    conn = None
    try:
        print(f"Attempting to connect: dbname='{dbname}' user='{user}' host='{host}' port='{port}'") # Debug print
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=5 # Add a timeout (in seconds)
        )
        print("Connection successful!") # Debug print
        return conn
    except OperationalError as e:
        # Catch specific psycopg2 connection errors
        print(f"Connection failed: {e}") # Debug print
        # Raise a more specific custom error
        raise ConnectionError(f"Could not connect to database.\nDetails: {e}") from e
    except Exception as e:
        # Catch any other unexpected errors during connection attempt
        print(f"An unexpected error occurred during connection: {e}") # Debug print
        if conn:
            conn.close() # Ensure connection is closed if partially opened
        raise ConnectionError(f"An unexpected error occurred.\nDetails: {e}") from e

# Example of how to use (for testing purposes, not typically run directly)
if __name__ == '__main__':
    # --- IMPORTANT ---
    # Replace with actual test database details
    # DO NOT COMMIT ACTUAL CREDENTIALS
    test_details = {
        "host": "localhost",
        "port": "5432",
        "dbname": "your_test_db",
        "user": "your_test_user",
        "password": "your_test_password"
    }

    try:
        connection = connect_to_db(**test_details)
        if connection:
            print("\n--- Test Connection Successful ---")
            print(f"Connected to PostgreSQL server version: {connection.server_version}")
            # You can perform a simple query here if needed
            # cur = connection.cursor()
            # cur.execute("SELECT version();")
            # print(cur.fetchone())
            # cur.close()
            connection.close()
            print("--- Test Connection Closed ---")
    except ConnectionError as err:
        print(f"\n--- Test Connection Failed ---")
        print(err)
    except ImportError:
        print("Error: psycopg2 library not found. Please install it: pip install psycopg2-binary")

