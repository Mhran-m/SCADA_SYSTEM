USE ScadaDB;
GO

UPDATE AlarmDefinition
SET Setpoint = 40.5
WHERE Name = 'HighTemp';