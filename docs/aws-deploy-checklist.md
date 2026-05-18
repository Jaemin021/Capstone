# AWS Deploy Checklist (Amplify + EC2)

This checklist is for this project layout:
- Frontend: AWS Amplify (`develop5`)
- Backend API: EC2 (FastAPI)

## 1) Amplify branch env (frontend)

Open Amplify Console:
- App -> Branch `develop5` -> `Environment variables`

Set these values:

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=https://<YOUR_BACKEND_DOMAIN_OR_PUBLIC_IP>
VITE_PUBLIC_APP_ORIGIN=https://develop5.d167kadf77tmvj.amplifyapp.com
VITE_REQUIRE_MOBILE_RESPOND=false
```

Notes:
- `VITE_API_BASE_URL` must be reachable from mobile network.
- Do not use private LAN addresses (`172.x.x.x`, `192.168.x.x`, `10.x.x.x`) for public users.

After saving env:
- Click `Redeploy this version` (or trigger a new build on `develop5`).

## 2) EC2 backend deploy check

SSH to EC2, then:

```bash
cd <backend_repo_path>
git fetch origin
git rev-parse --short HEAD
git rev-parse --short origin/develop5
```

If different, deploy latest:

```bash
git checkout develop5
git pull --ff-only origin develop5
```

Restart backend service (replace service name):

```bash
sudo systemctl restart <backend_service_name>
sudo systemctl status <backend_service_name> --no-pager
```

Check logs:

```bash
sudo journalctl -u <backend_service_name> -n 200 --no-pager
```

## 3) Backend runtime env check

Ensure backend has:
- `OPENAI_API_KEY` set (for quality/construct LLM evaluation)
- `FRONTEND_ORIGINS` includes Amplify domain

Example:

```env
FRONTEND_ORIGINS=https://develop5.d167kadf77tmvj.amplifyapp.com
OPENAI_API_KEY=sk-...
```

If env changed, restart service again.

## 4) Health check (added endpoint)

Backend now provides:

```text
GET /health
```

Expected JSON keys:
- `status: "ok"`
- `openai_api_key_configured: true|false`
- `allowed_origins: [...]`

Quick test:

```bash
curl -s https://<BACKEND_HOST>/health
```

## 5) Quick validation flow

1. Hard refresh frontend (`Ctrl+F5`)
2. Create public link
3. Verify link is not `.../public/s/mock-...`
4. Open link on mobile
5. Run quality evaluation on results page

If quality evaluation returns HTML:
- frontend is still calling wrong host/path
- recheck `VITE_API_BASE_URL` and Amplify redeploy

