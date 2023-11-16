import requests
import os
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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


# Note: Only APPEND new items at the end of the list, do not insert anything in the middle or beginning of the list
search_dispositions_list = [
    ["1+1","1 + 1"],
    ["2+1","2 + 1"],
    ["3+1","3 + 1"],
    ["1+kk","1 + kk"],
    ["2+kk","2 + kk"],
    ["3+kk","3 + kk"]
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
    "plastová okna"
]

# A set to keep track of visited URLs to avoid infinite loops
advertised_property_details = ['A', 0, 0, 0, 0, 0, 0, 0]
all_target_properties_details = [[] for i in search_dispositions_list]
new_target_properties_details = [[] for i in search_dispositions_list]


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
            if new_target_property_detail[6] in search_dispositions_list[i][0]:
                body2 += f"{new_target_property_detail[6]}, {new_target_property_detail[5]} {new_target_property_detail[4]}, přidáno dne {new_target_property_detail[1]}:\n"
                body2 += f"Odkaz: {new_target_property_detail[2]}\n"
                body2 += f"Detaily: {new_target_property_detail[3]} Kč {new_target_property_detail[7]}\n"
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
    file_gen_fullpath = f"{output_directory}\\{file_gen_name}"
    print(f"PY: New file {file_gen_name} created: {file_gen_fullpath}")
    file_gen_line = open(file_gen_fullpath, 'w', encoding="utf-8-sig")
    file_gen_line.close()


