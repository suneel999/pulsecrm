# WhatsApp appointment Flow → Pulse Desk (production)

Same EC2 as CRM. Bookings land on the desk with source **WA** next to Web and App.

**Endpoint URL (use this in Meta):**  
`https://desk.thepulseheart.com/api/whatsapp/flow`

---

## A. On EC2 (one time)

```bash
cd /opt/pulse-desk
sudo git pull
sudo mkdir -p secrets
sudo docker compose run --rm desk python scripts/gen_wa_flow_keys.py
# If docker path fails, run on host with cryptography installed:
#   sudo python3 scripts/gen_wa_flow_keys.py

sudo nano .env
```

Add (fill App Secret from Meta):

```
WA_FLOW_PRIVATE_KEY_PATH=secrets/wa_flow_private.pem
WA_FLOW_PASSPHRASE=
WA_APP_SECRET=YOUR_META_APP_SECRET
WA_PHONE_NUMBER_ID=YOUR_PHONE_NUMBER_ID
WA_ACCESS_TOKEN=YOUR_SYSTEM_USER_OR_TEMP_TOKEN
```

```bash
sudo docker compose up -d --build
curl -s https://desk.thepulseheart.com/api/whatsapp/flow
# expect: {"ok":true,"service":"pulse-whatsapp-flow",...}
```

### Upload public key to Meta

```bash
cd /opt/pulse-desk
PUB=$(sudo cat secrets/wa_flow_public.pem | awk '{printf "%s\\n", $0}')
# Better: use the file with curl --data-urlencode

sudo apt-get install -y jq 2>/dev/null || true

PHONE_NUMBER_ID="YOUR_PHONE_NUMBER_ID"
TOKEN="YOUR_ACCESS_TOKEN"

curl -sS -X POST "https://graph.facebook.com/v21.0/${PHONE_NUMBER_ID}/whatsapp_business_encryption" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "business_public_key=@secrets/wa_flow_public.pem"
```

If Meta rejects the file form, send JSON with newlines escaped — see Meta “Sign and upload the business public key” docs.

---

## B. In WhatsApp Manager (your screenshot)

1. **Account tools → Flows → Create**
2. **Name:** `Pulse Appointment Booking`
3. **Categories:** Appointment booking
4. **With Endpoint** + **Appointment booking** template
5. Click **Create**

### Connect endpoint

1. Open the Flow → **⋯ / Endpoint** (or Edit Flow → Endpoint)
2. Endpoint URL: `https://desk.thepulseheart.com/api/whatsapp/flow`
3. Connect your **Meta App** (same app as WhatsApp Cloud API)
4. Ensure public key is uploaded (step A)

### Departments in the template

Endpoint already returns Pulse departments:

- Cardiology, Neurology, Pulmonology, Gastroenterology  
- Orthopedics, General Medicine, Radiology  

Location: **Miyapur only**  
Dates: next ~14 OP days (Sun skipped)  
Times: 10:30–3:30 (General Medicine also 6:30–7:30)

If the Flow Builder dropdown ids differ from the template, open Endpoint → **Snippets → Responses** and align screen names: `APPOINTMENT`, `DETAILS`, `SUMMARY`, `SUCCESS`.

---

## C. Test before Publish

1. Flow → **Preview / Test**
2. Complete a booking with your phone
3. Open https://desk.thepulseheart.com → **To call / Requested**  
   Row should show tag **WA**, status **New**
4. Only then click **Publish**

### Optional: send Flow from Cloud API

Use a message template or interactive Flow message with `flow_id` after publish. Front office can also share a CTA “Book appointment” that opens the Flow.

---

## D. After go-live checklist

| Check | OK |
|-------|----|
| Desk shows WA bookings | |
| Website ingest key fixed (Hostinger `crm-endpoint.php`) | |
| App sync still running | |
| All three sources on one desk | Web / App / WA |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Endpoint health fails in Meta | `curl` the URL; rebuild containers; check Caddy |
| HTTP 421 | Public key mismatch — re-upload `wa_flow_public.pem` |
| HTTP 432 | Wrong/missing `WA_APP_SECRET` |
| Booking not on desk | Check container logs: `sudo docker compose logs desk --tail=100` |
| Empty departments | Flow screen must be named `APPOINTMENT` (template default) |

```bash
sudo docker compose -f /opt/pulse-desk/docker-compose.yml logs desk --tail=80
```
