from multiprocessing import Process
from time import process_time, gmtime, time, strftime
from os import path
from watchdog_lib import unmask_database_items, \
                         check_for_active_urls_threaded, \
                         write_content_to_output_files, \
                         send_report_email, \
                         remove_dir, \
                         recepients_list


def main():

    # Properties for sale
    all_target_properties_details = unmask_database_items("prodej")
    check_for_active_urls_threaded(all_target_properties_details, 0)
    write_content_to_output_files("prodej", all_target_properties_details, directory="temp")
    send_report_email("prodej", "k prodeji", recepients_list)
    remove_dir(f"{path.dirname(path.realpath(__file__))}\\temp")

    # Properties for rent
    all_target_properties_details = unmask_database_items("pronajem")
    check_for_active_urls_threaded(all_target_properties_details, 0)
    write_content_to_output_files("pronajem", all_target_properties_details, directory="temp")
    send_report_email("pronajem", "k pronájmu", recepients_list)
    remove_dir(f"{path.dirname(path.realpath(__file__))}\\temp")


if __name__ == '__main__':
    cpu_time_start = process_time()
    wall_time_start = time()
    main()
    elapsed_cpu_time = process_time() - cpu_time_start
    elapsed_wall_time = time() - wall_time_start
    print("PY: CPU time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_cpu_time)))
    print("PY: Wall time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_wall_time)))
