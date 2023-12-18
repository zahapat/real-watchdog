import asyncio
import psutil
from multiprocessing import Process
from time import process_time, gmtime, time, strftime
from os import path
from watchdog_lib import unmask_database_items, \
                         check_for_active_urls_threaded, \
                         check_for_active_urls_threaded_async, \
                         write_content_to_output_files, \
                         send_report_email, \
                         remove_dir, \
                         recepients_list, \
                         process_ids, \
                         cpu_affinity


def report(purpose, purpose_context, process_id, cpu_affinity=None, asynchronous=False):

    # This process is supposed to be executed on a separate core defined by cpu_id. Check affinity, assign the process to this core altering the affinity.
    if cpu_affinity != None:
        this_process = psutil.Process()
        print(f'PY: Process #{process_id}: {this_process}, affinity {this_process.cpu_affinity()}')
        this_process.cpu_affinity([cpu_affinity])
        print(f'PY: Process #{process_id}: Set affinity to {cpu_affinity}, affinity now {this_process.cpu_affinity()}')

    all_target_properties_details = unmask_database_items(purpose)
    if asynchronous:
        asyncio.run(check_for_active_urls_threaded_async(all_target_properties_details, 0))
    else:
        check_for_active_urls_threaded(all_target_properties_details, 0)
    write_content_to_output_files(purpose, all_target_properties_details, directory=f"temp_{purpose}")
    send_report_email(purpose, purpose_context, recepients_list)
    remove_dir(f"{path.dirname(path.realpath(__file__))}\\temp_{purpose}")


def main():

    parallel_processes = []

    # Run Parallel Job: Properties for sale (Parallel Core 0)
    parallel_processes.append(Process( 
        target=report,
        args=("prodej", "k prodeji", process_ids[0], cpu_affinity[0], True,)
    ))
    [parallel_processes[i].start() for i in range(len(parallel_processes))]

    # Run Parallel Job: Properties for rent (Main Core 0)
    report("pronajem", "k pronájmu", process_ids[1], cpu_affinity[1], asynchronous=True)

    # Join Parallel Jobs
    [parallel_processes[i].join() for i in range(len(parallel_processes))]


if __name__ == '__main__':
    cpu_time_start = process_time()
    wall_time_start = time()
    main()
    elapsed_cpu_time = process_time() - cpu_time_start
    elapsed_wall_time = time() - wall_time_start
    print("PY: CPU time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_cpu_time)))
    print("PY: Wall time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_wall_time)))
