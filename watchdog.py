from multiprocessing import Process
from time import process_time, gmtime, time, strftime
import watchdog_lib


def main(asynchronous=False):

    # Important: Minimum allowed value of the 'thread_count' variable is 2 in each process
    threads_count = 10
    parallel_processes = []


    if asynchronous:
        print(f'PY: Running in asynchronous mode using the httpx library')
        # Run Parallel Job: Properties for sale (Child Process 0)
        parallel_processes.append(Process( 
            target=watchdog_lib.main_execution_flow_async,
            args=(f"prodej", f"k prodeji", f"/prodam/byt/", threads_count, watchdog_lib.process_ids[0], watchdog_lib.cpu_affinity[0],)
        ))
        [parallel_processes[i].start() for i in range(len(parallel_processes))]

        # Run Parallel Job: Properties for rent (Main Process 1)
        watchdog_lib.main_execution_flow_async(f"pronajem", f"k pronájmu", f"/pronajmu/byt/", threads_count, watchdog_lib.process_ids[1], cpu_affinity=watchdog_lib.cpu_affinity[1])
    else:
        print(f'PY: Running using the requests library')
        # Run Parallel Job: Properties for sale (Child Process 0)
        parallel_processes.append(Process( 
            target=watchdog_lib.main_execution_flow,
            args=(f"prodej", f"k prodeji", f"/prodam/byt/", threads_count, watchdog_lib.process_ids[0], watchdog_lib.cpu_affinity[0],)
        ))
        [parallel_processes[i].start() for i in range(len(parallel_processes))]

        # Run Parallel Job: Properties for rent (Main Process 1)
        watchdog_lib.main_execution_flow(f"pronajem", f"k pronájmu", f"/pronajmu/byt/", threads_count, watchdog_lib.process_ids[1], cpu_affinity=watchdog_lib.cpu_affinity[1])

    # Join Parallel Jobs
    [parallel_processes[i].join() for i in range(len(parallel_processes))]


if __name__ == '__main__':
    cpu_time_start = process_time()
    wall_time_start = time()

    watchdog_lib.get_cpu_info()
    all_least_utilized_cores_sorted = watchdog_lib.get_cpus_with_least_usage()
    two_least_utilized_cores_sorted = watchdog_lib.get_cpus_with_least_usage(2)

    main(asynchronous=True)

    elapsed_cpu_time = process_time() - cpu_time_start
    elapsed_wall_time = time() - wall_time_start
    print("PY: CPU time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_cpu_time)))
    print("PY: Wall time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_wall_time)))
