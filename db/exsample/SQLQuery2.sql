USE ScadaDB;
GO

UPDATE AlarmDefinition
SET Enabled = 1
WHERE Name = 'HighTemp';