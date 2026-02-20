# TruE-MAN Middleware

## 1. Overview

The TruE-MAN Middleware is a RESTful web service that acts as an intermediary layer between the administrative web panel and the underlying infrastructure components. Its primary purpose is to orchestrate spectrum sharing requests by bridging communication between the user-facing administration interface, a blockchain-based smart contract system, and the gNodeB (5G base station) agent. The middleware manages the complete lifecycle of spectrum sharing transactions, from initial request creation through execution and eventual restoration of the original network configuration.

## 2. Technology Stack

The middleware is implemented in **Python 3** using the **Flask** web framework (version 3.0+), a lightweight and extensible microframework well-suited for building RESTful APIs. HTTP client operations are handled via the **requests** library for outbound communication with external services. The application is designed to be containerized and deployable using **Docker**, with container orchestration supported through **Docker Compose**.

## 3. Architecture

The middleware follows a modular, service-oriented architecture with clear separation of concerns:

- **Application Entry Point (`main.py`)**: Initializes the Flask application, configures environment variables, and registers API route blueprints.
- **Routes Layer (`routes.py`)**: Defines HTTP endpoints and handles request parsing and response formatting.
- **Service Layer (`services/`)**: Contains business logic organized into specialized modules:
  - `request_service.py`: Handles creation and validation of sharing requests.
  - `state_service.py`: Manages request state transitions and orchestrates agent operations.
  - `agent_service.py`: Encapsulates all communication with the gNodeB agent.
  - `config_service.py`: Handles scheduling of configuration restoration.
- **Utilities (`utils.py`)**: Provides low-level agent communication functions and helper methods.
- **Database Layer (`database.py`)**: Manages persistent storage of request data.

## 4. Data Model

The middleware employs an embedded **SQLite** relational database for persistent storage of request records. The database schema consists of a single `requests` table with the following structure:

| Field | Type | Description |
|-------|------|-------------|
| `id` | TEXT (PK) | Internal UUID for the request |
| `external_requestId` | TEXT (UNIQUE) | Blockchain transaction identifier |
| `private_key` | TEXT | Blockchain private key for transaction signing |
| `contract_address` | TEXT | Smart contract address on the blockchain |
| `shared_tac` | TEXT | Tracking Area Code allocated for sharing |
| `ue_imsis_json` | TEXT | JSON array of tenant User Equipment IMSIs |
| `duration_mins` | INTEGER | Sharing duration in minutes |
| `tenant_plmn` | TEXT | Public Land Mobile Network identifier for tenant |
| `tenant_amf_ip` | TEXT | IP address of tenant's Access and Mobility Management Function |
| `tenant_amf_port` | INTEGER | Port number of tenant's AMF |
| `tenant_nssai_json` | TEXT | JSON representation of Network Slice Selection Assistance Information |
| `gtp_addr` | TEXT | GTP tunnel endpoint address |
| `tdd_config` | INTEGER | Time Division Duplex configuration |
| `amf_addr` | TEXT | Non-tenant AMF address |
| `nssai_json` | TEXT | Non-tenant NSSAI configuration |
| `plmn` | TEXT | Non-tenant PLMN |
| `tac` | INTEGER | Non-tenant Tracking Area Code |
| `state` | TEXT | Request lifecycle state |
| `created_at` | TIMESTAMP | Record creation timestamp |

Request states follow a defined lifecycle: `Created` → `Pending` → `Accepted`/`Rejected` → `Completed`/`Expired`/`RestoreFailed`.

## 5. API Endpoints

The middleware exposes the following RESTful HTTP endpoints:

### 5.1 Create Request

- **Endpoint**: `POST /api/request`
- **Description**: Creates a new spectrum sharing request and forwards it to the blockchain server for registration on the smart contract.
- **Request Body** (JSON):

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

- **Response**: Returns the blockchain request ID upon successful creation.

### 5.2 Update Request State

- **Endpoint**: `PATCH /api/request/<external_requestId>/<state>`
- **Description**: Updates the state of an existing request. Valid states are `accepted`, `rejected`, and `completed`.
- **Behaviour on `accepted`**:
  1. Restarts the gNodeB service with tenant-specific configuration parameters.
  2. Retrieves all registered User Equipment (UE) from the agent.
  3. Updates Tracking Area Code (TAC) restrictions for non-tenant UEs to enforce network isolation.
  4. Schedules automatic restoration of the original configuration upon expiration of the sharing duration.

## 6. External Integrations

The middleware integrates with two external systems:

1. **Blockchain Node Server**: A Node.js service that interfaces with the Ethereum-compatible blockchain (Hyperledger Besu) hosting the spectrum sharing smart contracts. The middleware forwards request creation payloads to this server for on-chain registration.

2. **gNodeB Agent**: An HTTP-based agent running on the 5G base station that accepts configuration commands. The middleware communicates with the agent to:
   - Restart the gNodeB service with modified parameters (tenant AMF, PLMN, NSSAI, TAC).
   - Retrieve the list of connected UEs.
   - Update UE configurations (e.g., forbidden TAI lists for network isolation).

## 7. Deployment

The middleware is packaged as a Docker container with the following specifications:

- **Default Port**: 25000
- **Data Persistence**: SQLite database stored in a mounted volume at `/app/data/`
- **Configuration**: Environment variables for external service URLs and gNodeB parameters

A `docker-compose.yml` file is provided for simplified deployment, handling container networking and volume management.

## 8. Configuration Parameters

The middleware supports configuration via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_SERVER_URL` | URL of the blockchain Node.js server | `http://localhost:3020/api` |
| `AGENT_URL` | Base URL of the gNodeB agent | `http://localhost:4000` |
| `AGENT_GNB_ID` | gNodeB resource identifier | `1` |
| `AGENT_GTP_ADDR` | GTP tunnel address | `172.16.100.209` |
| `AGENT_AMF_ADDR` | Non-tenant AMF address | `172.16.100.203` |
| `AGENT_PLMN` | Non-tenant PLMN | `99940` |
| `AGENT_TAC` | Non-tenant TAC | `100` |
| `AGENT_TDD_CONFIG` | TDD configuration index | `1` |
| `AGENT_NSSAI` | Non-tenant NSSAI (JSON) | `[{"sst":1}, ...]` |
