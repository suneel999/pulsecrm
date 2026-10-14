# Pulse Heart front-office appointment desk

Website forms keep sending email to `appointments@thepulseheart.com`. They also post each request here so front office can call, mark status, add notes, tick services after visit, and download a month Excel.

Hi Pulse App requests from `https://api.thepulseheart.com` are pulled into the same list (source tag **App**). Set `APP_API_EMAIL` and `APP_API_PASSWORD` in `.env`. The desk syncs automatically every ~90 seconds, or use **Sync Hi Pulse App**. Staff status and notes are never overwritten by a sync.

Staff login: `/login`

## Local test

```
cd D:\pulse\pulse-desk
copy .env.example .env
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8090/login

## AWS

1. New Ubuntu EC2, open 22, 80, 443.
2. Clone this folder to `/opt/pulse-desk`.
3. Copy `.env.example` to `.env` and set `ADMIN_PASS` and `CRM_INGEST_KEY`.
4. Hostinger DNS: A record `desk` → EC2 public IP.
5. `sudo docker compose up -d --build`
6. On Hostinger, set `crm-endpoint.php`:

```
'url' => 'https://desk.thepulseheart.com/api/ingest',
'secret' => 'the same CRM_INGEST_KEY',
```

Email still works if this desk is down.
