# alarm_module.py
import time
from datetime import datetime, timezone
from common.common_db import get_connection

# For simplicity, we assume:
# - One high alarm on PV (AlarmDefID=1)
# - TagID for PV = 1
ALARMDEF_ID = 1
TAG_ID_PV = 1

def get_latest_value(cursor, tag_id):
    cursor.execute("""
        SELECT TOP 1 Value, [Timestamp]
        FROM TagValueLog
        WHERE TagID = ?
        ORDER BY [Timestamp] DESC
    """, tag_id)
    row = cursor.fetchone()
    if row:
        return float(row[0]), row[1]
    return None, None

def get_alarm_definition(cursor, alarmdef_id):
    cursor.execute("""
        SELECT AlarmDefID, TagID, Type, Setpoint, Hysteresis, Enabled
        FROM AlarmDefinition
        WHERE AlarmDefID = ?
    """, alarmdef_id)
    return cursor.fetchone()

def insert_alarm_event(cursor, alarmdef_id, tag_id, state, value):
    now = datetime.now(timezone.utc)
    cursor.execute("""
        INSERT INTO AlarmEvent (AlarmDefID, TagID, EventTime, State, ValueAtEvent)
        VALUES (?, ?, ?, ?, ?)
    """, alarmdef_id, tag_id, now, state, value)

def alarm_logic_loop(stop_flag):
    conn = get_connection()
    cursor = conn.cursor()

    alarm_active = False

    while not stop_flag["stop"]:
        ad = get_alarm_definition(cursor, ALARMDEF_ID)
        if not ad:
            print("No AlarmDefinition found, waiting...")
            time.sleep(2)
            continue

        _, tag_id, atype, setpoint, hysteresis, enabled = ad
        if not enabled:
            time.sleep(2)
            continue

        value, ts = get_latest_value(cursor, TAG_ID_PV)
        if value is None:
            print("No PV data yet...")
            time.sleep(2)
            continue

        # Only implement 'Hi' type in this prototype
        if atype == "Hi":
            if not alarm_active and value > setpoint:
                alarm_active = True
                print(f"[ALARM] PV {value:.2f} exceeded setpoint {setpoint:.2f}")
                insert_alarm_event(cursor, ALARMDEF_ID, TAG_ID_PV, "ActiveUnack", value)
                conn.commit()
            elif alarm_active and value < setpoint - hysteresis:
                alarm_active = False
                print(f"[ALARM CLEAR] PV {value:.2f} returned below reset level")
                insert_alarm_event(cursor, ALARMDEF_ID, TAG_ID_PV, "ReturnToNormalUnack", value)
                conn.commit()

        time.sleep(1)

    conn.close()

def list_active_alarms():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AlarmEventID, EventTime, State, ValueAtEvent
        FROM AlarmEvent
        WHERE State LIKE 'Active%'
        ORDER BY EventTime DESC
    """)
    rows = cursor.fetchall()
    for r in rows:
        print(f"ID={r[0]} Time={r[1]} State={r[2]} Value={r[3]:.2f}")
    conn.close()

def acknowledge_alarm(alarm_event_id, user_id=1, comment=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE AlarmEvent
        SET State = CASE 
                        WHEN State = 'ActiveUnack' THEN 'ActiveAck'
                        WHEN State = 'ReturnToNormalUnack' THEN 'ReturnToNormalAck'
                        ELSE State
                    END,
            AcknowledgedBy = ?,
            AcknowledgedTime = SYSDATETIME(),
            Comment = ISNULL(Comment, '') + COALESCE(?, '')
        WHERE AlarmEventID = ?
    """, user_id, comment, alarm_event_id)
    conn.commit()
    conn.close()

def main():
    stop_flag = {"stop": False}

    import threading
    t = threading.Thread(target=alarm_logic_loop, args=(stop_flag,))
    t.start()

    try:
        while True:
            cmd = input("Alarm CLI (list, ack <id>, quit): ").strip()
            if cmd == "list":
                list_active_alarms()
            elif cmd.startswith("ack"):
                parts = cmd.split()
                if len(parts) == 2 and parts[1].isdigit():
                    acknowledge_alarm(int(parts[1]), user_id=1, comment="Ack from CLI")
                else:
                    print("Usage: ack <AlarmEventID>")
            elif cmd == "quit":
                break
            else:
                print("Unknown command")
    finally:
        stop_flag["stop"] = True
        t.join()

if __name__ == "__main__":
    main()
