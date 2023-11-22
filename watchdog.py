import requests
import time
import threading
import os
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import re

import smtplib
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
recepients_list = list(filter(None, os.environ["recepients_email"].split(',')))
search_cities_list = list(filter(None, str(os.environ["search_cities_list"]).split(',')))


# String envs
zone_info = os.environ["zone_info"]
smtp_server = os.environ["smtp_server"]
smtp_port = int(os.environ["smtp_port"])
smtp_username = os.environ["smtp_username"]
mail_app_password = os.environ["mail_app_password"]
website_url_root = os.environ["website_url_root"]
search_requirements = os.environ["search_requirements"]
mask = int(os.environ["mask"])


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

all_target_properties_details = [[] for i in search_dispositions_list]
new_target_properties_details = [[] for i in search_dispositions_list]
advertisements_done = 0




# Send an email
def send_email(purpose, to_recepients_list):
    global search_dispositions_list
    global new_target_properties_details

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

    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
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
        global all_target_properties_details
        output_directory = os.path.dirname(os.path.realpath(__file__))
        file_gen_fullpath = f"{output_directory}\\database\\{file_name}"

        for i, search_disposition in enumerate(search_dispositions_list):
            if (file_name.split("_")[1].replace(".csv","") in search_disposition[0]):
                all_target_properties_details[i] = pd.read_csv(
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

                break



    except Exception as e:
        # print(f"PY: ErrorHandler: Detected Error: {e}. Creating a file")
        create_file(output_directory, file_name)
    
    print(f"PY: Getting data from CSV files DONE.")



# Function to search for the pattern in a web page
def get_details(url, advertised_property_details):

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
                    or re.compile(search_disposition[1]).findall(header)):  # Regex (flexible, slower execution)
                    is_target_disposition = True
                    advertised_property_details[7] = search_disposition[0]
                    break

                # Search in description
                elif ((search_disposition[0] in details)            # String (static, faster execution)
                    or re.compile(search_disposition[1]).findall(details)):  # Regex (flexible, slower execution)
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
                print(f"PY: New item: {advertised_property_details}")

                # Store the item to the respective disposition slot
                global all_target_properties_details
                global new_target_properties_details
                for i, (search_disposition, all_target_properties_detail) in enumerate(zip(search_dispositions_list, all_target_properties_details)):
                    if (search_disposition[0] == advertised_property_details[7]):
                        advertised_property_details[3] = url
                        new_target_properties_details[i].append(advertised_property_details.copy())

                        # Mask sensitive/personal information to create ambiguity, save to csv database
                        advertised_property_details[3] = mask_char_values_in_string(advertised_property_details[3], mask)
                        advertised_property_details[5] = mask_char_values_in_string(advertised_property_details[5], mask)
                        advertised_property_details[6] = mask_char_values_in_string(advertised_property_details[6], mask)
                        all_target_properties_detail.append(advertised_property_details.copy())
                        break


    except ValueError as e:
        print(f"Error while processing {url}: {e}")

    return None


# Function to search for the pattern in a web page
def search_in_page(url):
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
        global all_target_properties_details
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
                                    get_details(website_url_root+advertised_property_details[3], advertised_property_details)

        # Returns 1 if on the last page, else 0 to proceed to the next page
        if advertisements == 0: 
            advertisements_done = 1
            return 1
        advertisements_done = 0
        return 0

    except ValueError as e:
        print(f"Error while processing {url}: {e}")


def check_if_active_property_thread(all_target_property_detail):
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
                print(f"PY: Inactive URL: {mask_char_values_in_string(all_target_property_detail[3], -mask)}")

    except ValueError as e:
        print(f"PY: Error while processing: {mask_char_values_in_string(all_target_property_detail[3], -mask)}: {e}")

    return all_target_property_detail


def check_for_active_urls_threaded():
    global all_target_properties_details
    print(f"PY: Checking for active URLs...")
    for all_target_properties_detail in all_target_properties_details:
        all_target_properties_detail_len = len(all_target_properties_detail)
        threads = [None for i in range(len(all_target_properties_detail))]
        for i, all_target_property_detail in enumerate(all_target_properties_detail):
            threads[i] = threading.Thread(target=check_if_active_property_thread, args=(all_target_property_detail,))
            threads[i].start()

        for i in range(all_target_properties_detail_len):
            threads[i].join()
    print(f"PY: Checking for active URL DONE.")