# Function to get already searched urls from files in the current file directory
def get_data_from_file(file_name):
    try:
        global all_target_properties_details
        output_directory = os.path.dirname(os.path.realpath(__file__))
        file_gen_fullpath = f"{output_directory}\\{file_name}"

        for i, search_disposition in enumerate(search_dispositions_list):
            if (file_name.split("_")[1].replace(".csv","") in search_disposition[0]):
                all_target_properties_details[i] = pd.read_csv(
                    file_gen_fullpath, 
                    encoding="utf-8-sig",
                    sep = ',', header=None, 
                    names=['Active', 'Date', 'URL', 'Price', 'ZIP', 'City', 'Disposition', 'Detail'], 
                    dtype={
                        'Active': 'string',
                        'Date': 'string',
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



# Function to search for the pattern in a web page
def get_details(url):

    try:
        searched_property_details = ""
        global advertised_property_details
        response = requests.get(url)
        if response.status_code == 200:
            page_content = response.text

            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(page_content, "html.parser")
            header = str(soup.find_all("h1", {"class": "nadpisdetail"})).replace("<h1 class=\"nadpisdetail\">","").replace("</h1>","")
            details = str(soup.find_all("div", {"class": "popisdetail"})).replace("<div class=\"popisdetail\">","").replace("</div>","")

            # Search for the target disposition keyword in the page content
            target_disposition = False
            for search_disposition in search_dispositions_list:
                # Search in header
                if (search_disposition[0] in header) or (search_disposition[1] in header):
                    target_disposition = True
                    advertised_property_details[6] = search_disposition[0]
                    break

                # Search in description
                elif (search_disposition[0] in details) or (search_disposition[1] in details):
                    target_disposition = True
                    advertised_property_details[6] = search_disposition[0]
                    break

            # If target disposition found:
            if target_disposition == True:

                # Get Keywords about the property
                for search_detail in search_details:
                    if search_detail in page_content:
                        # Faster method than using StringIO on smaller strings
                        searched_property_details += f"|  {search_detail}  "
                advertised_property_details[7] = searched_property_details

                # Get date added
                date_added = str(soup.find_all("span", {"class": "velikost10"})[0]).replace("<span class=\"velikost10\">","").replace("</span>","").replace(" ", "").split('-[')[1].replace("]", "")
                advertised_property_details[1] = datetime.strptime(date_added, "%d.%m.%Y").date().strftime("%d.%m.%Y")

                # Announce new advertised property
                print(f"PY: New item: {advertised_property_details}")

                # Store the item to the respective disposition slot
                global all_target_properties_details
                global new_target_properties_details
                for i, (search_disposition, all_target_properties_detail) in enumerate(zip(search_dispositions_list, all_target_properties_details)):
                    if (search_disposition[0] == advertised_property_details[6]):
                        advertised_property_details[2] = website_url_root+advertised_property_details[2]
                        new_target_properties_details[i].append(advertised_property_details.copy())

                        # Remove or trim sensitive/personal information to create ambiguity, save to csv database
                        advertised_property_details[2] = advertised_property_details[2].replace(website_url_root, '')
                        advertised_property_details[4] = advertised_property_details[4].split(" ")[1]
                        for i, city in enumerate(search_cities_list):
                            if advertised_property_details[5] in city:
                                advertised_property_details[5] = i
                                break
                        all_target_properties_detail.append(advertised_property_details.copy())
                        break


    except ValueError as e:
        print(f"Error while processing {url}: {e}")

    return None


# Function to search for the pattern in a web page
def search_in_page(url):

    try:
        global advertised_property_details
        global all_target_properties_details
        response = requests.get(url)
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
                            advertised_property_details[2] = line.replace("<div class=\"inzeratynadpis\"><a href=\"", "").split("\">",1)[0]

                        elif line.startswith("<div class=\"inzeratycena\">"):
                            advertised_property_details[3] = line.replace("<div class=\"inzeratycena\"><b>", "").replace("</b></div>", "").replace("Kč", "").replace(" ", "")

                        elif line.startswith("<div class=\"inzeratylok\">"):
                            area = line.replace("<div class=\"inzeratylok\">", "").replace("</div>", "").split("<br/>", 2)
                            advertised_property_details[4] = area[1]
                            advertised_property_details[5] = area[0]
                            if area[0] in search_cities_list:
                                # Check if URL not visited before
                                visited = False

                                # Using len() and indices is 15 seconds faster than for _ in _ method in the first for loop
                                search_dispositions_list_len = len(search_dispositions_list)
                                for i in range(search_dispositions_list_len):
                                    for all_target_properties_detail in all_target_properties_details[i]:

                                        # Use short-circuit evaluation and utilize the and operation to 'fail the condition faster'
                                        if (all_target_properties_detail[0] != "A") \
                                            and (advertised_property_details[2] in all_target_properties_detail[2]):

                                            # Mark as Active and set visited flag to True
                                            all_target_properties_detail[0] = 'A'
                                            print(f"PY: Skip visited: {advertised_property_details[2]}")
                                            visited = True
                                            break

                                    if visited == True: 
                                        break


                                if visited == False:
                                    get_details(website_url_root+advertised_property_details[2])

        # Returns 1 if on the last page, else 0 to proceed to the next page
        if advertisements == 0: 
            return 1
        return 0

    except ValueError as e:
        print(f"Error while processing {url}: {e}").encode('utf-8-sig')


# Sort the databases from the newest to the oldest added item
def sort_list_by_date():
    global all_target_properties_details
    print(f"PY: Sorting list by time added...")
    for all_target_properties_detail in all_target_properties_details:
        all_target_properties_detail.sort(key=lambda x: datetime.strptime(x[1], "%d.%m.%Y"), reverse=True)



# Write the content to the respective output files
def write_content_to_output_files(file_prefix):
    global all_target_properties_details

    # Using len() and indices is 15 seconds faster than for _ in _ method in the first for loop
    search_dispositions_list_len = len(search_dispositions_list)
    output_directory = os.path.dirname(os.path.realpath(__file__))
    for i in range(search_dispositions_list_len):
        file_gen_name = file_prefix+'_'+search_dispositions_list[i][0]+'.csv'
        file_gen_fullpath = ('{0}{1}{2}'.format(output_directory, "\\", file_gen_name))

        pd.DataFrame(all_target_properties_details[i]).to_csv(
            path_or_buf=file_gen_fullpath, 
            sep = ',', header=None, 
            encoding="utf-8-sig", 
            index=False
        )

    # Reset the list content to empty list of lists and free memory
    all_target_properties_details = [[] for i in search_dispositions_list]



def main():

    max_scan_pages = 1400 # Temporary solution

    # ----------------------------------------------------------------------------
    #                             PROPERTIES FOR SALE
    # ----------------------------------------------------------------------------
    # Create an array of output files if noexist and get data from them
    for search_disposition in search_dispositions_list:
        get_data_from_file(f'prodej_{search_disposition[0]}.csv')


    # Start the search from the initial URL, loop until there is at least one advertisement
    search_in_page(f"{website_url_root}/prodam/byt/{search_requirements}")
    advertisements_done = 0
    page = 1
    while (advertisements_done == 0) and (page*20 <= max_scan_pages):
        advertisements_done = search_in_page(f"{website_url_root}/prodam/byt/{page*20}/{search_requirements}")
        page = page + 1

    sort_list_by_date()
    write_content_to_output_files(f'prodej')
    send_email('k prodeji', recepients_list)


    # ----------------------------------------------------------------------------
    #                             PROPERTIES FOR RENT
    # ----------------------------------------------------------------------------
    # Create an array of output files if noexist and get data from them
    for search_disposition in search_dispositions_list:
        get_data_from_file(f'pronajem_{search_disposition[0]}.csv')


    # Start the search from the initial URL, loop until there is at least one advertisement
    search_in_page(f"{website_url_root}/pronajmu/byt/{search_requirements}")
    advertisements_done = 0
    page = 1
    while (advertisements_done == 0) and (page*20 <= max_scan_pages):
        advertisements_done = search_in_page(f"{website_url_root}/pronajmu/byt/{page*20}/{search_requirements}")
        page = page + 1

    sort_list_by_date()
    write_content_to_output_files(f'pronajem')
    send_email('k pronájmu', recepients_list)


if __name__ == '__main__':
    main()



