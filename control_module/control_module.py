# control_module.py
import time
import threading
from opcua import ua, Server

# Simple PID controller
class PIDController:
    def __init__(self, Kp, Ki, Kd, dt, u_min=0.0, u_max=100.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.u_min = u_min
        self.u_max = u_max
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, setpoint, pv):
        error = setpoint - pv
        self.integral += error * self.dt
        derivative = (error - self.prev_error) / self.dt
        u = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        # Clamp
        u = max(self.u_min, min(self.u_max, u))
        self.prev_error = error
        return u

# Simple first-order process model (simulated Air Heater)
class AirHeaterSim:
    def __init__(self, ambient=25.0, gain=0.5, tau=30.0, dt=0.1):
        self.ambient = ambient
        self.gain = gain
        self.tau = tau
        self.dt = dt
        self.pv = ambient

    def step(self, u):
        # u in 0-100%, convert to "power"
        power = u / 100.0
        dT = (-(self.pv - self.ambient) + self.gain * 100 * power) * self.dt / self.tau
        self.pv += dT
        return self.pv

def run_control_loop(pv_var, sp_var, co_var, stop_event):
    dt = 0.1  # 100 ms
    pid = PIDController(Kp=2.0, Ki=0.5, Kd=0.0, dt=dt, u_min=0.0, u_max=100.0)
    process = AirHeaterSim(dt=dt)

    # Initialize SP
    sp_var.set_value(ua.Variant(50.0, ua.VariantType.Double))

    while not stop_event.is_set():
        sp = sp_var.get_value()
        pv = process.pv
        co = pid.update(sp, pv)
        pv = process.step(co)

        pv_var.set_value(ua.Variant(float(pv), ua.VariantType.Double))
        co_var.set_value(ua.Variant(float(co), ua.VariantType.Double))

        time.sleep(dt)

def main():
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/scada_poc/")
    server.set_server_name("SCADA_PoC_AirHeater")

    uri = "http://examples.scada_poc"
    idx = server.register_namespace(uri)

    objects = server.get_objects_node()
    air_heater = objects.add_object(idx, "AirHeater")

    # Explicit string NodeIds so client can use ns=2;s=AirHeater.PV etc.
    pv_var = air_heater.add_variable(ua.NodeId("AirHeater.PV", idx), "PV", 25.0)
    sp_var = air_heater.add_variable(ua.NodeId("AirHeater.SP", idx), "SP", 40.0)
    co_var = air_heater.add_variable(ua.NodeId("AirHeater.CO", idx), "CO", 0.0)

    # Allow clients to write SP; PV and CO are read-only for clients
    sp_var.set_writable()

    server.start()
    print("OPC UA server started at opc.tcp://localhost:4840/scada_poc/")

    stop_event = threading.Event()
    control_thread = threading.Thread(
        target=run_control_loop, args=(pv_var, sp_var, co_var, stop_event)
    )
    control_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        stop_event.set()
        control_thread.join()
        server.stop()

if __name__ == "__main__":
    main()
