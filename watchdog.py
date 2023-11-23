import requests
import pandas as pd
from queue import Queue
from time import process_time, gmtime, time, strftime
from os import environ, path
from threading import Thread
from multiprocessing import Process
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from re import compile, findall
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sys import stdin, stdout

# Configure the environment to support accented characters
stdin.reconfigure(encoding='utf-8-sig')
stdout.reconfigure(encoding='utf-8-sig')

# Set browser ID
agent = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.160 Safari/537.36'
}

# -------------------------------------------------
#                     SECRETS
# -------------------------------------------------
# Array envs
recepients_list = list(filter(None, environ["recepients_email"].split(',')))
search_cities_list = list(filter(None, str(environ["search_cities_list"]).split(',')))


# String envs
zone_info = environ["zone_info"]
smtp_server = environ["smtp_server"]
smtp_port = int(environ["smtp_port"])
smtp_username = environ["smtp_username"]
mail_app_password = environ["mail_app_password"]
website_url_root = environ["website_url_root"]
search_requirements = environ["search_requirements"]
mask = int(environ["mask"])


# Note: Only APPEND new items at the end of the list, do not insert anything in the middle or beginning of the list
search_dispositions_list = [
    # STR           REGEX
    ["1+1",  r"\b1\s?\+\s?1\b"],
    ["2+1",  r"\b2\s?\+\s?1\b"],
    ["3+1",  r"\b3\s?\+\s?1\b"],
    ["1+kk", r"\b1\s?\+?\s?[k|K]{2}\b|\bgar[s|z]on\w+\b|\bstudio\b"],
    ["2+kk", r"\b2\s?\+?\s?[k|K]{2}\b"],
    ["3+kk", r"\b3\s?\+?\s?[k|K]{2}\b"]
]

search_details = [
    "osobní",
    "OV",
    "družstevní",
    "po rekonstrukci",
    "centrum",
    "novostavb",
    "zateplen",
    "MHD",
    "aukc",
    "balk",
    "plastová okna"
]

cpu_cores = 2
cpu_ids = [i for i in range(cpu_cores)]
advertisements_done = [0 for i in range(cpu_cores)]




# Send an email
def send_email(purpose, to_recepients_list, new_target_properties_details):
    send_email = False
    search_dispositions_list_len = len(search_dispositions_list)
    for i in range(search_dispositions_list_len):
        if len(new_target_properties_details[i]) > 0:
            send_email = True
    if send_email == True:
        pass
    else:
        print(f"There are no new properties. Skip sending email messsage.")
        return 1

    subject = 'Watchdog: nové položky '+purpose+' ze dne '\
        +str(datetime.now(ZoneInfo(zone_info)).date().strftime("%d.%m.%Y"))


    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = ', '.join(to_recepients_list)
    msg['Subject'] = subject

    # Body: Intro
    body1 = (
        f"Toto je hlídací pes nových vybraných nemovitostí. \n\n"
        f"Detaily o nově inzerovaných položkách "+purpose+" naleznete na odkazech níže.\n\n"
        f" \n\n"
    )
    # Body: New properties listed
    body2 = ""
    for i, new_target_properties_detail in enumerate(new_target_properties_details):
        for new_target_property_detail in new_target_properties_detail:
            if new_target_property_detail[7] in search_dispositions_list[i][0]:
                body2 += f"{new_target_property_detail[7]}, {new_target_property_detail[6]} {new_target_property_detail[5]}, přidáno dne {new_target_property_detail[1]}:\n"
                body2 += f"Odkaz: {new_target_property_detail[3]}\n"
                body2 += f"Detaily: {new_target_property_detail[4]} Kč {new_target_property_detail[8]}\n"
                body2 += f" \n"
        if len(new_target_properties_detail) > 0:
            body2 += f"\n\n"

    body = str(body1)+str(body2)
    msg.attach(MIMEText(body))

    with SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, mail_app_password)
        smtp.sendmail(from_addr=smtp_username, to_addrs=recepients_list, msg=msg.as_string())


    # Reset the list content to empty list of lists
    new_target_properties_details = [[] for i in search_dispositions_list]

    print(f"PY: Email has been sent successfully.")

    return 0


