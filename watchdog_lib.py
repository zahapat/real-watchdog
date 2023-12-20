# from pandas import DataFrame, read_csv
from polars import DataFrame, Utf8, read_csv, col
from requests import get as requests_get
from platform import processor, machine, architecture, python_version_tuple
from asyncio import run, gather
from psutil import Process as psutil_Process, cpu_percent
from httpx import AsyncClient
from time import time
from queue import Queue
from os import environ, path, listdir, mkdir, cpu_count, getpid
from threading import Thread
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from re import compile
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from sys import stdin, stdout, exit



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

# Get information about CPU
def get_cpu_info():
    print(f'PY: platform.processor() = {processor()}', flush=True)
    print(f'PY: platform.machine() = {machine()}', flush=True)
    print(f'PY: platform.architecture() = {architecture()}', flush=True)
    print(f'PY: platform.python_version_tuple() = {python_version_tuple()}', flush=True)
    print(f'PY: os.cpu_count() = {cpu_count()}', flush=True)
    print(f'PY: psutil.cpu_percent(percpu=True) = {cpu_percent(percpu=True)}', flush=True)
    print(f'PY: getpid() = {getpid()}', flush=True)
    print(f'PY: psutil.Process(getpid(getpid())).cpu_affinity() = {psutil_Process(getpid()).cpu_affinity()}', flush=True)

# Find the respective cores with least usage to assign processes to these cores later
def get_cpus_with_least_usage(number_of_cpus=None):
    cores_percentages = cpu_percent(percpu=True)
    cores_ids = [x for x in range(len(cores_percentages))]
    zipped_cores_percentages_and_ids = sorted(zip(cores_ids, cores_percentages),
                                                key= lambda zipped_item : zipped_item[1], 
                                                reverse=False)
    if number_of_cpus == None:
        print(f'PY: All cores sorted from the lowest utilization percentage (core_id, utilization): {zipped_cores_percentages_and_ids}', flush=True)
        return zipped_cores_percentages_and_ids
    else:
        print(f'PY: {number_of_cpus} cores sorted from the lowest utilization percentage (core_id, utilization): {zipped_cores_percentages_and_ids[:number_of_cpus]}', flush=True)
        return zipped_cores_percentages_and_ids[:number_of_cpus]


cpu_cores = 2
process_ids = [i for i in range(cpu_cores)]
cpu_affinity = get_cpus_with_least_usage(cpu_cores)
cpu_affinity = [[i for i, j in cpu_affinity],
                [j for i, j in cpu_affinity]][0]
advertisements_done = [0 for i in range(cpu_cores)]


# Create directory if noexist
def create_dir_if_noexist(path_to_dir):
    if not path.exists(f"{path_to_dir}"):
        mkdir(f"{path_to_dir}")
        print(f"PY: Created {path_to_dir}", flush=True)


# Remove directory if exist
def remove_dir(path):
    import shutil
    shutil.rmtree(f"{path}")
    print(f"PY: Removed {path}", flush=True)


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
        print(f"There are no new properties. Skip sending email messsage.", flush=True)
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
        for recepient in recepients_list:
            smtp.sendmail(from_addr=smtp_username, to_addrs=recepient, msg=msg.as_string())


    # Reset the list content to empty list of lists
    new_target_properties_details = [[] for i in search_dispositions_list]

    print(f"PY: Email has been sent successfully.", flush=True)

    return 0


def send_report_email(purpose, purpose_context, to_recepients_list):

    subject = 'Watchdog: report položek '+purpose_context+' ke dni '\
        +str(datetime.now(ZoneInfo(zone_info)).date().strftime("%d.%m.%Y"))

    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = ', '.join(to_recepients_list)
    msg['Subject'] = subject

    # Body: Intro
    body1 = (
        f"Report všech položek "+purpose_context+" naleznete v příloze tohoto emailu.\n\n"
        f" \n\n"
    )
    msg.attach(MIMEText(body1))

    files_path = f"{path.dirname(path.realpath(__file__))}\\temp_{purpose}"
    files = [f for f in listdir(files_path) if path.isfile(path.join(files_path, f))]

    for file in files:
        with open(f"{files_path}\\{file}", "rb") as fil:
            if purpose in file:
                part = MIMEApplication(
                    fil.read(),
                    Name=path.basename(file)
                )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % path.basename(file)
        msg.attach(part)

    with SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, mail_app_password)
        for recepient in recepients_list:
            smtp.sendmail(from_addr=smtp_username, to_addrs=recepient, msg=msg.as_string())


    print(f"PY: Email has been sent successfully.", flush=True)

    return 0