# Sort the databases from the newest to the oldest added item
def sort_list_by_date():
    global all_target_properties_details
    print(f"PY: Sorting list by time added...")
    for all_target_properties_detail in all_target_properties_details:
        all_target_properties_detail.sort(key=lambda x: datetime.strptime(x[1], "%d.%m.%Y"), reverse=True)
    print(f"PY: Sorting list by time added DONE.")



# Write the content to the respective output files
def write_content_to_output_files(file_prefix):
    print(f"PY: Writing data to CSV files...")
    global all_target_properties_details

    # Using len() and indices is 15 seconds faster than for _ in _ method in the first for loop
    search_dispositions_list_len = len(search_dispositions_list)
    output_directory = os.path.dirname(os.path.realpath(__file__))
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



def main():
    global advertisements_done

    threads_count = 1024

    # ----------------------------------------------------------------------------
    #                             PROPERTIES FOR SALE
    # ----------------------------------------------------------------------------
    # Create an array of output files if noexist and get data from them
    for search_disposition in search_dispositions_list:
        get_data_from_file(f'prodej_{search_disposition[0]}.csv')

    # Check if logged URLs are still active
    check_for_active_urls_threaded()

    # Start the search from the initial URL, loop until there is at least one advertisement
    print(f"PY: Getting data from website...")
    min_scan_pages = 1
    max_scan_pages = threads_count
    search_in_page(f"{website_url_root}/prodam/byt/{search_requirements}")
    while advertisements_done == 0:
        threads = [None for i in range(min_scan_pages, max_scan_pages)]
        for page in range(min_scan_pages, max_scan_pages):
            threads[page-min_scan_pages] = threading.Thread(
                target=search_in_page, 
                args=(f"{website_url_root}/prodam/byt/{page*20}/{search_requirements}",)
            )
            threads[page-min_scan_pages].start()

        # Wait for threads to complete tasks
        for page in range (min_scan_pages, max_scan_pages):
            threads[page-min_scan_pages].join()

        min_scan_pages = min_scan_pages + threads_count
        max_scan_pages = max_scan_pages + threads_count

        if advertisements_done == 1:
            print(f"PY: Reached the last page. Break.")
            break

    print(f"PY: Getting data from website DONE.")
    advertisements_done = 0
    print("new_target_properties_details = ", new_target_properties_details)

    sort_list_by_date()
    write_content_to_output_files(f'prodej')   
    send_email('k prodeji', recepients_list)


    # ----------------------------------------------------------------------------
    #                             PROPERTIES FOR RENT
    # ----------------------------------------------------------------------------
    # Create an array of output files if noexist and get data from them
    for search_disposition in search_dispositions_list:
        get_data_from_file(f'pronajem_{search_disposition[0]}.csv')

    # Check if logged URLs are still active
    check_for_active_urls_threaded()

    # Start the search from the initial URL, loop until there is at least one advertisement
    print(f"PY: Getting data from website...")
    min_scan_pages = 1
    max_scan_pages = threads_count
    search_in_page(f"{website_url_root}/pronajmu/byt/{search_requirements}")
    while advertisements_done == 0:
        threads = [None for i in range(min_scan_pages, max_scan_pages)]
        for page in range(min_scan_pages, max_scan_pages):
            threads[page-min_scan_pages] = threading.Thread(
                target=search_in_page, 
                args=(f"{website_url_root}/pronajmu/byt/{page*20}/{search_requirements}",)
            )
            threads[page-min_scan_pages].start()

        # Wait for threads to complete tasks
        for page in range (min_scan_pages, max_scan_pages):
            threads[page-min_scan_pages].join()
        
        min_scan_pages = min_scan_pages + threads_count
        max_scan_pages = max_scan_pages + threads_count
        
        if advertisements_done == 1:
            print(f"PY: Reached the last page. Break.")
            break

    print(f"PY: Getting data from website DONE.")
    advertisements_done = 0
    print("new_target_properties_details = ", new_target_properties_details)

    sort_list_by_date()
    write_content_to_output_files(f'pronajem')
    send_email('k pronájmu', recepients_list)


if __name__ == '__main__':
    main()



