USE ScadaDB;
GO

INSERT INTO AlarmDefinition (Name, Description, TagID, Type, Setpoint, Hysteresis, Priority, Enabled)
SELECT
    'VeryHighTemp',
    'Very high temperature alarm on Air Heater PV',
    TagID,
    'Hi',
    70.0,       -- very high alarm
    1.0,
    1,          -- high priority
    1
FROM Tag
WHERE Name = 'AirHeater.PV';
