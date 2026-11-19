from agent.translation.translator import translate_to_english

text = """
Rechnungsnummer INV-101
Gesamtbetrag 1500 Euro
"""

result = translate_to_english(text, "de")

print(result)