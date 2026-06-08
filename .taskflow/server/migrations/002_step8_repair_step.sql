-- Migration 002: set repair_step_number for step 8
-- When step 8 (Run tests) fails, the builder (step 7) needs to fix the code
-- before the tester can re-run. This column was already in the schema but
-- never populated. Setting it to 7 makes the intent explicit.

UPDATE pipeline_steps SET repair_step_number = 7 WHERE step_number = 8;