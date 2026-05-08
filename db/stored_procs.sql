USE ScadaDB;
GO

-- 1) Stored procedure for logging tag values
IF OBJECT_ID('dbo.usp_LogTagValue', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_LogTagValue;
GO

CREATE PROCEDURE dbo.usp_LogTagValue
    @TagID INT,
    @Timestamp DATETIME2,
    @Value FLOAT,
    @Quality NVARCHAR(20),
    @Source NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO TagValueLog (TagID, [Timestamp], Value, Quality, Source)
    VALUES (@TagID, @Timestamp, @Value, @Quality, @Source);
END;
GO

-- 2) Optional helper: get latest value for a tag
IF OBJECT_ID('dbo.usp_GetLatestTagValue', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_GetLatestTagValue;
GO

CREATE PROCEDURE dbo.usp_GetLatestTagValue
    @TagID INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP 1
        LogID,
        TagID,
        [Timestamp],
        Value,
        Quality,
        Source
    FROM TagValueLog
    WHERE TagID = @TagID
    ORDER BY [Timestamp] DESC;
END;
GO
