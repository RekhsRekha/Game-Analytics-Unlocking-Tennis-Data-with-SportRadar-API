import pandas as pd
from sqlalchemy import create_engine, text

# SQL Server Connection Configuration
# Replace 'DESKTOP-XXXXXX' with your actual SQL Server Instance Name (e.g. localhost, SQLEXPRESS, DESKTOP-TQ1Q8G3)
SERVER_NAME = "localhost" 
DATABASE_NAME = "GameAnalyticsDB"

# Create SQLAlchemy Engine using pyodbc Windows Authentication
connection_string = f"mssql+pyodbc://@{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
engine = create_engine(connection_string, fast_executemany=True)

def load_data():
    print("Starting Database Ingestion into SQL Server...\n")
    
    # Order matters due to Foreign Keys!
    tables_to_load = [
        ("categories.csv", "Categories"),
        ("competitions.csv", "Competitions"),
        ("complexes.csv", "Complexes"),
        ("venues.csv", "Venues"),
        ("competitors.csv", "Competitors"),
        ("rankings.csv", "Competitor_Rankings")
    ]

    with engine.connect() as conn:
        for csv_file, table_name in tables_to_load:
            print(f"Loading '{csv_file}' into SQL table '{table_name}'...")
            
            df = pd.read_csv(csv_file)
            
            # Clean empty or null values
            df = df.where(pd.notnull(df), None)

            # Insert into SQL Server
            # Competitor_Rankings uses identity column for rank_id, so we don't pass rank_id
            df.to_sql(
                name=table_name, 
                con=engine, 
                if_exists="append", 
                index=False
            )
            
            # Verify count
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f" Successfully loaded {len(df)} rows. Total table rows: {count}\n")

    print("Data ingestion complete! All 6 tables populated successfully.")

if __name__ == "__main__":
    load_data()