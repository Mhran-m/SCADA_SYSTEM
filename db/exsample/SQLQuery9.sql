USE ScadaDB;
GO

INSERT INTO AlarmDefinition (Name, Description, TagID, Type, Setpoint, Hysteresis, Priority, Enabled)
SELECT
    'LowTemp',
    'Low temperature alarm on Air Heater PV',
    TagID,
    'Lo',
    35.0,       -- low alarm at 35 °C
    0.5,        -- hysteresis
    2,          -- lower priority
    1
FROM Tag
WHERE Name = 'AirHeater.PV';
