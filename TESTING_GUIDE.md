# Integration Server Testing Guide

## 🚀 Quick Start (3 Steps)

### 1. **Start the System**
```bash
# Make sure you're in the root directory
cd /workspaces/GenericIntegrationServer

# Start everything (this handles Docker, databases, backend, and web UI)
bash start_system.sh
```

### 2. **Access the Web Interface** 
Open your browser to: **http://localhost:5173**

### 3. **Create Your First Account**
Click "Create an account" and sign up with:
- **Organization Name**: `Test Org` (or any name you prefer)  
- **Email**: `admin@test.com` (or your preferred email)
- **Password**: `password123` (or your preferred password)

---

## 🎯 Complete Testing Walkthrough

### **Step 1: System Startup** ✅

The `start_system.sh` script automatically:
- ✅ Sets up Docker access
- ✅ Starts PostgreSQL database (port 5432)
- ✅ Starts Redis cache (port 6379) 
- ✅ Runs database migrations
- ✅ Starts backend API server (port 8000)
- ✅ Starts web development server (port 5173)

**Expected Output:**
```
🎉 SYSTEM FULLY OPERATIONAL!
   Backend: http://localhost:8000
   Web UI: http://localhost:5173
   Ready for Gmail/Google Drive → CleverBrag testing!
```

### **Step 2: Create Organization & User Account** ✅

1. **Navigate to Web UI**: http://localhost:5173
2. **Click "Create an account"**
3. **Fill out signup form**:
   - Organization Name: `My Test Organization`
   - Email: `test@example.com`  
   - Password: `testpassword123`
4. **Click "Create Account"**

**✅ Success**: You should be automatically logged in and see the dashboard

### **Step 3: Explore the Main Interface** ✅

After login, you'll see the main navigation with:
- **Dashboard**: Overview of your profiles
- **Profiles**: Connector configurations (legacy view)
- **Connectors**: Credential management 
- **Destinations**: Target system configurations
- **Sync Monitor**: Real-time sync progress dashboard ⭐ *NEW*

### **Step 4: Test API Documentation** ✅

1. **Open API Docs**: http://localhost:8000/docs
2. **Explore the enhanced documentation** we built:
   - Comprehensive endpoint descriptions
   - Authentication examples (JWT + API Keys)
   - Request/response schemas
   - Business context explanations

**✅ Test API Health**:
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### **Step 5: Set Up Your First Destination** ✅

1. **Go to "Destinations"** in the navigation
2. **Click "Add Destination"**
3. **Configure CleverBrag destination**:
   ```
   Name: My CleverBrag Instance
   Type: cleverbrag
   API Key: your_api_key_here
   Base URL: https://api.cleverbrag.cleverthis.com
   ```
4. **Test Connection** (optional)
5. **Save Destination**

**Alternative: CSV Destination for Testing**:
```
Name: CSV Export Test
Type: csvdump  
Output Directory: ./csv_dumps
```

### **Step 6: Set Up Connectors & Credentials** ✅

#### **Option A: Mock Connector (Easiest for testing)**
1. **Go to "Connectors"**
2. **Add Static Credential**:
   ```
   Connector: Mock Source
   Name: Test Mock Connector
   Config: {"test": "value"}
   ```

#### **Option B: Google Drive (Full OAuth)**
1. **Set up Google OAuth** (requires Google Cloud Console):
   - Create OAuth 2.0 credentials
   - Set redirect URI: `http://localhost:8000/oauth/google/drive/callback`
   - Add credentials to environment

2. **Start OAuth Flow**:
   - Go to "Connectors"
   - Find "Google Drive"
   - Click "Start OAuth"
   - Complete Google authorization

### **Step 7: Create CC-Pair (Connector-Credential Pair)** ⭐ *NEW*

1. **Go to "Sync Monitor"** or use API directly
2. **Create new CC-Pair**:
   ```bash
   curl -X POST http://localhost:8000/cc-pairs/ \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "X-Org-ID: YOUR_ORG_ID" \
     -H "Content-Type: application/json" \
     -d '{
       "connector_id": 1,
       "credential_id": "your-credential-uuid",
       "name": "Test Sync",
       "destination_target_id": "your-destination-id"
     }'
   ```

### **Step 8: Test Real-Time Sync Monitoring** ⭐ *NEW*

1. **Navigate to "Sync Monitor"**
2. **Start a test sync**:
   ```bash
   curl -X POST http://localhost:8000/cc-pairs/1/index-attempts \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "X-Org-ID: YOUR_ORG_ID"
   ```

3. **Watch real-time progress**:
   - ✅ Progress bars showing batch completion
   - ✅ Heartbeat indicators
   - ✅ Real-time status updates (every 5 seconds)
   - ✅ Sync cancellation capability

