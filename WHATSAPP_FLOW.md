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

# Generate keys on the HOST (do not use docker for this if secrets was :ro)
sudo openssl genrsa -out secrets/wa_flow_private.pem 2048
sudo openssl rsa -in secrets/wa_flow_private.pem -pubout -out secrets/wa_flow_public.pem
sudo chmod 600 secrets/wa_flow_private.pem
sudo ls -la secrets/
# must show wa_flow_private.pem and wa_flow_public.pem

sudo nano .env
```

Add (digits only for phone id — no comments on the same line):

```
WA_FLOW_PRIVATE_KEY_PATH=secrets/wa_flow_private.pem
WA_FLOW_PASSPHRASE=
WA_APP_SECRET=YOUR_META_APP_SECRET
WA_PHONE_NUMBER_ID=1337805766078219
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

# Clean exports (no comments in values)
export WA_PHONE_NUMBER_ID="$(sudo grep '^WA_PHONE_NUMBER_ID=' .env | cut -d= -f2- | tr -d '[:space:]' | sed 's/#.*//')"
export WA_ACCESS_TOKEN="$(sudo grep '^WA_ACCESS_TOKEN=' .env | cut -d= -f2- | tr -d '[:space:]' | sed 's/#.*//')"

echo "PHONE=$WA_PHONE_NUMBER_ID"
echo "TOKEN_LEN=${#WA_ACCESS_TOKEN}"
# PHONE should be ~15-17 digits only

curl -sS -X POST "https://graph.facebook.com/v21.0/${WA_PHONE_NUMBER_ID}/whatsapp_business_encryption" \
  -H "Authorization: Bearer ${WA_ACCESS_TOKEN}" \
  -F "business_public_key=@/opt/pulse-desk/secrets/wa_flow_public.pem"
```

Expect JSON like `{"success":true}`.

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

### Flow JSON (doctors + slot rules)

Paste `flow_json/pulse_appointment_booking.json` into Flow Builder (replace the draft JSON), **Save**, then Preview.

Rules enforced by the endpoint (`wa_flow.py`):

- **Doctor** dropdown after department (site doctors, titles ≤30 chars)
- **Dates**: next **~1 week** of OP days (Sun skipped). Mukharjee starts **day after tomorrow**
- **Dr. Movva Srinivas**: slots **9:00 AM–3:00 PM**
- **Other doctors**: OP slots from resumes; **today** only shows slots **≥ 2 hours from now**
- **General Medicine**: 10:30–1:30 + 6:30–7:30
- Location assumed Miyapur (no location field)

Screen ids: `APPOINTMENT` → `DETAILS` → `SUMMARY` → `SUCCESS` (+ `TERMS`).

---

## C. Auto-reply menu (any patient message)

Webhook URL (Meta App → WhatsApp → Configuration → Callback):  
`https://desk.thepulseheart.com/api/whatsapp/webhook`

1. In `.env` on EC2 add (same App Secret already used for Flows):

```
WA_VERIFY_TOKEN=pulse-wa-verify
WA_FLOW_ID=
WA_EMERGENCY_PHONE=9000777019
WA_APPOINTMENTS_PHONE=8886688063
```

2. Meta → Webhook → Verify and save (token = `WA_VERIFY_TOKEN`)
3. Subscribe to field **messages**
4. Patient texts anything → bot replies with buttons:
   - **Book appointment** → opens published Flow
   - **Emergency** → emergency + appointments numbers + location pin
   - **Location** → Miyapur map pin

After **Publish**, copy Flow ID into `WA_FLOW_ID` and recreate containers.

On Confirm, patient gets a WhatsApp **confirmation** message; desk gets a **WA** row.

---

## D. Test then Publish

1. Flow → **Preview** (interactive) → complete one booking  
2. Desk shows **WA** row + confirmation message on WhatsApp  
3. Click **Publish**  
4. Set `WA_FLOW_ID` on EC2, rebuild  
5. Message the business number → menu → Book → finish Flow  

---

## E. After go-live checklist

| Check | OK |
|-------|----|
| Desk shows WA bookings | |
| Confirmation WhatsApp after Confirm | |
| Menu: Book / Emergency / Location | |
| Website ingest key (Hostinger) | |
| App sync still running | |
| Web / App / WA on one desk | |

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
