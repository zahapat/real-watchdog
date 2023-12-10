from multiprocessing import Process
from time import process_time, gmtime, time, strftime
from os import path
from watchdog_lib import unmask_database_items, \
                         check_for_active_urls_threaded, \
                         write_content_to_output_files, \
                         send_report_email, \
                         remove_dir, \
                         recepients_list


def report(purpose, purpose_context):
    all_target_properties_details = unmask_database_items(purpose)
    check_for_active_urls_threaded(all_target_properties_details, 0)
    write_content_to_output_files(purpose, all_target_properties_details, directory=f"temp_{purpose}")
    send_report_email(purpose, purpose_context, recepients_list)
    remove_dir(f"{path.dirname(path.realpath(__file__))}\\temp_{purpose}")


def main():

    parallel_processes = []

    # Run Parallel Job: Properties for sale (Parallel Core 0)
    parallel_processes.append(Process( target=report,
        args=("prodej", "k prodeji",)
    ))
    [parallel_processes[i].start() for i in range(len(parallel_processes))]

    # Run Parallel Job: Properties for rent (Main Core 0)
    report("pronajem", "k pronájmu")

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
