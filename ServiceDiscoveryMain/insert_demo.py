import pandas as pd
from sqlalchemy import create_engine, text
import urllib

def insert_data(file):
    df = pd.read_csv(file)

    # SQL Server connection
    params = urllib.parse.quote_plus(
        'DRIVER={ODBC Driver 18 for SQL Server};'
        'SERVER=172.28.3.181;'
        'DATABASE=GPONServiceDiscovery;'
        'UID=ossuser;'
        'PWD=1q2w!Q@W;'
        'TrustServerCertificate=yes;'
    )
    engine = create_engine(f'mssql+pyodbc:///?odbc_connect={params}')

    # ✅ Execute cleanup query before inserting
    with engine.begin() as conn:

        # Insert into SQL
        df.to_sql(name='IPMPLSServices', con=conn, schema='dbo', if_exists='append', index=False)
        print("✅ Data inserted into [dbo].[GPONServices] successfully.")

file = 'IPReports\IPMPLSServiceDiscovery.csv'
insert_data(file)