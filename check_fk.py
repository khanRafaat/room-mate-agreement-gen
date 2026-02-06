"""
Check all FK constraints on base_agreement table
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

def check_constraints():
    with engine.connect() as conn:
        # Get all FK constraints
        result = conn.execute(text("""
            SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_NAME = 'base_agreement' 
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """))
        
        constraints = result.fetchall()
        print("All FK constraints on base_agreement:")
        for row in constraints:
            print(f"  - {row[0]}: {row[1]} -> {row[2]}.{row[3]}")
        
        if not constraints:
            print("  No FK constraints found!")
        
        # Also check the column definition
        result2 = conn.execute(text("SHOW CREATE TABLE base_agreement"))
        create_stmt = result2.fetchone()
        print("\nTable definition:")
        print(create_stmt[1] if create_stmt else "Could not get table definition")

if __name__ == "__main__":
    check_constraints()
