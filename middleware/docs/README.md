# TruE-MAN Middleware

Flask-based middleware service that bridges the admin panel with the gNodeB agent and blockchain smart contracts.

## Structure

```
middleware/
├── src/
│   ├── main.py              # Flask app entry point
│   ├── routes.py            # API endpoints
│   ├── database.py          # SQLite database operations
│   ├── utils.py             # Agent communication utilities
│   └── services/
│       ├── __init__.py
│       ├── agent_service.py    # gNodeB agent interaction logic
│       ├── config_service.py   # Configuration restoration scheduling
│       ├── request_service.py  # Request creation and validation
│       └── state_service.py    # Request state transitions
├── tests/
│   ├── test_agent_service.py
│   ├── test_config_service.py
│   ├── test_database.py
│   ├── test_request_service.py
│   ├── test_routes.py
│   ├── test_routes_integration.py
│   ├── test_state_service.py
│   └── test_utils.py
├── data/               # SQLite database (auto-created)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pytest.ini
```

## Setup

### Local Development

```bash
cd middleware
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Docker

```bash
cd middleware
docker compose up --build
```

Or without compose:
```bash
docker build -t trueman-middleware .
docker run -p 25000:25000 -v middleware-data:/app/data trueman-middleware
```

## Running

### Local
```bash
source venv/bin/activate
python src/main.py
```

The service starts on port **25000** by default.

### Docker
```bash
docker compose up
```

## Testing

```bash
source venv/bin/activate
pytest
```

## API Endpoints

### POST `/api/request`

Create a new spectrum sharing request and forward it to the blockchain server.

**Request Body:**
```json
{
  "privateKey": "0x...",
  "contractAddress": "0x...",
  "sharedTAC": "100",
  "ueImsis": ["123456789012345", "987654321098765"],
  "durationMins": 60,
  "tenantPLMN": "99940",
  "tenantAMFIP": "172.16.10.203",
  "tenantAMFPort": 38412,
  "tenantNSSAI": [{"sst": 1}, {"sst": 1, "sd": 10}]
}
```

### PATCH `/api/request/<external_requestId>/<state>`

Update request state. Valid states: `accepted`, `rejected`, `completed`.

When state is `accepted`:
1. Restarts gNodeB with tenant configuration
2. Fetches all UEs from agent
3. Updates TAC restrictions (forbidden TAI lists) for non-tenant UEs
4. Marks request as `Completed`
5. Schedules automatic configuration restoration if a duration was specified

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_SERVER_URL` | Blockchain Node.js server URL | `https://besu.wimots.com/api` |
| `AGENT_URL` | gNodeB agent base URL | `http://172.16.100.209:28080` |
| `AGENT_GNB_ID` | gNodeB resource identifier | `1` |
| `AGENT_FEATURE_NAME` | Agent feature name | `gNodeB_service` |
| `AGENT_GTP_ADDR` | GTP tunnel address | `172.16.100.209` |
| `AGENT_TDD_CONFIG` | TDD configuration index | `1` |
| `AGENT_AMF_ADDR` | Non-tenant AMF address | `172.16.100.203` |
| `AGENT_NSSAI` | Non-tenant NSSAI (JSON) | `[{"sst":1}, {"sst":1,"sd":10}, ...]` |
| `AGENT_PLMN` | Non-tenant PLMN | `99940` |
| `AGENT_TAC` | Non-tenant TAC | `100` |

## Database

SQLite database at `middleware/data/requests.db` with the following states:
- `Created` - Initial state after request creation
- `Pending` - After forwarding to blockchain
- `Accepted` - Request approved by admin
- `Rejected` - Request denied by admin
- `Completed` - All agent operations finished successfully
- `Expired` - Configuration restored after sharing duration elapsed
- `RestoreFailed` - Automatic configuration restoration failed
