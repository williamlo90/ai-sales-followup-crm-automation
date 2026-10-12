"""Use the common connected lab launcher for missed-schedule acceptance."""
import os
import runpy

if __name__ == "__main__":
    os.environ["SALES_MISSED_SCHEDULE_PROBE"] = "enabled"
    runpy.run_module("scripts.connected_workload", run_name="__main__")
