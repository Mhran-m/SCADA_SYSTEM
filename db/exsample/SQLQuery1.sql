USE ScadaDB;
GO

SELECT TOP 50 * 
FROM TagValueLog
ORDER BY [Timestamp] DESC;	