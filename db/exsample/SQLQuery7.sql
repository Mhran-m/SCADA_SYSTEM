USE ScadaDB;
GO

UPDATE AlarmDefinition
SET Enabled = 0
WHERE Name = 'HighTemp';