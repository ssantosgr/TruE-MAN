# TruE-MAN Middleware

Flask-based middleware service that bridges the admin panel with the gNodeB agent and blockchain smart contracts.

## Structure

```
middleware/
├── src/
│   ├── main.py         # Flask app entry point
│   ├── routes.py       # API endpoints
│   ├── database.py     # SQLite database operations
│   └── utils.py        # Agent communication utilities
├── tests/
│   ├── test_database.py
│   └── test_utils.py
├── data/               # SQLite database (auto-created)
├── requirements.txt
└── pytest.ini
```

## Setup

```bash
cd middleware
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
source venv/bin/activate
python src/main.py
```

## Testing

```bash
source venv/bin/activate
pytest
```

## API Endpoints

### POST `/api/create`

Create a new sharing request.

**Request Body:**
```json
{
  "privateKey": "0x...",
  "contractAddress": "0x...",
  "sharedTAC": "101",
  "ueImsis": ["001010000045613"],
  "durationMins": 60,
  "tenantPLMN": "00101",
  "tenantAMFIP": "192.168.1.1",
  "tenantAMFPort": 38412,
  "tenantNSSAI": [{"sst": 1}]
}
```

### PATCH `/api/request/<tx_hash>/<state>`

Update request state. Valid states: `accepted`, `rejected`, `completed`.

When state is `accepted`:
1. Restarts gNodeB with tenant configuration
2. Fetches all UEs from agent
3. Updates TAC restrictions for non-tenant UEs
4. Marks request as `completed`

## Configuration

Environment variables or Flask config:
- `NODE_SERVER_URL` - Node.js blockchain server URL (default: `http://localhost:3020/api`)
- `AGENT_URL` - gNodeB agent URL (default: `http://localhost:4000/resource/1`)

## Database

SQLite database at `middleware/data/requests.db` with the following states:
- `Created` - Initial state after request creation
- `Pending` - After forwarding to blockchain
- `Accepted` - Request approved by admin
- `Rejected` - Request denied by admin
- `Completed` - All agent operations finished
