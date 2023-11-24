from multiprocessing import Process
from time import process_time, gmtime, time, strftime
from os import path
import watchdog_lib


def main():

    # Properties for sale
    all_target_properties_details = watchdog_lib.unmask_database_items("prodej")
    watchdog_lib.check_for_active_urls_threaded(all_target_properties_details, 0)
    watchdog_lib.write_content_to_output_files("prodej", all_target_properties_details, directory="temp")
    watchdog_lib.send_report_email("prodej", "k prodeji", watchdog_lib.recepients_list)
    watchdog_lib.remove_dir(f"{path.dirname(path.realpath(__file__))}\\temp")

    # Properties for rent
    all_target_properties_details = watchdog_lib.unmask_database_items("pronajem")
    watchdog_lib.check_for_active_urls_threaded(all_target_properties_details, 0)
    watchdog_lib.write_content_to_output_files("pronajem", all_target_properties_details, directory="temp")
    watchdog_lib.send_report_email("pronajem", "k pronájmu", watchdog_lib.recepients_list)
    watchdog_lib.remove_dir(f"{path.dirname(path.realpath(__file__))}\\temp")



if __name__ == '__main__':
    cpu_time_start = process_time()
    wall_time_start = time()
    main()
    elapsed_cpu_time = process_time() - cpu_time_start
    elapsed_wall_time = time() - wall_time_start
    print("PY: CPU time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_cpu_time)))
    print("PY: Wall time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_wall_time)))
