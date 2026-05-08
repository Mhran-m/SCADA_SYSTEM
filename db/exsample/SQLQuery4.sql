USE ScadaDB;
GO

UPDATE AlarmDefinition
SET Setpoint = 40.0, Hysteresis = 0.2
WHERE Name = 'HighTemp';