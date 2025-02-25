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