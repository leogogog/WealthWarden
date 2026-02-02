
# reproduce_issue.py
import os

def test_prompt_structure():
    print("Checking file content matches expected prompt structure...")
    try:
        with open("services/ai_service.py", "r") as f:
            content = f.read()
            # Check for key phrases in the new prompt
            if 'OUTPUT_FORMAT (JSON ONLY):' in content and 'CASE 1: RECORD' in content and '"intent": "RECORD"' in content:
                print("SUCCESS: Prompt seems to contain JSON instructions.")
            else:
                print("FAILURE: Prompt instructions missing.")
                exit(1)
    except Exception as e:
        print(f"Error checking file: {e}")
        exit(1)

if __name__ == "__main__":
    test_prompt_structure()
