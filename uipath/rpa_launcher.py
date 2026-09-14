import os
import requests
import webbrowser
import sys

API_URL = "http://127.0.0.1:8000"
PORTAL_URL = "http://127.0.0.1:8080"

DOWNLOAD_DIR = "uipath/downloaded_documents"


def get_next_application():
    response = requests.get(
        f"{API_URL}/api/rpa/next-application"
    )

    response.raise_for_status()

    return response.json()


def start_application(application_id):
    response = requests.post(
        f"{API_URL}/api/rpa/{application_id}/start"
    )

    response.raise_for_status()

    return response.json()


def get_documents(application_id):
    response = requests.get(
        f"{API_URL}/api/rpa/{application_id}/documents"
    )

    response.raise_for_status()

    return response.json()


def download_document(application_id, document):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    document_id = document["document_id"]
    filename = document["filename"]

    url = (
        f"{API_URL}/api/rpa/"
        f"{application_id}/documents/"
        f"{document_id}/download"
    )

    response = requests.get(url)

    response.raise_for_status()

    filepath = os.path.join(
        DOWNLOAD_DIR,
        filename
    )

    with open(filepath, "wb") as file:
        file.write(response.content)

    return filepath


def main():

    print("=" * 60)
    print("AGRICULTURAL RPA AUTOMATION ENGINE")
    print("=" * 60)

    # --------------------------------------------------
    # STEP 1 — GET NEXT APPLICATION
    # --------------------------------------------------

    print("\n[1] Checking RPA queue...")

    application = get_next_application()

    if not application.get("available"):
        print(
            "No application available for RPA processing."
        )
        sys.exit(0)

    application_id = application["application_id"]

    print(
        f"Application ID : "
        f"{application_id}"
    )

    print(
        f"Farmer         : "
        f"{application['farmer_name']}"
    )

    print(
        f"Service        : "
        f"{application['service_type']}"
    )

    print(
        f"Survey Number  : "
        f"{application['survey_number']}"
    )

    print(
        f"Village        : "
        f"{application['village']}"
    )

    print(
        f"Score          : "
        f"{application['verification_score']}"
    )


    # --------------------------------------------------
    # STEP 2 — START RPA
    # --------------------------------------------------

    print("\n[2] Starting RPA processing...")

    result = start_application(
        application_id
    )

    print(
        f"Status         : "
        f"{result['status']}"
    )


    # --------------------------------------------------
    # STEP 3 — GET DOCUMENT LIST
    # --------------------------------------------------

    print("\n[3] Retrieving supporting documents...")

    document_data = get_documents(
        application_id
    )

    documents = document_data["documents"]

    print(
        f"Documents found: "
        f"{len(documents)}"
    )


    # --------------------------------------------------
    # STEP 4 — DOWNLOAD DOCUMENTS
    # --------------------------------------------------

    print("\n[4] Downloading documents...")

    downloaded_files = []

    for document in documents:

        print(
            f"Downloading: "
            f"{document['filename']}"
        )

        filepath = download_document(
            application_id,
            document
        )

        downloaded_files.append(filepath)

        print(
            f"Saved to: "
            f"{filepath}"
        )


    # --------------------------------------------------
    # STEP 5 — DISPLAY RPA PACKAGE
    # --------------------------------------------------

    print("\n[5] RPA package ready")

    print(
        f"Application: "
        f"{application_id}"
    )

    print("Documents:")

    for filepath in downloaded_files:
        print(
            f"  - {filepath}"
        )


    # --------------------------------------------------
    # STEP 6 — OPEN GOVERNMENT PORTAL
    # --------------------------------------------------

    portal_url = (
        f"{PORTAL_URL}/"
        f"?application_id={application_id}"
    )

    print(
        "\n[6] Opening government portal..."
    )

    print(
        f"URL: {portal_url}"
    )

    webbrowser.open(
        portal_url
    )


    print(
        "\nRPA workflow started successfully."
    )


if __name__ == "__main__":
    main()

