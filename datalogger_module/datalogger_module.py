# datalogger_module.py
import time
from datetime import datetime, timezone
from opcua import Client
from common.common_db import get_connection

# Hard-coded TagIDs for simplicity; match what you inserted in SQL
TAGID_PV = 1
TAGID_SP = 2
TAGID_CO = 3

def main():
    opc_client = Client("opc.tcp://localhost:4840/scada_poc/")
    opc_client.connect()
    print("Datalogger connected to OPC UA server")

    idx = 2  # ns=2 from server; adjust if needed
    pv_node = opc_client.get_node(f"ns={idx};s=AirHeater.PV")
    sp_node = opc_client.get_node(f"ns={idx};s=AirHeater.SP")
    co_node = opc_client.get_node(f"ns={idx};s=AirHeater.CO")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        while True:
            now = datetime.now(timezone.utc)

            pv = float(pv_node.get_value())
            sp = float(sp_node.get_value())
            co = float(co_node.get_value())

            # Call stored procedure for each tag
            cursor.execute("EXEC usp_LogTagValue ?, ?, ?, ?, ?",
                           TAGID_PV, now, pv, "Good", "Datalogger")
            cursor.execute("EXEC usp_LogTagValue ?, ?, ?, ?, ?",
                           TAGID_SP, now, sp, "Good", "Datalogger")
            cursor.execute("EXEC usp_LogTagValue ?, ?, ?, ?, ?",
                           TAGID_CO, now, co, "Good", "Datalogger")
            conn.commit()

            print(f"Logged PV={pv:.2f}, SP={sp:.2f}, CO={co:.2f} at {now.isoformat()}")
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("Stopping datalogger...")
    finally:
        opc_client.disconnect()
        conn.close()

if __name__ == "__main__":
    main()
