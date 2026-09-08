import json
import urllib.request

TEXT = "send $400 to three people monthly, 80% to spend, 20% held"
req = urllib.request.Request(
    "http://127.0.0.1:8765/api/execute",
    data=json.dumps({"text": TEXT}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=20) as response:
    receipt = json.loads(response.read())
print(receipt["instruction"]["source_text"])
print("warnings", receipt["instruction"]["warnings"])
print(receipt["ok"], receipt["receipt_id"])
print(receipt["totals"])
print("verify", receipt["receipt_hash"])