# Create a file if does not exist in the current file directory
def create_file(output_directory, file_name):
    file_gen_name = file_name
    file_gen_fullpath = f"{output_directory}\\database\\{file_gen_name}"
    print(f"PY: New file {file_gen_name} created: {file_gen_fullpath}")
    file_gen_line = open(file_gen_fullpath, 'w', encoding="utf-8-sig")
    file_gen_line.close()


# Function to get already searched urls from files in the current file directory
def get_data_from_file(file_name):
    try:
        print(f"PY: Getting data from CSV files...")
        target_properties_details = [] # Try not global this time
        output_directory = path.dirname(path.realpath(__file__))
        file_gen_fullpath = f"{output_directory}\\database\\{file_name}"

        target_properties_details = pd.read_csv(
            file_gen_fullpath, 
            encoding="utf-8-sig",
            sep = ',', header=None, 
            names=['Active', 'Date Added', 'Last Active' , 'URL', 'Price', 'ZIP', 'City', 'Disposition', 'Detail'], 
            dtype={
                'Active': 'string',
                'Date Added': 'string',
                'Last Active': 'string',
                'URL': 'string',
                'Price': 'string',
                'ZIP': 'string',
                'City': 'string',
                'Disposition': 'string',
                'Detail': 'string',
            }
        ).assign(Active=lambda x: 'X').values.tolist()



    except Exception as e:
        # print(f"PY: ErrorHandler: Detected Error: {e}. Creating a file")
        create_file(output_directory, file_name)
    
    print(f"PY: Getting data from CSV files DONE.")

    return target_properties_details



# Function to search for the pattern in a web page
def get_details(url, advertised_property_details, new_target_properties_details_queue):

    try:
        searched_property_details = ""
        response = requests.get(url=url, headers=agent)
        if response.status_code == 200:
            page_content = response.text

            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(page_content, "html.parser")
            header = str(soup.find_all("h1", {"class": "nadpisdetail"})).replace("<h1 class=\"nadpisdetail\">","").replace("</h1>","")
            details = str(soup.find_all("div", {"class": "popisdetail"})).replace("<div class=\"popisdetail\">","").replace("</div>","")

            # Search for the target disposition keyword in the page content
            is_target_disposition = False
            for search_disposition in search_dispositions_list:
                # Search in header
                if ((search_disposition[0] in header)                       # String (static, faster execution)
                    or compile(search_disposition[1]).findall(header)):  # Regex (flexible, slower execution)
                    is_target_disposition = True
                    advertised_property_details[7] = search_disposition[0]
                    break

                # Search in description
                elif ((search_disposition[0] in details)            # String (static, faster execution)
                    or compile(search_disposition[1]).findall(details)):  # Regex (flexible, slower execution)
                    is_target_disposition = True
                    advertised_property_details[7] = search_disposition[0]
                    break

            # If target disposition found:
            if is_target_disposition == True:

                # Get Keywords about the property
                for search_detail in search_details:
                    if search_detail in page_content:
                        # Faster method than using StringIO on smaller strings
                        searched_property_details += f"|  {search_detail}  "
                advertised_property_details[8] = searched_property_details

                # Get date added
                date_added = str(soup.find_all("span", {"class": "velikost10"})[0]).replace("<span class=\"velikost10\">","").replace("</span>","").replace(" ", "").split('-[')[1].replace("]", "")
                advertised_property_details[1] = datetime.strptime(date_added, "%d.%m.%Y").date().strftime("%d.%m.%Y")

                # Announce new advertised property
                advertised_property_details[3] = url
                new_target_properties_details_queue.put(advertised_property_details.copy())
                print(f"PY: New item: {advertised_property_details}")


    except ValueError as e:
        print(f"Error while processing {url}: {e}")



