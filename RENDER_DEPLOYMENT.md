# 🚀 Deploy AgeixAISOC on Render.com (Free SaaS)

## Prerequisites

1. **GitHub account** - Already done (repo: https://github.com/azizragab83/AgeixAISOC.git)
2. **Render.com account** - Create free account at https://render.com
3. **Groq API Key** - Free API key at https://console.groq.com (used for AI agents in cloud)

## Deployment Steps

### 1. Create Render Account
- Go to https://render.com and sign up with GitHub
- Click "New +" → "Blueprint"

### 2. Connect GitHub Repo
- Select the `AgeixAISOC` repository
- Render will automatically detect the `render.yaml` file

### 3. Configure Environment Variables
After the Blueprint is created, you need to set the **GROQ_API_KEY**:

1. Go to your **ageixaisoc-backend** service
2. Click **Environment** tab
3. Add the following:
   - `GROQ_API_KEY` = your Groq API key (from https://console.groq.com)
4. Click **Save Changes** → **Manual Deploy** → **Deploy latest commit**

### 4. Wait for Deployment
- Backend will build and deploy first (~5-10 min)
- Frontend will build and deploy second (~3-5 min)

### 5. Access Your SaaS
- **Frontend:** `https://ageixaisoc-frontend.onrender.com`
- **Backend API:** `https://ageixaisoc-backend.onrender.com`
- **Health Check:** `https://ageixaisoc-backend.onrender.com/api/health`

## What Works in the Cloud

| Feature | Status |
|--------|--------|
| Dashboard UI | ✅ Works |
| API Endpoints | ✅ Works |
| AI Agents (via Groq) | ✅ Works (requires GROQ_API_KEY) |
| RAG Engine | ✅ Works (ChromaDB in-memory) |
| WebSocket Dashboard | ✅ Works |
| MITRE ATT&CK Coverage | ✅ Works |
| Threat Intel Feeds | ✅ Works |
| Sigma Rule Generation | ✅ Works |

## What Won't Work in the Cloud

| Feature | Reason |
|--------|-------|
| Kali SSH Attacks | Lab VMs are on local network (192.168.56.x) |
| Wazuh SIEM | Local VM only |
| FortiGate Firewall | Local VM only |
| n8n SOAR | Local service only |
| Win10/AD/Metasploitable | Local VMs only |

## Free Tier Limits (Render.com)

- **750 hours/month** free per service (2 services = 1500 hours)
- **Sleep after 15 min** of inactivity (wakes on request)
- **500 MB storage** per service
- **512 MB RAM** per service

## Troubleshooting

### Backend fails to build
- Check build logs for missing dependencies
- Ensure `Dockerfile.render` is being used (not `Dockerfile.backend`)

### Backend deploys but health check fails
- Check logs: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Ensure port 8000 is exposed

### Frontend can't reach backend
- Check `BACKEND_URL` env var in frontend service
- Should be: `https://ageixaisoc-backend.onrender.com`

### AI agents return fallback values
- Set `GROQ_API_KEY` in backend service environment
- Verify the key is valid at https://console.groq.com