### **Step 9: Test Error Handling** ⭐ *NEW*

#### **Test Form Validation**:
1. **Go to Login page**
2. **Try invalid inputs**:
   - Invalid email format
   - Short password  
   - Empty fields
3. **✅ Expected**: Real-time validation with helpful error messages

#### **Test Network Errors**:
1. **Stop the backend**: `pkill -f uvicorn`
2. **Try to navigate in the web UI**
3. **✅ Expected**: 
   - User-friendly error messages
   - Retry buttons
   - Graceful error boundaries (no crashes)

4. **Restart backend**: `bash start_system.sh`
5. **✅ Expected**: Automatic recovery with retry mechanisms

### **Step 10: Test Advanced Features**

#### **API Key Management**:
```bash
# Create API key
curl -X POST http://localhost:8000/api-keys/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"name": "Test API Key", "role": "BASIC"}'

# Use API key instead of JWT
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/connectors/definitions
```

#### **Security & Encryption**:
```bash
# Check encryption status (requires admin)
curl -H "X-Admin-Secret: YOUR_ADMIN_SECRET" \
  http://localhost:8000/security/encryption/status
```

#### **Metrics & Monitoring**:
- **Prometheus metrics**: http://localhost:8000/metrics/prometheus
- **Health checks**: http://localhost:8000/health/detailed
- **Alert management**: http://localhost:8000/alerts/active

---

## 🛠️ Troubleshooting

### **Services Won't Start**
```bash
# Check if ports are in use
lsof -i :8000  # Backend
lsof -i :5173  # Web UI  
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Kill existing processes
pkill -f uvicorn
pkill -f vite
pkill -f postgres
pkill -f redis

# Restart
bash start_system.sh
```

### **Database Issues**
```bash
# Reset database
bash bin/reset_databases.sh

# Check database connectivity
python -c "
import asyncpg, asyncio, os
async def test(): 
    conn = await asyncpg.connect(host='localhost', port=5432, user='postgres', password='postgres', database='integration_server')
    print(await conn.fetchval('SELECT version()'))
asyncio.run(test())
"
```

### **Web UI Issues**
```bash
# Check web dependencies
cd web
npm install
npm run dev -- --port 5173 --host 0.0.0.0
```

### **Environment Issues**
```bash
# Copy sample environment
cp sample.env .env

# Generate Fernet key for credential encryption
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 📋 Test Checklist

Use this checklist to verify all features:

### **✅ Core System**
- [ ] System starts without errors
- [ ] All services respond (backend, web UI, database, Redis)
- [ ] Environment variables loaded correctly

### **✅ Authentication**  
- [ ] User signup works
- [ ] User login works
- [ ] JWT tokens issued correctly
- [ ] Organization isolation working
- [ ] API key generation works

### **✅ API Documentation**
- [ ] Swagger UI loads at /docs
- [ ] All endpoints have descriptions
- [ ] Authentication examples present
- [ ] Parameter descriptions clear

### **✅ Web Interface**
- [ ] All navigation links work
- [ ] Forms validate properly
- [ ] Error messages user-friendly
- [ ] Loading states display
- [ ] Responsive design works

### **✅ Real-Time Sync Monitoring**
- [ ] Sync Monitor page loads
- [ ] Active syncs display
- [ ] Progress bars show correctly
- [ ] Auto-refresh works (5-second polling)
- [ ] Sync cancellation works

### **✅ Error Handling**
- [ ] Form validation works
- [ ] Network error recovery
- [ ] Error boundaries prevent crashes
- [ ] Retry mechanisms functional
- [ ] User-friendly error messages

### **✅ Advanced Features**
- [ ] Connector definitions load
- [ ] Destination configuration works
- [ ] CC-Pair creation successful
- [ ] Metrics endpoint responds
- [ ] Health checks work

---

## 🎉 Success Indicators

**You'll know everything is working when**:

1. **✅ Dashboard shows**: "You have X connector profiles"
2. **✅ Sync Monitor displays**: Active syncs with progress bars
3. **✅ API Docs load**: With comprehensive descriptions  
4. **✅ Error handling works**: Try invalid forms/network errors
5. **✅ Real-time updates**: Progress updates every 5 seconds

**Your Integration Server is ready for production! 🚀**

---

## 📞 Need Help?

**Common URLs:**
- **Web UI**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs  
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics/prometheus

**Log Locations:**
- **Backend logs**: Terminal where you ran `start_system.sh`
- **Web UI logs**: Browser developer console
- **Database logs**: Docker logs

**Quick Reset:**
```bash
# Complete system reset
pkill -f uvicorn && pkill -f vite
bash bin/reset_databases.sh
bash start_system.sh
```
