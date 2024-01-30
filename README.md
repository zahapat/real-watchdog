# Efficient Property Listing Scraping with Multithreading and Multiprocessing on GitHub Actions

This code efficiently scrapes property listings from a website using multiple threads and/or processes to improve performance. It also maintains data integrity by tracking visited URLs and anonymizing sensitive information.

It is designed and optimized for execution times under 1 minute per run on Github Actions.


## Overall Features

* Efficiently scrapes new listings.
* Leverages multiple processes and threads for faster scraping.
* Maintains data integrity with visited URLs tracking.
* Masks sensitive information for privacy.


## Process Workflow

1. Assign jobs to the least utilized processor cores.
2. Load unmasked data from all local database files to a multidimensional list, and check which listings are active.
3. Scan for new listings starting from the last one detected in the previous Github Actions run.
4. Append freshly added listings to the list and sort all listings by the date they were added.
5. Mask potentially sensitive information for privacy and save all items to respective database files.
6. Send an email to all recepients if new listings are discovered.
7. Compile a weekly report with all CSV database files attached for review.


## Key Functions

| Function | Description |
|---|---|
| `get_data_from_file()` | Handling data loading from local CSV files using Polars CSV reader, and set all listings to inactive (X). |
| `check_for_active_urls_threaded_async()` | Sets listings to active (A) by visiting the stored URLs. |
| `find_new_and_update_all_properties_from_websites()` | Searches for new listings until it encounters a URL that has been previously scraped. |
| `append_all_new_properties()` | Anonymize and append all new listings. |
| `sort_list_by_date()` | Arranges all listings in ascending order based on the date they were added. |
| `write_content_to_output_files()` | Update locally stored CSV database files with new listings details using Polars CSV writer. |
| `send_email()` | Sends an email notification to all recipients if new listings have been detected. |
| `send_report_email()` | Generates a weekly report and sends it to all email recipients, attaching updated CSV database files for review. |
