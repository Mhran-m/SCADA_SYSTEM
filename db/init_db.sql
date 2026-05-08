CREATE DATABASE ScadaDB;
GO
USE ScadaDB;
GO

CREATE TABLE Tag (
    TagID INT IDENTITY PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(255),
    EngUnit NVARCHAR(50),
    DataType NVARCHAR(50) NOT NULL,
    SourceType NVARCHAR(50) NOT NULL,
    OPCNodeID NVARCHAR(255),
    ScanRateMs INT,
    IsActive BIT NOT NULL DEFAULT 1
);

CREATE TABLE Sensor (
    SensorID INT IDENTITY PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL,
    Description NVARCHAR(255),
    Location NVARCHAR(100),
    TagID INT NOT NULL FOREIGN KEY REFERENCES Tag(TagID)
);

CREATE TABLE AlarmDefinition (
    AlarmDefID INT IDENTITY PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL,
    Description NVARCHAR(255),
    TagID INT NOT NULL FOREIGN KEY REFERENCES Tag(TagID),
    Type NVARCHAR(20) NOT NULL,   -- 'Hi', 'Lo', etc.
    Setpoint FLOAT NOT NULL,
    Hysteresis FLOAT NOT NULL DEFAULT 0,
    Priority INT NOT NULL,
    Enabled BIT NOT NULL DEFAULT 1
);

CREATE TABLE TagValueLog (
    LogID BIGINT IDENTITY PRIMARY KEY,
    TagID INT NOT NULL FOREIGN KEY REFERENCES Tag(TagID),
    [Timestamp] DATETIME2 NOT NULL,
    Value FLOAT NOT NULL,
    Quality NVARCHAR(20),
    Source NVARCHAR(50)
);

CREATE TABLE UserAccount (
    UserID INT IDENTITY PRIMARY KEY,
    Username NVARCHAR(100) NOT NULL UNIQUE,
    PasswordHash VARBINARY(256) NOT NULL,
    Role NVARCHAR(50) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1
);

CREATE TABLE AlarmEvent (
    AlarmEventID BIGINT IDENTITY PRIMARY KEY,
    AlarmDefID INT NOT NULL FOREIGN KEY REFERENCES AlarmDefinition(AlarmDefID),
    TagID INT NOT NULL FOREIGN KEY REFERENCES Tag(TagID),
    EventTime DATETIME2 NOT NULL,
    State NVARCHAR(50) NOT NULL,  -- 'ActiveUnack', 'ActiveAck', etc.
    ValueAtEvent FLOAT,
    AcknowledgedBy INT NULL FOREIGN KEY REFERENCES UserAccount(UserID),
    AcknowledgedTime DATETIME2 NULL,
    Comment NVARCHAR(255) NULL
);
GO

CREATE PROCEDURE usp_LogTagValue
    @TagID INT,
    @Timestamp DATETIME2,
    @Value FLOAT,
    @Quality NVARCHAR(20),
    @Source NVARCHAR(50)
AS
BEGIN
    INSERT INTO TagValueLog (TagID, [Timestamp], Value, Quality, Source)
    VALUES (@TagID, @Timestamp, @Value, @Quality, @Source);
END;
GO
