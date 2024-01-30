# Efficient Property Listing Scraping with Multithreading and Multiprocessing on Github Actions

This code efficiently scrapes property listings from a website using multiple threads and/or processes to improve performance. It also maintains data integrity by tracking visited URLs and anonymizing sensitive information.

It is designed and optimized for execution times under 1 minute per run on Github Actions.


## Overall Features

* Efficiently scrapes new listings.
* Leverages multiple processes and threads for faster scraping.
* Maintains data integrity with visited URLs tracking.
* Masks sensitive information for privacy.


## Process Workflow

1. Assign each job to the least utilized processor core.
2. Load unmasked data from database files to a multidimensional list and check which listings are still active.
3. Scan for new website listings until the last one detected in the previous Github Actions run.
4. Append new listings to the list and sort all listings by date added.
5. Mask sensitive information for privacy and save to respective database files.
6. Send an email to all recepients if new listings were detected.
7. Send a weekly report with all csv database files attached for review.


## Key Functions

| Function | Description |
|---|---|
| `get_data_from_file()` | Handling data loading from local CSV files using Polars CSV reader, and set all listings to inactive (X). |
| `check_for_active_urls_threaded_async()` | Sets listings to active (A) by visiting the stored URLs. |
| `find_new_and_update_all_properties_from_websites()` | Search for new listings until a known URL has been detected. |
| `append_all_new_properties()` | Anonymize and append all new listings. |
| `sort_list_by_date()` | Sort all listings by date added. |
| `write_content_to_output_files()` | Update locally stored CSV database files with new listings details using Polars CSV writer. |
| `send_email()` | Send an email in case new listings have been detected. |
| `send_report_email()` | Send a report email to all email recepients. |