# Function to search for the pattern in a web page
def search_in_page(url, all_target_properties_details, new_target_properties_details_queue, cpu_id):
    global advertisements_done
    try:
        # A set to keep track of visited URLs to avoid infinite loops
        advertised_property_details = [
            'A',    # [0] 'A' = Active / 'X' = Inactive
            0,      # [1] Date Added
            str(datetime.now(ZoneInfo(zone_info)).date().strftime("%d.%m.%Y")),      # [2] Last Active
            0,      # [3] URL
            0,      # [4] Price
            0,      # [5] ZIP
            0,      # [6] City
            0,      # [7] Disposition
            0       # [8] Details
        ]
        response = requests.get(url=url, headers=agent)
        if response.status_code == 200:
            page_content = response.text

            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(page_content, "html.parser")

            advertisements = 0
            for div in soup.find_all("div", {"class": "inzeraty inzeratyflex"}):
                advertisements = advertisements + 1
                for line in div:
                    line = str(line)
                    if line.startswith("<div class=\"inzeratynadpis\">"):
                        advertised_property_details[3] = line.replace("<div class=\"inzeratynadpis\"><a href=\"", "").split("\">",1)[0]

                    elif line.startswith("<div class=\"inzeratycena\">"):
                        advertised_property_details[4] = line.replace("<div class=\"inzeratycena\"><b>", "").replace("</b></div>", "").replace("Kč", "").replace(" ", "")

                    elif line.startswith("<div class=\"inzeratylok\">"):
                        area = line.replace("<div class=\"inzeratylok\">", "").replace("</div>", "").split("<br/>", 2)
                        advertised_property_details[5] = area[1]
                        advertised_property_details[6] = area[0]

                        # Skip if not among desired cities
                        for search_city_list in search_cities_list:
                            if area[0] == search_city_list:
                                # Check if URL not visited before
                                visited = False

                                # Using len() and indices is 15 seconds faster than for _ in _ method in the first for loop
                                search_dispositions_list_len = len(search_dispositions_list)
                                for i in range(search_dispositions_list_len):
                                    for all_target_properties_detail in all_target_properties_details[i]:

                                        # Use short-circuit evaluation and utilize the and operation to 'fail the condition faster'
                                        if (all_target_properties_detail[0] == "A") \
                                            and advertised_property_details[3] in mask_char_values_in_string(all_target_properties_detail[3], -mask):

                                            # Mark as Active and set visited flag to True
                                            print(f"PY: Skip: {mask_char_values_in_string(all_target_properties_detail[3], -mask)}")
                                            visited = True
                                            break

                                    if visited == True: 
                                        break


                                if visited == False:
                                    get_details(
                                        website_url_root+advertised_property_details[3], 
                                        advertised_property_details,
                                        new_target_properties_details_queue)

        # Returns 1 if on the last page, else 0 to proceed to the next page
        if advertisements == 0: 
            advertisements_done[cpu_id] = 1
            return 1
        advertisements_done[cpu_id] = 0
        return 0

    except ValueError as e:
        print(f"Error while processing {url}: {e}")


def check_if_active_property_thread(all_target_property_detail, all_target_properties_detail_queue):
    try:
        response = requests.get(url=mask_char_values_in_string(all_target_property_detail[3], -mask), headers=agent)
        if response.status_code == 200:
            page_content = response.text

            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(page_content, "html.parser")

            # Check if the date added matches the logged value, then it is still an active item
            date_added = str(soup.find_all("span", {"class": "velikost10"})[0]).replace("<span class=\"velikost10\">","").replace("</span>","").replace(" ", "").split('-[')[1].replace("]", "")
            if datetime.strptime(date_added, "%d.%m.%Y").date().strftime("%d.%m.%Y") in all_target_property_detail[1]:
                all_target_property_detail[0] = "A"
                all_target_property_detail[2] = str(datetime.now(ZoneInfo(zone_info)).date().strftime("%d.%m.%Y")) # Override Last Active Time
            else:
                print(f"PY: Inactive: {mask_char_values_in_string(all_target_property_detail[3], -mask)}")

    except ValueError as e:
        print(f"PY: check_if_active_property_thread: Error while processing: {mask_char_values_in_string(all_target_property_detail[3], -mask)}: {e}")
        print(f"PY: check_if_active_property_thread: DEBUG: all_target_property_detail = {all_target_property_detail}")

    all_target_properties_detail_queue.put(all_target_property_detail.copy())