# Create a file if does not exist in the current file directory
def create_file(output_directory, file_name, directory="database"):
    file_gen_name = file_name
    create_dir_if_noexist(f"{output_directory}\\{directory}")
    file_gen_fullpath = f"{output_directory}\\{directory}\\{file_gen_name}"
    print(f"PY: New file {file_gen_name} created: {file_gen_fullpath}", flush=True)
    file_gen_line = open(file_gen_fullpath, 'w', encoding="utf-8-sig")
    file_gen_line.close()


# Function to get already searched urls from files in the current file directory
def get_data_from_file(file_name, directory="database"):
    try:
        print(f"PY: Getting data from CSV files...")
        target_properties_details = [] # Try not global this time
        output_directory = path.dirname(path.realpath(__file__))
        create_dir_if_noexist(f"{output_directory}\\{directory}")
        file_gen_fullpath = f"{output_directory}\\{directory}\\{file_name}"

        target_properties_details = list(
            map(lambda set : set.to_list(), read_csv(
                source=file_gen_fullpath, 
                has_header=True,
                columns=['Active', 'Date Added', 'Last Active' , 'URL', 'Price', 'ZIP', 'City', 'Disposition', 'Details'], 
                encoding="utf-8-sig",
                separator=',',
                dtypes={
                    'Active': Utf8,
                    'Date Added': Utf8,
                    'Last Active': Utf8,
                    'URL': Utf8,
                    'Price': Utf8,
                    'ZIP': Utf8,
                    'City': Utf8,
                    'Disposition': Utf8,
                    'Details': Utf8
                })
                .with_columns(col(["Active"]).str.replace_all('A', 'X',))
                .transpose()
                .get_columns()
        ))

    except Exception as e:
        print(f"PY: ErrorHandler: Detected Error: {e}. Creating a file", flush=True)
        create_file(output_directory, file_name, directory)
    
    print(f"PY: Getting data from CSV files DONE.", flush=True)
    return target_properties_details


# Function to search for the pattern in a web page
def get_details(url, advertised_property_details, new_target_properties_details_queue, process_id):

    try:
        searched_property_details = ""
        response = requests_get(url=url, headers=agent)
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
                print(f"PY: Process {process_id}: New item: {advertised_property_details}", flush=True)


    except ValueError as e:
        print(f"Error while processing {url}: {e}", flush=True)


# Function to search for the pattern in a web page
def search_in_page(url, all_target_properties_details, new_target_properties_details_queue, process_id):
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
        response = requests_get(url=url, headers=agent)
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
                                            print(f"PY: Skip: {mask_char_values_in_string(all_target_properties_detail[3], -mask)}", flush=True)
                                            visited = True
                                            break

                                    if visited == True: 
                                        break

                                if visited == False:
                                    get_details(
                                        website_url_root+advertised_property_details[3], 
                                        advertised_property_details,
                                        new_target_properties_details_queue,
                                        process_id)

        # Returns 1 if on the last page, else 0 to proceed to the next page
        if advertisements == 0: 
            advertisements_done[process_id] = 1
            return 1
        advertisements_done[process_id] = 0
        return 0

    except ValueError as e:
        print(f"Error while processing {url}: {e}", flush=True)



async def search_in_page_async(url, all_target_properties_details, new_target_properties_details_queue, process_id, client):
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

        response = await client.get(url)
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
                                            print(f"PY: Process {process_id}: Skip: {mask_char_values_in_string(all_target_properties_detail[3], -mask)}", flush=True)
                                            visited = True
                                            break

                                    if visited == True: 
                                        break

                                if visited == False:
                                    get_details(
                                        website_url_root+advertised_property_details[3], 
                                        advertised_property_details,
                                        new_target_properties_details_queue,
                                        process_id)

        # Returns 1 if on the last page, else 0 to proceed to the next page
        if advertisements == 0: 
            advertisements_done[process_id] = 1
            return 1
        advertisements_done[process_id] = 0
        return 0

    except ValueError as e:
        print(f"Error while processing {url}: {e}", flush=True)



