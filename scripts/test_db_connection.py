import os
from dotenv import load_dotenv
import psycopg2
import urllib.parse

# Load environment variables from .env file
load_dotenv()

def get_connection_string():
    """Get PostgreSQL connection string from environment variables"""
    try:
        dbhost = os.getenv('DBHOST')
        dbname = os.getenv('DBNAME')
        dbuser = urllib.parse.quote(os.getenv('DBUSER'))
        password = os.getenv('DBPASSWORD')
        sslmode = os.getenv('SSLMODE', 'require')  # Default to 'require' for Azure

        # Check if all required variables are set
        if not all([dbhost, dbname, dbuser, password]):
            missing = [var for var, val in {
                'DBHOST': dbhost,
                'DBNAME': dbname,
                'DBUSER': dbuser,
                'DBPASSWORD': password
            }.items() if not val]
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return f"host={dbhost} dbname={dbname} user={dbuser} password={password} sslmode={sslmode}"
    except Exception as e:
        print(f"Error constructing connection string: {e}")
        return None

def test_connection():
    """Test the PostgreSQL connection"""
    print("Attempting to connect to database...")
    conn_string = get_connection_string()
    if not conn_string:
        return False
    
    print(f"Using connection string: {conn_string}")
    
    try:
        # Create connection with SSL required for Azure
        
        # Attempt to connect
        conn = psycopg2.connect(conn_string)
        
        # Get cursor and execute test query
        cur = conn.cursor()
        cur.execute('SELECT version();')
        ver = cur.fetchone()
        print("\nSuccessfully connected to PostgreSQL!")
        print(f"PostgreSQL version: {ver[0]}")
        
        # List available tables
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cur.fetchall()
        print("\nAvailable tables:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\nError connecting to PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    print("Testing connection to Azure PostgreSQL...")
    test_connection()