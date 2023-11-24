from multiprocessing import Process
from time import process_time, gmtime, time, strftime
import watchdog_lib


def main():

    # Important: Minimum allowed number of the 'thread_count' variable is 2 within each process
    threads_count = 5
    parallel_processes = []

    # Properties for sale
    parallel_processes.append(Process( target=watchdog_lib.main_execution_flow,
        args=(f"prodej", f"k prodeji", f"/prodam/byt/", threads_count, watchdog_lib.cpu_ids[0],)
    ))

    # Properties for rent
    parallel_processes.append(Process( target=watchdog_lib.main_execution_flow,
        args=(f"pronajem", f"k pronájmu", f"/pronajmu/byt/", threads_count, watchdog_lib.cpu_ids[1],)
    ))

    [parallel_processes[i].start() for i in range(len(parallel_processes))]
    [parallel_processes[i].join() for i in range(len(parallel_processes))]


if __name__ == '__main__':
    cpu_time_start = process_time()
    wall_time_start = time()
    main()
    elapsed_cpu_time = process_time() - cpu_time_start
    elapsed_wall_time = time() - wall_time_start
    print("PY: CPU time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_cpu_time)))
    print("PY: Wall time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_wall_time)))
