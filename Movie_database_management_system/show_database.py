import sqlite3
from tabulate import tabulate

def display_database_tables(db_path='instance/movies.db'):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "="*50)
    print("DATABASE TABLES AND CONTENTS")
    print("="*50 + "\n")

    # Get all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        
        # Get table structure (columns)
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Get all data from the table
        cursor.execute(f"SELECT * FROM {table_name};")
        data = cursor.fetchall()
        
        # Display table info
        print(f"\nTABLE: {table_name.upper()}")
        print("-" * (len(table_name) + 8))
        print(f"Columns: {', '.join(column_names)}\n")
        
        if data:
            # Print data in a nice table format
            print(tabulate(data, headers=column_names, tablefmt="grid"))
        else:
            print("No data found in this table.")
        
        print("\n" + "-"*50)

    conn.close()

if __name__ == "__main__":
    display_database_tables()