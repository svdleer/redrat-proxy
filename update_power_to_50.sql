-- Update existing database records to use power=50 instead of power=100
-- Run this against your redrat database

-- Update commands table
UPDATE commands SET power = 50 WHERE power = 100;

-- Update sequences table  
UPDATE sequences SET power = 50 WHERE power = 100;

-- Update sequence_commands table
UPDATE sequence_commands SET power = 50 WHERE power = 100;

-- Show updated counts
SELECT 'commands' as table_name, COUNT(*) as records_with_power_50 FROM commands WHERE power = 50
UNION ALL
SELECT 'sequences' as table_name, COUNT(*) as records_with_power_50 FROM sequences WHERE power = 50  
UNION ALL
SELECT 'sequence_commands' as table_name, COUNT(*) as records_with_power_50 FROM sequence_commands WHERE power = 50;

-- Show any remaining records with power=100
SELECT 'Remaining power=100 in commands' as check_name, COUNT(*) as count FROM commands WHERE power = 100
UNION ALL
SELECT 'Remaining power=100 in sequences' as check_name, COUNT(*) as count FROM sequences WHERE power = 100
UNION ALL  
SELECT 'Remaining power=100 in sequence_commands' as check_name, COUNT(*) as count FROM sequence_commands WHERE power = 100;
