#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from common.common_db import get_connection

REFRESH_MS = 1000  # 1 second
MAX_POINTS = 200   # sliding window of last points

def get_all_variables():
    """
    Read all active tags from SQL Server Tag table.
    Returns list of (TagID, Name) tuples.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TagID, Name
        FROM Tag
        WHERE IsActive = 1
        ORDER BY Name
    """)
    rows = cursor.fetchall()
    conn.close()
    return [(int(r.TagID), r.Name) for r in rows]

def get_history_sql(tag_id, last_timestamp=None):
    """
    Read history from TagValueLog for a given tag.
    If last_timestamp is provided, only return newer data.
    Returns (times, values, new_last_timestamp)
    """
    conn = get_connection()
    cursor = conn.cursor()

    if last_timestamp is None:
        cursor.execute("""
            SELECT TOP 500 [Timestamp], Value
            FROM TagValueLog
            WHERE TagID = ?
            ORDER BY [Timestamp] ASC
        """, tag_id)
    else:
        cursor.execute("""
            SELECT [Timestamp], Value
            FROM TagValueLog
            WHERE TagID = ? AND [Timestamp] > ?
            ORDER BY [Timestamp] ASC
        """, tag_id, last_timestamp)

    times = []
    vals = []
    last_ts = last_timestamp

    for ts, val in cursor.fetchall():
        dt = ts  # ts is already a datetime from SQL Server
        times.append(dt)
        vals.append(float(val))
        last_ts = dt

    conn.close()
    return times, vals, last_ts
def get_active_alarms():
    """
    Return list of active (unacknowledged) alarms.
    Each row: (AlarmEventID, Time, TagName, AlarmName, State, Value, Priority)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ae.AlarmEventID,
            ae.EventTime,
            t.Name AS TagName,
            ad.Name AS AlarmName,
            ae.State,
            ae.ValueAtEvent,
            ad.Priority
        FROM AlarmEvent ae
        JOIN AlarmDefinition ad ON ae.AlarmDefID = ad.AlarmDefID
        JOIN Tag t ON ae.TagID = t.TagID
        WHERE ae.State LIKE 'Active%'
        ORDER BY ae.EventTime DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def acknowledge_alarm_event(alarm_event_id, user_id=1, comment="Ack from GUI"):
    """
    Acknowledge a single AlarmEvent.
    """
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
            Comment = ISNULL(Comment, '') + ' ' + ?
        WHERE AlarmEventID = ?
    """, user_id, comment, alarm_event_id)
    conn.commit()
    conn.close()


class LivePlotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SCADA Historical & Live Data")
        self.geometry("1000x650")

        self.all_variables = []      # list of (TagID, Name)
        self.current_tag_id = None
        self.current_var_name = None
        self.x_data = []
        self.y_data = []
        self.last_timestamp = None
        self.line = None

        # ---------- TOP BAR ----------
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(top, text="Search tag:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(top, textvariable=self.search_var, width=25)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search_changed)

        ttk.Label(top, text="Tag:").pack(side=tk.LEFT, padx=(15, 0))
        self.var_combo = ttk.Combobox(top, state="readonly", width=45)
        self.var_combo.pack(side=tk.LEFT, padx=5)

        self.plot_button = ttk.Button(top, text="Plot", command=self.start_plot)
        self.plot_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(top, text="Loading tags from SQL Server...")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # ---------- FIGURE ----------
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        # ---------- BOTTOM BAR ----------
        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        self.last_point_label = ttk.Label(bottom, text="Last point: -  |  Value: -")
        self.last_point_label.pack(side=tk.LEFT)

                # ---------- ALARM PANEL ----------
        alarm_frame = ttk.LabelFrame(self, text="Active Alarms")
        alarm_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        columns = ("id", "time", "tag", "alarm", "state", "value", "prio")
        self.alarm_tree = ttk.Treeview(
            alarm_frame, columns=columns, show="headings", height=5
        )
        self.alarm_tree.heading("id", text="ID")
        self.alarm_tree.heading("time", text="Time")
        self.alarm_tree.heading("tag", text="Tag")
        self.alarm_tree.heading("alarm", text="Alarm")
        self.alarm_tree.heading("state", text="State")
        self.alarm_tree.heading("value", text="Value")
        self.alarm_tree.heading("prio", text="Prio")

        self.alarm_tree.column("id", width=60, anchor=tk.CENTER)
        self.alarm_tree.column("time", width=150)
        self.alarm_tree.column("tag", width=140)
        self.alarm_tree.column("alarm", width=140)
        self.alarm_tree.column("state", width=100, anchor=tk.CENTER)
        self.alarm_tree.column("value", width=80, anchor=tk.E)
        self.alarm_tree.column("prio", width=50, anchor=tk.CENTER)

        self.alarm_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)

        alarm_buttons = ttk.Frame(alarm_frame)
        alarm_buttons.pack(side=tk.LEFT, padx=5, pady=5)

        self.refresh_alarm_btn = ttk.Button(
            alarm_buttons, text="Refresh alarms", command=self.refresh_alarms_once
        )
        self.refresh_alarm_btn.pack(fill=tk.X, pady=2)

        self.ack_alarm_btn = ttk.Button(
            alarm_buttons, text="Acknowledge selected", command=self.ack_selected_alarm
        )
        self.ack_alarm_btn.pack(fill=tk.X, pady=2)

        # periodic refresh of alarms
        self.after(2000, self.refresh_alarms_periodic)


        # Load variables from DB
        self.after(100, self.load_variables)

    def load_variables(self):
        try:
            self.all_variables = get_all_variables()  # list of (TagID, Name)
            names = [name for (_id, name) in self.all_variables]
            self.update_combo(names)
            self.status_label.config(
                text=f"Connected. {len(self.all_variables)} tags loaded."
            )
        except Exception as e:
            self.status_label.config(text=f"Error loading tags: {e}")

    # ---------- SEARCH ----------
    def on_search_changed(self, event=None):
        text = self.search_var.get().strip()
        if not text:
            filtered = self.all_variables
        else:
            t_lower = text.lower()
            filtered = [
                (tid, name) for (tid, name) in self.all_variables
                if t_lower in name.lower()
            ]
        names = [name for (_id, name) in filtered]
        self.update_combo(names)

    def update_combo(self, values):
        self.var_combo["values"] = values
        if values:
            self.var_combo.current(0)
        else:
            self.var_combo.set("")

    # ---------- PLOT ----------
    def start_plot(self):
        var_name = self.var_combo.get()
        if not var_name:
            self.status_label.config(text="No tag selected.")
            return

        # find TagID for selected name
        tag_id = None
        for (tid, name) in self.all_variables:
            if name == var_name:
                tag_id = tid
                break

        if tag_id is None:
            self.status_label.config(text="Selected tag not found.")
            return

        self.current_tag_id = tag_id
        self.current_var_name = var_name
        self.status_label.config(text=f"Plotting: {var_name}")
        self.x_data = []
        self.y_data = []
        self.last_timestamp = None

        try:
            times, vals, self.last_timestamp = get_history_sql(tag_id, last_timestamp=None)
        except Exception as e:
            self.status_label.config(text=f"Error loading data: {e}")
            return

        if not vals:
            self.status_label.config(text=f"No data found for {var_name}.")
            return

        x_temp = mdates.date2num(times)
        y_temp = vals

        if len(x_temp) > MAX_POINTS:
            self.x_data = x_temp[-MAX_POINTS:]
            self.y_data = y_temp[-MAX_POINTS:]
        else:
            self.x_data = x_temp
            self.y_data = y_temp

        self.ax.clear()
        self.ax.set_title(var_name)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)

        (self.line,) = self.ax.plot(self.x_data, self.y_data, "b.-")

        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        self.fig.autofmt_xdate()
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

        last_dt = times[-1]
        last_val = vals[-1]
        self.last_point_label.config(
            text=f"Last point: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}  |  Value: {last_val}"
        )

        self.after(REFRESH_MS, self.update_plot)

    def update_plot(self):
        if self.current_tag_id is None:
            return

        try:
            times, vals, self.last_timestamp = get_history_sql(
                self.current_tag_id, last_timestamp=self.last_timestamp
            )
        except Exception as e:
            self.status_label.config(text=f"Error updating data: {e}")
            self.after(REFRESH_MS, self.update_plot)
            return

        if vals:
            new_x = mdates.date2num(times)
            self.x_data = list(self.x_data) + list(new_x)
            self.y_data = list(self.y_data) + vals

            if len(self.x_data) > MAX_POINTS:
                self.x_data = self.x_data[-MAX_POINTS:]
                self.y_data = self.y_data[-MAX_POINTS:]

            self.line.set_xdata(self.x_data)
            self.line.set_ydata(self.y_data)

            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()

            last_dt = times[-1]
            last_val = vals[-1]
            self.last_point_label.config(
                text=f"Last point: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}  |  Value: {last_val}"
            )

        self.after(REFRESH_MS, self.update_plot)
        # ---------- ALARMS ----------
    def refresh_alarms_once(self):
        """Reload active alarms from DB into the Treeview."""
        for item in self.alarm_tree.get_children():
            self.alarm_tree.delete(item)

        try:
            rows = get_active_alarms()
        except Exception as e:
            self.status_label.config(text=f"Error loading alarms: {e}")
            return

        for row in rows:
            alarm_id, event_time, tag_name, alarm_name, state, value, prio = row
            time_str = event_time.strftime("%Y-%m-%d %H:%M:%S")
            value_str = f"{value:.2f}" if value is not None else "-"
            self.alarm_tree.insert(
                "", tk.END,
                values=(alarm_id, time_str, tag_name, alarm_name, state, value_str, prio)
            )

    def refresh_alarms_periodic(self):
        """Periodic auto-refresh of alarms."""
        self.refresh_alarms_once()
        self.after(2000, self.refresh_alarms_periodic)

    def ack_selected_alarm(self):
        """Acknowledge the alarm selected in the Treeview."""
        selected = self.alarm_tree.selection()
        if not selected:
            self.status_label.config(text="No alarm selected.")
            return

        item_id = selected[0]
        values = self.alarm_tree.item(item_id, "values")
        alarm_event_id = int(values[0])  # first column is ID

        try:
            acknowledge_alarm_event(alarm_event_id, user_id=1, comment="Ack from GUI")
            self.status_label.config(text=f"Acknowledged alarm {alarm_event_id}")
            self.refresh_alarms_once()
        except Exception as e:
            self.status_label.config(text=f"Error acknowledging alarm: {e}")



if __name__ == "__main__":
    app = LivePlotApp()
    app.mainloop()
