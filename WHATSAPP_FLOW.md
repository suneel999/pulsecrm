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
- **Dr. Mukharjee** (Cardiology): date = **day after tomorrow** only (Monday if that is Sunday)
- **Dr. Movva Srinivas**: slots **9:00 AM–3:00 PM**
- **Other doctors**: OP slots from resumes; **today** only shows slots **≥ 2 hours from now**
- **General Medicine**: 10:30–1:30 + 6:30–7:30
- Location: Miyapur · Sundays closed for OP

Screen ids: `APPOINTMENT` → `DETAILS` → `SUMMARY` → `SUCCESS` (+ `TERMS`).

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