def check_if_active_property_thread(all_target_property_detail, all_target_properties_detail_queue, this_mask):
    try:
        response = requests_get(url=mask_char_values_in_string(all_target_property_detail[3], -1*this_mask), headers=agent)
        if response.status_code == 200:
            page_content = response.text

            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(page_content, "html.parser")
            try:
                # If the advertised property webside contains class 'nadpisdetail' header, then it is still active
                if str(soup.find_all("h1", {"class": "nadpisdetail"})).replace("<h1 class=\"nadpisdetail\">","").replace("</h1>","") != str([]):
                    all_target_property_detail[0] = "A"
                    all_target_property_detail[2] = str(datetime.now(ZoneInfo(zone_info)).date().strftime("%d.%m.%Y")) # Override Last Active Time
                else:
                    # Do not update all_target_property_detail, report inactive
                    print(f"PY: Inactive: {mask_char_values_in_string(all_target_property_detail[3], -1*this_mask)}", flush=True)
            except:
                # Do not update all_target_property_detail, report inactive
                print(f"PY: Inactive: {mask_char_values_in_string(all_target_property_detail[3], -1*this_mask)}", flush=True)

    except ValueError as e:
        print(f"PY: check_if_active_property_thread: Error while processing: {all_target_property_detail[3]}: {e}", flush=True)
        print(f"PY: check_if_active_property_thread: DEBUG: all_target_property_detail = {all_target_property_detail}", flush=True)

    all_target_properties_detail_queue.put(all_target_property_detail.copy())



async def check_if_active_property_thread_async(all_target_property_detail, all_target_properties_detail_queue, this_mask, client):
    try:
        response = await client.get(mask_char_values_in_string(all_target_property_detail[3], -1*this_mask))
        if response.status_code == 200:
            page_content = response.text

            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(page_content, "html.parser")
            try:
                # If the advertised property webside contains class 'nadpisdetail' header, then it is still active
                if str(soup.find_all("h1", {"class": "nadpisdetail"})).replace("<h1 class=\"nadpisdetail\">","").replace("</h1>","") != str([]):
                    all_target_property_detail[0] = "A"
                    all_target_property_detail[2] = str(datetime.now(ZoneInfo(zone_info)).date().strftime("%d.%m.%Y")) # Override Last Active Time
                else:
                    # Do not update all_target_property_detail, report inactive
                    print(f"PY: Inactive: {mask_char_values_in_string(all_target_property_detail[3], -1*this_mask)}", flush=True)
            except:
                # Do not update all_target_property_detail, report inactive
                print(f"PY: Inactive: {mask_char_values_in_string(all_target_property_detail[3], -1*this_mask)}", flush=True)

    except ValueError as e:
        print(f"PY: check_if_active_property_thread: Error while processing: {all_target_property_detail[3]}: {e}", flush=True)
        print(f"PY: check_if_active_property_thread: DEBUG: all_target_property_detail = {all_target_property_detail}", flush=True)

    all_target_properties_detail_queue.put(all_target_property_detail.copy())



