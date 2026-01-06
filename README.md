<p align="center">
  <img src="/logos/trueman-logo-round.png" width="200" />
</p>

<h1 align="center">TruE-MAN</h1>

<p align="center">
  <strong>Trusted Ethereum-based Multi-operator Access Network</strong>
</p>

<p align="center">
  A blockchain-powered platform for secure 5G network resource sharing between mobile operators
</p>

---

## Overview

TruE-MAN enables trusted, transparent, and automated resource sharing agreements (SLAs) between 5G network operators using Ethereum smart contracts. The platform facilitates:

- **Secure SLA Management**: Smart contract-based service level agreements with automated payment escrow
- **Multi-operator Collaboration**: Seamless resource sharing between different mobile network operators
- **Real-time Network Control**: Integration with gNodeB agents for dynamic network reconfiguration
- **Transparent Transactions**: All agreements and payments recorded on the blockchain

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User Panel    │     │   Admin Panel   │     │   Blockchain    │
│   (Port 3020)   │     │   (Port 3010)   │     │   (Port 8545)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         └───────────┬───────────┴───────────────────────┘
                     │
              ┌──────┴──────┐
              │  Middleware │
              │ (Port 5000) │
              └──────┬──────┘
                     │
              ┌──────┴──────┐
              │ gNodeB Agent│
              │ (Port 4000) │
              └─────────────┘
```

## Project Structure

```
TruE-MAN/
├── contracts/           # Solidity smart contracts
│   └── contract1/       # Resource sharing SLA contract
├── middleware/          # Flask API bridging panels with network agent
│   ├── src/             # Application source code
│   ├── tests/           # Unit tests
│   └── docs/            # API documentation
├── panel-admin/         # Admin web interface (Express.js)
│   └── public/          # Frontend assets
├── panel-user/          # User web interface (Express.js)
│   └── public/          # Frontend assets
├── shared/              # Shared utilities (ethers.js helpers)
└── logos/               # Project branding assets
```

## Components

### Smart Contract (`contracts/`)

Ethereum smart contract managing resource sharing SLAs:
- Create service requests with ETH escrow
- Confirm/cancel requests with automatic payment handling
- Track request status (Created, Confirmed, Cancelled)
- Event emission for transaction tracking

### Middleware (`middleware/`)

Flask-based REST API that:
- Bridges admin panel with gNodeB agent
- Manages SQLite database for request tracking
- Handles network reconfiguration on request approval
- Communicates with blockchain via Node.js panels

### Admin Panel (`panel-admin/`)

Web interface for network operators to:
- View pending resource sharing requests
- Confirm or reject requests
- Monitor active SLAs
- Manage network configurations

### User Panel (`panel-user/`)

Web interface for tenant operators to:
- Create new resource sharing requests
- Specify user count, duration, and configuration
- Submit ETH payments for services
- Track request status

## Prerequisites

- **Node.js** v18+
- **Python** 3.9+
- **Docker** (optional, for containerized deployment)
- **Ethereum Node** (local Ganache or testnet)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/TruE-MAN.git
cd TruE-MAN
```

### 2. Install Node.js Dependencies

```bash
npm install
```

### 3. Set Up Middleware

```bash
cd middleware
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Or using Docker:
```bash
cd middleware
docker compose up --build
```

## Running the Application

### Start All Services

**Terminal 1 - Middleware:**
```bash
cd middleware
source venv/bin/activate
python src/main.py
```

**Terminal 2 - Admin Panel:**
```bash
node panel-admin/server.js
```

**Terminal 3 - User Panel:**
```bash
node panel-user/server.js
```

### Service Ports

| Service      | Port  | Description                    |
|--------------|-------|--------------------------------|
| User Panel   | 3020  | Tenant operator interface      |
| Admin Panel  | 3010  | Network operator interface     |
| Middleware   | 5000  | Backend API                    |
| gNodeB Agent | 4000  | Network control agent          |
| Blockchain   | 8545  | Ethereum JSON-RPC              |

## Configuration

### Environment Variables

**Middleware:**
| Variable          | Default                        | Description              |
|-------------------|--------------------------------|--------------------------|
| `NODE_SERVER_URL` | `http://localhost:3020/api`    | User panel API endpoint  |
| `AGENT_URL`       | `http://localhost:4000`        | gNodeB agent endpoint    |
| `FLASK_ENV`       | `development`                  | Flask environment        |

### Blockchain Configuration

Update the RPC provider URL in `shared/shared.js`:
```javascript
const provider = new ethers.JsonRpcProvider("http://localhost:8545");
```

## Testing

### Middleware Tests
```bash
cd middleware
source venv/bin/activate
pytest
```

## API Reference

See [Middleware API Documentation](middleware/docs/README.md) for detailed endpoint specifications.

### Quick Reference

| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| POST   | `/api/create`                     | Create sharing request   |
| PATCH  | `/api/request/<tx_hash>/<state>`  | Update request state     |
| POST   | `/api/pending`                    | Get pending requests     |
| POST   | `/api/confirm`                    | Confirm a request        |

## Smart Contract

The `contract1` smart contract handles:

- **Request Creation**: Operators submit requests with ETH payment
- **Payment Escrow**: ETH held in contract until confirmation
- **Confirmation**: Deployer confirms and receives payment
- **Cancellation**: Automatic refund to buyer on cancellation

### Pricing

```
Rate: 0.00012 ETH per minute per user (~€0.50/min)
Total Cost = rate × duration (mins) × number of users
```

## License

ISC License

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