def check_for_active_urls_threaded(all_target_properties_details):
    # global all_target_properties_details
    print(f"PY: Checking for active URLs...")
    threads_all_target_properties_details = [[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_len =[[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_queue = [[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_indices = [[] for i in range(len(all_target_properties_details))]

    for i, all_target_properties_detail in enumerate(all_target_properties_details):
        for pos, all_target_property_detail in enumerate(all_target_properties_detail):
            # Skip whether or not the item is active if it has been inactive for two days, otherwise check newer/active ones
            if datetime.strptime(all_target_property_detail[2], "%d.%m.%Y") >= (datetime.today() - timedelta(days=2)):
                threads_all_target_properties_details_indices[i].append(pos)
                threads_all_target_properties_details_queue[i].append(Queue())
                threads_all_target_properties_details[i].append(Thread(
                    target=check_if_active_property_thread, 
                    args=(all_target_property_detail,threads_all_target_properties_details_queue[i][-1],)
                ))
                threads_all_target_properties_details[i][-1].start()

        threads_all_target_properties_details_len[i] = len(threads_all_target_properties_details[i])
        [threads_all_target_properties_details[i][j].join() for j in range(threads_all_target_properties_details_len[i])]


    # Update the values after running multiple threads based on the content in the queue
    for i, all_target_properties_detail in enumerate(all_target_properties_details):
        for j in range(threads_all_target_properties_details_len[i]):
            all_target_properties_detail[threads_all_target_properties_details_indices[i][j]] = threads_all_target_properties_details_queue[i][j].get()

        
    print(f"PY: Checking for active URL DONE.")
    return all_target_properties_details


# Sort the databases from the newest to the oldest added item
def sort_list_by_date(all_target_properties_details):
    # global all_target_properties_details
    print(f"PY: Sorting list by time added...")
    for all_target_properties_detail in all_target_properties_details:
        all_target_properties_detail.sort(key=lambda x: datetime.strptime(x[1], "%d.%m.%Y"), reverse=True)
    print(f"PY: Sorting list by time added DONE.")

    return all_target_properties_details



# Write the content to the respective output files
def write_content_to_output_files(file_prefix, all_target_properties_details):
    print(f"PY: Writing data to CSV files...")

    # Using len() and indices is 15 seconds faster than for _ in _ method in the first for loop
    search_dispositions_list_len = len(search_dispositions_list)
    output_directory = path.dirname(path.realpath(__file__))
    for i in range(search_dispositions_list_len):
        file_gen_name = file_prefix+'_'+search_dispositions_list[i][0]+'.csv'
        file_gen_fullpath = f"{output_directory}\\database\\{file_gen_name}"

        pd.DataFrame(all_target_properties_details[i]).to_csv(
            path_or_buf=file_gen_fullpath, 
            sep = ',', header=None, 
            encoding="utf-8-sig", 
            index=False
        )

    # Reset the list content to empty list of lists and free memory
    all_target_properties_details = [[] for i in search_dispositions_list]

    print(f"PY: Writing data to CSV files DONE.")


# [UNUSED] Xor two strings to create a masked string based on a custom secret mask
def xor_two_strings(string, mask):
    # 0 = \x00; 10 = \n; 13 = \r => Bias to exclude null, \n and \r characters
    bias = 0
    str_mask_len = len(mask)
    xored = []

    # Xor an adbitrarily long string with arbitrarily long mask
    for i, string_char in enumerate(string):
        try:
            xored_value = chr((ord(string_char) ) ^ (ord(mask[i % str_mask_len]) ) + bias)
        except IndexError:
            break
        xored.append(xored_value)

    return ''.join(xored)


# Increment string character values to create a masked or unmasked string
def mask_char_values_in_string(string, bias):
    string_array = []
    for string_char in string:
        string_array.append(chr((ord(string_char) ) + bias ))

    return ''.join(string_array)


# Append all new properties to the list of all target properties
def append_all_new_properties(new_target_properties_details_queue, all_target_properties_details):
    print("PY: Update all target properties database list...")
    new_target_properties_details = [[] for i in search_dispositions_list]
    while not new_target_properties_details_queue.empty():
        # Get one item from the queue holding information about the new property
        new_target_properties_detail = new_target_properties_details_queue.get()
        print("new_target_properties_detail = ", new_target_properties_detail)

        # Sort to the corresponding disposition bucket
        for i, (search_disposition) in enumerate(search_dispositions_list):
            if (search_disposition[0] == new_target_properties_detail[7]):
                new_target_properties_details[i].append(new_target_properties_detail.copy())

                # Mask sensitive/personal information to create ambiguity, save to csv database
                new_target_properties_detail[3] = mask_char_values_in_string(new_target_properties_detail[3], mask)
                new_target_properties_detail[5] = mask_char_values_in_string(new_target_properties_detail[5], mask)
                new_target_properties_detail[6] = mask_char_values_in_string(new_target_properties_detail[6], mask)
                all_target_properties_details[i].append(new_target_properties_detail.copy())

    print("PY: Update all target properties database list DONE.")
    return all_target_properties_details, new_target_properties_details



def find_new_and_update_all_properties_from_websites(
        threads_count, all_target_properties_details, website_substring, cpu_id):
    
    # Start the search from the initial URL, loop until there is at least one advertisement
    print(f"PY: Getting data from website...")
    global advertisements_done
    threads_page = []
    new_target_properties_details_queue = Queue()
    min_scan_pages = 1
    max_scan_pages = threads_count

    threads_page.append(Thread(
        target=search_in_page,
        args=(
            f"{website_url_root}{website_substring}{search_requirements}",
            all_target_properties_details,
            new_target_properties_details_queue,
            cpu_id
        )
    ))
    threads_page[-1].start()

    while advertisements_done[int(cpu_id)] == 0:
        for page in range(min_scan_pages, max_scan_pages):
            threads_page.append(Thread(
                target=search_in_page, 
                args=(
                    f"{website_url_root}{website_substring}{page*20}/{search_requirements}",
                    all_target_properties_details,
                    new_target_properties_details_queue,
                    cpu_id
                )
            ))
            threads_page[-1].start()

        # Wait for threads to complete tasks
        [threads_page[i].join() for i in range (len(threads_page))]

        min_scan_pages = min_scan_pages + threads_count
        max_scan_pages = max_scan_pages + threads_count

        if advertisements_done[cpu_id] == 1:
            print(f"PY: Reached the last page. Break.")
            break

    threads_page = []
    advertisements_done[cpu_id] = 0
    print(f"PY: Getting data from website DONE.")

    all_target_properties_details, new_target_properties_details = append_all_new_properties(
        new_target_properties_details_queue, 
        all_target_properties_details)

    return all_target_properties_details, new_target_properties_details


def main_execution_flow(
        file_purpose_keyword, mail_purpose_occurrence_in_context_keyword, website_substring, search_threads_count, cpu_id):

    # Create an array of output files if noexist and get data from them
    all_target_properties_details = [[] for i in search_dispositions_list]
    for i, search_disposition in enumerate(search_dispositions_list):
        all_target_properties_details[i] = get_data_from_file(f'{file_purpose_keyword}_{search_disposition[0]}.csv')

    # Check if logged URLs are still active
    all_target_properties_details = check_for_active_urls_threaded(all_target_properties_details)

    # Start the search from the initial URL, loop until there is at least one advertisement
    all_target_properties_details, new_target_properties_details = find_new_and_update_all_properties_from_websites(
        search_threads_count,
        all_target_properties_details, 
        f"{website_substring}",
        cpu_id
    )

    # Sort newly added items by date
    all_target_properties_details = sort_list_by_date(all_target_properties_details)

    # Update output CSV database files
    write_content_to_output_files(f'{file_purpose_keyword}', all_target_properties_details)   

    # Send email if new properties have been detected
    send_email(f"{mail_purpose_occurrence_in_context_keyword}", recepients_list, new_target_properties_details)



def main():

    threads_count = 512
    parallel_processes = []

    # ----------------------------------------------------------------------------
    #                             PROPERTIES FOR SALE
    # ----------------------------------------------------------------------------
    parallel_processes.append(Process( target=main_execution_flow,
        args=(f"prodej", f"k prodeji", f"/prodam/byt/", threads_count, cpu_ids[0],)
    ))


    # ----------------------------------------------------------------------------
    #                             PROPERTIES FOR RENT
    # ----------------------------------------------------------------------------
    parallel_processes.append(Process( target=main_execution_flow,
        args=(f"pronajem", f"k pronájmu", f"/pronajmu/byt/", threads_count, cpu_ids[1],)
    ))

    [parallel_processes[i].start() for i in range(len(parallel_processes))]
    [parallel_processes[i].join() for i in range(len(parallel_processes))]


if __name__ == '__main__':
    cpu_time_start, wall_time_start = process_time(), time()
    main()
    elapsed_cpu_time, elapsed_wall_time = (process_time() - cpu_time_start), (time() - wall_time_start)
    print("PY: CPU time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_cpu_time)))
    print("PY: Wall time elapsed: ", strftime("%H:%M:%S", gmtime(elapsed_wall_time)))