def check_for_active_urls_threaded(all_target_properties_details, this_mask=mask):
    # global all_target_properties_details
    print(f"PY: Checking for active URLs...", flush=True)
    threads_all_target_properties_details = [[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_len =[[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_queue = [[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_indices = [[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_indices_len = [[] for i in range(len(all_target_properties_details))]

    for i, all_target_properties_detail in enumerate(all_target_properties_details):
        for pos, all_target_property_detail in enumerate(all_target_properties_detail):
            # Skip whether or not the item is active if it has been inactive for two days, otherwise check newer/active ones
            if datetime.strptime(all_target_property_detail[2], "%d.%m.%Y") >= (datetime.today() - timedelta(days=2)):
                threads_all_target_properties_details_indices[i].append(pos)
                threads_all_target_properties_details_queue[i].append(Queue())
                threads_all_target_properties_details[i].append(Thread(
                    target=check_if_active_property_thread, 
                    args=(all_target_property_detail,
                          threads_all_target_properties_details_queue[i][-1],this_mask,)))
                threads_all_target_properties_details[i][-1].start()

        threads_all_target_properties_details_indices_len[i] = len(threads_all_target_properties_details_indices[i])
        threads_all_target_properties_details_len[i] = len(threads_all_target_properties_details[i])
        [threads_all_target_properties_details[i][j].join() for j in range(threads_all_target_properties_details_len[i])]


    # Update the values after running multiple threads based on the content in the queue
    for i, all_target_properties_detail in enumerate(all_target_properties_details):
        for j in range(threads_all_target_properties_details_indices_len[i]):
            all_target_properties_detail[threads_all_target_properties_details_indices[i][j]] = threads_all_target_properties_details_queue[i][j].get()

        
    print(f"PY: Checking for active URL DONE.", flush=True)
    return all_target_properties_details



async def check_for_active_urls_threaded_async(all_target_properties_details, this_mask=mask):
    # global all_target_properties_details
    print(f"PY: Checking for active URLs...", flush=True)
    threads_all_target_properties_details_queue = [[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_indices = [[] for i in range(len(all_target_properties_details))]
    threads_all_target_properties_details_indices_len = [[] for i in range(len(all_target_properties_details))]

    for i, all_target_properties_detail in enumerate(all_target_properties_details):
        for position_in_database, all_target_property_detail in enumerate(all_target_properties_detail):
            # Skip whether or not the item is active if it has been inactive for two days, otherwise check newer/active ones
            if datetime.strptime(all_target_property_detail[2], "%d.%m.%Y") >= (datetime.today() - timedelta(days=2)):
                threads_all_target_properties_details_indices[i].append(position_in_database)
                threads_all_target_properties_details_queue[i].append(Queue())

        async with AsyncClient() as client:
            await gather(
                *[check_if_active_property_thread_async(
                    all_target_properties_detail[position_in_database],
                    threads_all_target_properties_details_queue[i][item_in_list],
                    this_mask,
                    client)
                  for item_in_list, position_in_database in enumerate(threads_all_target_properties_details_indices[i])]
            )
        threads_all_target_properties_details_indices_len[i] = len(threads_all_target_properties_details_indices[i])


    # Update the values after running multiple threads based on the content in the queue
    for i, all_target_properties_detail in enumerate(all_target_properties_details):
        for j in range(threads_all_target_properties_details_indices_len[i]):
            threads_all_target_properties_details_indices[i]
            all_target_properties_detail[threads_all_target_properties_details_indices[i][j]] = threads_all_target_properties_details_queue[i][j].get()

        
    print(f"PY: Checking for active URL DONE.", flush=True)
    return all_target_properties_details



# Sort the databases from the newest to the oldest added item
def sort_list_by_date(all_target_properties_details):
    # global all_target_properties_details
    print(f"PY: Sorting list by time added...", flush=True)
    for all_target_properties_detail in all_target_properties_details:
        all_target_properties_detail.sort(key=lambda x: datetime.strptime(x[1], "%d.%m.%Y"), reverse=True)
    print(f"PY: Sorting list by time added DONE.", flush=True)

    return all_target_properties_details


# Write the content to the respective output files
def write_content_to_output_files(file_prefix, all_target_properties_details, directory="database"):
    print(f"PY: Writing data to CSV files...", flush=True)

    # Using len() and indices is 15 seconds faster than for _ in _ method in the first for loop
    search_dispositions_list_len = len(search_dispositions_list)
    output_directory = path.dirname(path.realpath(__file__))
    for i in range(search_dispositions_list_len):
        file_gen_name = file_prefix+'_'+search_dispositions_list[i][0]+'.csv'
        create_dir_if_noexist(f"{output_directory}\\{directory}")
        file_gen_fullpath = f"{output_directory}\\{directory}\\{file_gen_name}"

        DataFrame(all_target_properties_details[i],
                     schema=['Active', 'Date Added', 'Last Active' , 'URL', 'Price', 'ZIP', 'City', 'Disposition', 'Details']
                     ).write_csv(
            file=file_gen_fullpath, 
            include_header=True,
            separator=',',
        )

    # Reset the list content to empty list of lists and free memory
    all_target_properties_details = [[] for i in search_dispositions_list]

    print(f"PY: Writing data to CSV files DONE.", flush=True)


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
    print("PY: Update all target properties database list...", flush=True)
    new_target_properties_details = [[] for i in search_dispositions_list]
    while not new_target_properties_details_queue.empty():
        # Get one item from the queue holding information about the new property
        new_target_properties_detail = new_target_properties_details_queue.get()

        # Sort to the corresponding disposition bucket
        for i, (search_disposition) in enumerate(search_dispositions_list):
            if (search_disposition[0] == new_target_properties_detail[7]):
                new_target_properties_details[i].append(new_target_properties_detail.copy())

                # Mask sensitive/personal information to create ambiguity, save to csv database
                new_target_properties_detail[3] = mask_char_values_in_string(new_target_properties_detail[3], mask)
                new_target_properties_detail[5] = mask_char_values_in_string(new_target_properties_detail[5], mask)
                new_target_properties_detail[6] = mask_char_values_in_string(new_target_properties_detail[6], mask)
                all_target_properties_details[i].append(new_target_properties_detail.copy())

    print("PY: Update all target properties database list DONE.", flush=True)
    return all_target_properties_details, new_target_properties_details


def find_new_and_update_all_properties_from_websites(
        threads_count, all_target_properties_details, website_substring, process_id):

    # Start the search from the initial URL, loop until there is at least one advertisement
    print(f"PY: Getting data from website...", flush=True)
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
            process_id
        )
    ))
    threads_page[-1].start()

    # Main loop for properties search
    timer_start = time()
    max_timer_break = 60
    max_scan_pages_break = 200
    while advertisements_done[int(process_id)] == 0:

        # Start threads
        for page in range(min_scan_pages, max_scan_pages):
            threads_page.append(Thread(
                target=search_in_page, 
                args=(
                    f"{website_url_root}{website_substring}{page*20}/{search_requirements}",
                    all_target_properties_details,
                    new_target_properties_details_queue,
                    process_id
                )
            ))
            threads_page[-1].start()

        # Wait for threads to complete tasks
        threads_page_len = len(threads_page)
        [threads_page[i].join() for i in range (threads_page_len)]

        current_time = time()-timer_start
        print(f"PY: Process {process_id}: Searching on pages {min_scan_pages}-{max_scan_pages} done. Timer: {current_time}", flush=True)

        if advertisements_done[process_id] == 1:
            print(f"PY: Process {process_id}: Reached the last page. Break.", flush=True)
            break
        elif current_time > max_timer_break:
            print(f"PY: Process {process_id}: Maximum timer value reached. Break.", flush=True)
            break
        elif max_scan_pages >= max_scan_pages_break:
            print(f"PY: Process {process_id}: Maximum limit of pages to scan reached. Break.", flush=True)
            break
            

        min_scan_pages += threads_count
        max_scan_pages += threads_count


    threads_page = []
    advertisements_done[process_id] = 0
    print(f"PY: Getting data from website DONE.", flush=True)

    all_target_properties_details, new_target_properties_details = append_all_new_properties(
        new_target_properties_details_queue, 
        all_target_properties_details)

    return all_target_properties_details, new_target_properties_details



async def find_new_and_update_all_properties_from_websites_async(
        threads_count, all_target_properties_details, website_substring, process_id):
    
    # Start the search from the initial URL, loop until there is at least one advertisement
    print(f"PY: Getting data from website...", flush=True)
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
            process_id
        )
    ))
    threads_page[-1].start()
    

    # Main loop for properties search
    timer_start = time()
    max_timer_break = 60
    max_scan_pages_break = 200
    while advertisements_done[int(process_id)] == 0:

        # Start async threads
        async with AsyncClient() as client:
            await gather(
                *[search_in_page_async(
                    f"{website_url_root}{website_substring}{page*20}/{search_requirements}",
                    all_target_properties_details,
                    new_target_properties_details_queue,
                    process_id,
                    client)
                  for page in range(min_scan_pages, max_scan_pages)]
            )

        # Wait for threads to complete tasks
        if (threads_page_len := len(threads_page)) != 0:
            [threads_page[i].join() for i in range(threads_page_len)]

        current_time = time()-timer_start
        print(f"PY: Process {process_id}: Searching on pages {min_scan_pages}-{max_scan_pages} done. Timer: {current_time}", flush=True)

        if advertisements_done[process_id] == 1:
            print(f"PY: Process {process_id}: Reached the last page. Break.", flush=True)
            break
        elif current_time > max_timer_break:
            print(f"PY: Process {process_id}: Maximum timer value reached. Break.", flush=True)
            break
        elif max_scan_pages >= max_scan_pages_break:
            print(f"PY: Process {process_id}: Maximum limit of pages to scan reached. Break.", flush=True)
            break

        min_scan_pages += threads_count
        max_scan_pages += threads_count


    threads_page = []
    advertisements_done[process_id] = 0
    print(f"PY: Getting data from website DONE.", flush=True)

    all_target_properties_details, new_target_properties_details = append_all_new_properties(
        new_target_properties_details_queue, 
        all_target_properties_details)

    return all_target_properties_details, new_target_properties_details



def main_execution_flow(
        file_purpose_keyword, mail_purpose_occurrence_in_context_keyword, website_substring, search_threads_count, process_id, cpu_affinity=None):

    # This process is supposed to be executed on a separate core defined by cpu_affinity. Check affinity, assign the process to this core altering the affinity.
    if cpu_affinity != None:
        this_process = psutil_Process()
        print(f'PY: Process #{process_id}: {this_process}, affinity {this_process.cpu_affinity()}', flush=True)
        this_process.cpu_affinity([cpu_affinity])
        print(f'PY: Process #{process_id}: Set affinity to {cpu_affinity}, affinity now {this_process.cpu_affinity()}', flush=True)

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
        process_id
    )

    # Sort newly added items by date
    all_target_properties_details = sort_list_by_date(all_target_properties_details)

    # Update output CSV database files
    write_content_to_output_files(f'{file_purpose_keyword}', all_target_properties_details)   

    # Send email if new properties have been detected
    send_email(f"{mail_purpose_occurrence_in_context_keyword}", recepients_list, new_target_properties_details)


def main_execution_flow_async(
        file_purpose_keyword, mail_purpose_occurrence_in_context_keyword, website_substring, search_threads_count, process_id, cpu_affinity=None):

    # This process is supposed to be executed on a separate core defined by cpu_affinity. Check affinity, assign the process to this core altering the affinity.
    if cpu_affinity != None:
        this_process = psutil_Process()
        print(f'PY: Process #{process_id}: {this_process}, affinity {this_process.cpu_affinity()}', flush=True)
        this_process.cpu_affinity([cpu_affinity])
        print(f'PY: Process #{process_id}: Set affinity to {cpu_affinity}, affinity now {this_process.cpu_affinity()}', flush=True)

    # Create an array of output files if noexist and get data from them
    all_target_properties_details = [[] for i in search_dispositions_list]
    for i, search_disposition in enumerate(search_dispositions_list):
        all_target_properties_details[i] = get_data_from_file(f'{file_purpose_keyword}_{search_disposition[0]}.csv')

    # Check if logged URLs are still active (Launch asynchronous thread)
    all_target_properties_details = run(check_for_active_urls_threaded_async(all_target_properties_details))

    # Start the search from the initial URL, loop until there is at least one advertisement
    all_target_properties_details, new_target_properties_details = run(
        find_new_and_update_all_properties_from_websites_async(
            search_threads_count,
            all_target_properties_details, 
            f"{website_substring}",
            process_id)
    )

    # Sort newly added items by date
    all_target_properties_details = sort_list_by_date(all_target_properties_details)

    # Update output CSV database files
    write_content_to_output_files(f'{file_purpose_keyword}', all_target_properties_details)   

    # Send email if new properties have been detected
    send_email(f"{mail_purpose_occurrence_in_context_keyword}", recepients_list, new_target_properties_details)


def unmask_database_items(file_purpose_keyword):
    # Create an array of output files if noexist and get data from them
    all_target_properties_details = [[] for i in search_dispositions_list]
    for i, search_disposition in enumerate(search_dispositions_list):
        all_target_properties_details[i] = get_data_from_file(
            f'{file_purpose_keyword}_{search_disposition[0]}.csv')
        
        # Unmask
        for all_target_properties_detail in all_target_properties_details[i]:
            all_target_properties_detail[3] = mask_char_values_in_string(all_target_properties_detail[3], -mask)
            all_target_properties_detail[5] = mask_char_values_in_string(all_target_properties_detail[5], -mask)
            all_target_properties_detail[6] = mask_char_values_in_string(all_target_properties_detail[6], -mask)

    return all_target_properties_details