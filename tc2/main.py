from file_lookup import get_file_info
from email_search import search_gmail
from summarizer import summarize_snippets

# Prompt user for PV #
pv_input = input("Please enter PV #: ").strip()

# Look up file details by PV #
info = get_file_info(pv=pv_input)

if info:
    print("\n✅ File Found:")
    print(f"Name: {info.get('Name')}")
    print(f"PV #: {info.get('PV #')}")
    print(f"CMS: {info.get('CMS')}")
    print(f"Date of Injury: {info.get('Date of Injury')}")

    # Prepare clean search terms
    name = info.get("Name", "").strip()
    date = info.get("Date of Injury", "").split(" ")[0]
    pv = str(info.get("PV #"))
    cms = str(info.get("CMS"))

    # Build Gmail search query
    search_terms = [
        f'"{name}"',
        pv,
        cms,
        date
    ]
    search_query = " OR ".join(filter(None, search_terms))

    print("\n🔍 Searching Gmail for:", search_query)
    snippets = search_gmail(search_query)

    print("\n📬 Email Snippets Found:")
    if snippets:
        print("📬 Email Snippets Found:\n")
        print(snippets)

        
        print("\n🧠 Generating Summary with GPT...")
        summary = summarize_snippets(snippets, info["Name"])
        print("\n📄 Summary:")
        print(summary)
    else:
        print("No emails found.")

else:
    print("❌ No file found with that PV #.")
