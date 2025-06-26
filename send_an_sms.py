from twilio.rest import Client
import json
import os
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, RECIPIENT_PHONE_NUMBER
account_sid = TWILIO_ACCOUNT_SID
auth_token = TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token)
message = client.messages.create(
  from_=TWILIO_PHONE_NUMBER,
  body='Just beleive in Allah and you will see the magic. The ultimate secret is to have faith in Allah.',
  to=RECIPIENT_PHONE_NUMBER
)
print(message.sid)

# Save all SIDs to a JSON file as a list
sid_file = "sms_sid.json"
if os.path.exists(sid_file):
    with open(sid_file, "r") as f:
        try:
            sid_list = json.load(f)
            if not isinstance(sid_list, list):
                sid_list = [sid_list]
        except json.JSONDecodeError:
            sid_list = []
else:
    sid_list = []

sid_list.append({"sid": message.sid})

with open(sid_file, "w") as f:
    json.dump(sid_list, f, indent=2)