USE ScadaDB;
GO

UPDATE AlarmDefinition
SET Hysteresis = 2.0
WHERE Name = 'HighTemp';