"""
Quick script to drop the FK constraint on base_agreement.city_id
Run this from the room-mate-agreement-gen directory
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

def drop_fk_constraint():
    with engine.connect() as conn:
        # First, get the FK constraint name
        result = conn.execute(text("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.TABLE_CONSTRAINTS 
            WHERE TABLE_NAME = 'base_agreement' 
            AND CONSTRAINT_TYPE = 'FOREIGN KEY'
            AND CONSTRAINT_NAME LIKE '%city%' OR CONSTRAINT_NAME LIKE '%ibfk%'
        """))
        
        constraints = result.fetchall()
        print(f"Found FK constraints: {constraints}")
        
        for row in constraints:
            constraint_name = row[0]
            print(f"Dropping constraint: {constraint_name}")
            try:
                conn.execute(text(f"ALTER TABLE base_agreement DROP FOREIGN KEY {constraint_name}"))
                conn.commit()
                print(f"Successfully dropped: {constraint_name}")
            except Exception as e:
                print(f"Error dropping {constraint_name}: {e}")
        
        print("Done! FK constraint should be removed.")

if __name__ == "__main__":
    drop_fk_constraint()
