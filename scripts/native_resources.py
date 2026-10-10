"""Windows native process resource observation, not container/model capacity evidence."""
import ctypes
from ctypes import wintypes
import json
import time
from pathlib import Path
from scripts.native_workload import run


class Counters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]


def memory():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    info=Counters();info.cb=ctypes.sizeof(info)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(info),info.cb):raise ctypes.WinError(ctypes.get_last_error())
    return {'working_set_bytes':info.WorkingSetSize,'peak_working_set_bytes':info.PeakWorkingSetSize,'peak_pagefile_bytes':info.PeakPagefileUsage}


def main():
    budget={'peak_working_set_bytes':256*1024*1024,'cpu_seconds':5,'wall_seconds':10,'concurrency':1,'operations':100}
    before=memory();cpu=time.process_time();wall=time.perf_counter();result=run()
    cpu=time.process_time()-cpu;wall=time.perf_counter()-wall;after=memory()
    samples=result.pop('samples_ms')
    record={'scope':'Single native Python core process including imports/setup; 100 operations, temporary SQLite. Process lifetime peak, not incremental allocation or full stack.',
            'budget':budget,'before':before,'after':after,'cpu_seconds':cpu,'wall_seconds':wall,
            'resource_budget_met':after['peak_working_set_bytes']<=budget['peak_working_set_bytes'] and cpu<=budget['cpu_seconds'] and wall<=budget['wall_seconds'],
            'workload':result,'exclusions':['model residency','GPU','UI','PostgreSQL','n8n','Graph','Odoo','containers','production capacity']}
    folder=Path('local/phase-6');folder.mkdir(parents=True,exist_ok=True)
    raw=folder/f'native-resources-{time.time_ns()}.json';raw.write_text(json.dumps({**record,'samples_ms':samples},indent=2))
    record['raw_local_file']=str(raw).replace('\\','/')
    Path('docs/evidence/phase-6-native-resources.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))


if __name__=='__main__':main()
