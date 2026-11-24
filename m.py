from loader import generate_sample_files, load_inventory, load_requests
from allocater import allocate_blood
from reporter import write_reports


def main():
    generate_sample_files()
    inventory = load_inventory("inventory.csv")
    requests = load_requests("requests.csv")
    results = allocate_blood(inventory, requests)
    report_text = write_reports(results)
    print(report_text)


if __name__ == "__main__":
    main()