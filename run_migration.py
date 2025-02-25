#!/usr/bin/env python3
"""
Script to run the cascade delete migration on the Supabase database.
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
    print("Please check your .env file or set them manually.")
    exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL migration to add ON DELETE CASCADE
migration_sql = """
-- First, drop the existing foreign key constraint
ALTER TABLE run_results DROP CONSTRAINT IF EXISTS run_results_run_id_fkey;

-- Then, add it back with ON DELETE CASCADE
ALTER TABLE run_results 
  ADD CONSTRAINT run_results_run_id_fkey 
  FOREIGN KEY (run_id) 
  REFERENCES test_runs(id) 
  ON DELETE CASCADE;

-- Log the change
COMMENT ON CONSTRAINT run_results_run_id_fkey ON run_results IS 'Automatically deletes run results when a test run is deleted';
"""

def run_migration():
    """Run the migration to add ON DELETE CASCADE to the run_results table."""
    try:
        # Execute the SQL migration
        supabase.table("run_results").rpc("query", {"query_text": migration_sql}).execute()
        print("Migration successful! ON DELETE CASCADE has been added to run_results_run_id_fkey.")
    except Exception as e:
        print(f"Error running migration: {str(e)}")
        print("\nYou may need to run this SQL directly in the Supabase SQL Editor:")
        print(migration_sql)

if __name__ == "__main__":
    print("Running migration to add ON DELETE CASCADE to run_results_run_id_fkey...")
    run_migration() 