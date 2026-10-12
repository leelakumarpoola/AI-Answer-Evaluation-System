import re

text_qp = """
Q1. Explain blockchain architecture.
10 Marks

Q2 Describe consensus mechanisms.
Marks: 15

Question 3 Explain smart contracts.
(20)

4. Question four.
5) Question five.
"""

def test_regex():
    # Matches Q1, Question 1, 1., 1)
    pattern = r'(?:^|\n)(?:Q|Question No\.? |Question )?(\d+(?:\([a-z]\))?)[\.\)]?\s*(.*?)(?=(?:(?:^|\n)(?:Q|Question No\.? |Question )?\d+(?:\([a-z]\))?[\.\)]?)|$)'
    
    # stricter:
    pattern = r'(?:^|\n)(?:Q(\d+(?:\([a-z]\))?)[\.\)]?|Question No\.? (\d+(?:\([a-z]\))?)[\.\)]?|Question (\d+(?:\([a-z]\))?)[\.\)]?|(\d+(?:\([a-z]\))?)[\.\)])\s*(.*?)(?=(?:(?:^|\n)(?:Q\d+|Question No\.? \d+|Question \d+|\d+[\.\)]))|$)'
    
    print("=== Question Paper ===")
    matches = re.finditer(pattern, text_qp, re.IGNORECASE | re.DOTALL)
    for match in matches:
        q_num = (match.group(1) or match.group(2) or match.group(3) or match.group(4)).strip()
        q_content = match.group(5).strip()
        marks_match = re.search(r'(\d+)\s*[Mm]arks?|[Mm]arks?:\s*(\d+)|\((\d+)\)', q_content)
        max_marks = marks_match.group(1) or marks_match.group(2) or marks_match.group(3) if marks_match else 0
        q_text = re.sub(r'(\d+)\s*[Mm]arks?|[Mm]arks?:\s*(\d+)|\((\d+)\)', '', q_content).strip()
        print(f"Num: {q_num}, Marks: {max_marks}, Text: {q_text}")

if __name__ == "__main__":
    test_regex()
