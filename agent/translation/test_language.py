from agent.translation.language_detector import detect_language


test_cases = [
    {
        "name": "English Invoice",
        "text": "Invoice Number INV-101. Total Amount 1500 USD."
    },
    {
        "name": "German Invoice",
        "text": "Rechnungsnummer INV-102. Gesamtbetrag 1500 Euro."
    },
    {
        "name": "Spanish Invoice",
        "text": "Numero de factura INV-103. Importe total 1500 euros."
    },
    {
        "name": "French Invoice",
        "text": "Numero de facture INV-104. Montant total 1500 euros."
    }
]


for test in test_cases:

    print("\n------------------------------")
    print("Testing:", test["name"])

    result = detect_language(test["text"])

    print("Input:", test["text"])
    print("Result:", result)