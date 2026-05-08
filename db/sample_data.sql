USE ScadaDB;
GO

-- 1) Insert Tags for Air Heater PV, SP, CO
INSERT INTO Tag (Name, Description, EngUnit, DataType, SourceType, OPCNodeID, ScanRateMs)
VALUES
('AirHeater.PV', 'Air Heater Temperature', 'degC', 'Float', 'OPC', 'ns=2;s=AirHeater.PV', 1000),
('AirHeater.SP', 'Air Heater Setpoint',    'degC', 'Float', 'OPC', 'ns=2;s=AirHeater.SP', 1000),
('AirHeater.CO', 'Air Heater Control Out', '%',    'Float', 'OPC', 'ns=2;s=AirHeater.CO', 1000);
GO

-- 2) Insert a high alarm on PV (Hi alarm at 60 °C with 1 °C hysteresis)
INSERT INTO AlarmDefinition (Name, Description, TagID, Type, Setpoint, Hysteresis, Priority)
SELECT
    'HighTemp',
    'High temperature alarm on Air Heater PV',
    TagID,
    'Hi',
    60.0,
    1.0,
    1
FROM Tag
WHERE Name = 'AirHeater.PV';
GO

-- 3) Insert a dummy user (PasswordHash is placeholder, you will overwrite with create_user.py)
INSERT INTO UserAccount (Username, PasswordHash, Role, IsActive)
VALUES ('operator1', 0x00, 'Operator', 1);
GO

-- Optional: verify inserts
SELECT * FROM Tag;
SELECT * FROM AlarmDefinition;
SELECT * FROM UserAccount;
GO
