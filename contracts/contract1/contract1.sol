// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

/// @title contract1
/// @notice Resource sharing SLAs between 5G Operators
/// @dev Use orderDetails for adding raw data (IMSIs, etc) to the request

contract contract1 {
    address public deployerOperator;  // ETH address of the operator deploying the contract on the chain
    uint256 public nextRequestId;

    enum Status { Created, Confirmed, Cancelled }

    struct Request {
        uint256 id;
        address buyerOperator;  // ETH address of operator requesting the service
        uint256 numUsers;
        uint256 durationMins;
        bytes32 orderDetails;    // hash of off-chain payload (can be anything like IMSI list, details on the order of the service, etc.)
        Status status;
        uint256 createdAt;
        uint256 amountPaid;     // amount of ETH sent by the buyer
    }

    mapping(uint256 => Request) public requests;

    event RequestCreated(
        uint256 indexed id,
        address indexed buyerOperator,
        uint256 numUsers,
        uint256 durationMins,
        bytes32 orderDetails,
        uint256 amountPaid
    );

    event RequestConfirmed(uint256 indexed id);
    event RequestCancelled(uint256 indexed id, string reason);

    modifier onlyDeployer() {
        require(msg.sender == deployerOperator, "Not the deployer Operator"); // all contract actions (except for create request) should be possible by the deployer operator only
        _;
    }

    constructor(address _deployer) {
        deployerOperator = _deployer;
    }

    /// @notice New service request (ETH stored in contract until confirmation by the deployer Operator)
    function createRequest(
        address buyerOperator,
        uint256 numUsers,
        uint256 durationMins,
        bytes32 orderDetails
    ) external payable returns (uint256) {
        require(buyerOperator != address(0), "Invalid buyerOperator");

        uint256 requiredPayment = durationMins * numUsers * 0.00012 ether;  // charge approx. 0.5euro/minute
        require(msg.value >= requiredPayment, "Insufficient amount on buyer's account");

        uint256 id = nextRequestId++;
        requests[id] = Request({
            id: id,
            buyerOperator: buyerOperator,
            numUsers: numUsers,
            durationMins: durationMins,
            orderDetails: orderDetails,
            status: Status.Created,
            createdAt: block.timestamp,
            amountPaid: msg.value
        });

        emit RequestCreated(id, buyerOperator, numUsers, durationMins, orderDetails, msg.value);
        return id;
    }

    /// @notice Confirm the request and transfer ETH to the deployer Operator
    function confirmRequest(uint256 id) external onlyDeployer {
        Request storage req = requests[id];
        require(req.status == Status.Created, "The request is not in 'Created' status");

        (bool sent, ) = deployerOperator.call{value: req.amountPaid}("");
        require(sent, "Payment failed");

        req.status = Status.Confirmed;
        emit RequestConfirmed(id);
    }

    /// @notice Cancel the request and refund ETH to the buyer
    function cancelRequest(uint256 id, string calldata reason) external onlyDeployer {
        Request storage req = requests[id];
        require(req.status == Status.Created, "The request is not in 'Created' status");

        if (req.amountPaid > 0) {
            (bool refunded, ) = req.buyerOperator.call{value: req.amountPaid}("");
            require(refunded, "Refund failed");
        }

        req.status = Status.Cancelled;
        emit RequestCancelled(id, reason);
    }

    /// @notice Get pending requests (status = 'Created')
    function getPendingRequests() external view onlyDeployer returns (Request[] memory) {
        uint256 count = 0;

        for (uint256 i = 0; i < nextRequestId; i++) {   // Count pending requests first
            if (requests[i].status == Status.Created) {
                count++;
            }
        }

        Request[] memory pending = new Request[](count);
        uint256 index = 0;
        for (uint256 i = 0; i < nextRequestId; i++) {
            if (requests[i].status == Status.Created) {
                pending[index] = requests[i];
                index++;
            }
        }

        return pending;
    }

    /// @notice Get confirmed requests
    function getConfirmedRequests() external view onlyDeployer returns (Request[] memory) {
        uint256 count = 0;
        for (uint256 i = 0; i < nextRequestId; i++) {
            if (requests[i].status == Status.Confirmed) {
                count++;
            }
        }

        Request[] memory confirmed = new Request[](count);
        uint256 index = 0;
        for (uint256 i = 0; i < nextRequestId; i++) {
            if (requests[i].status == Status.Confirmed) {
                confirmed[index] = requests[i];
                index++;
            }
        }
        return confirmed;
    }

    /// @notice Get cancelled requests
    function getCancelledRequests() external view onlyDeployer returns (Request[] memory) {
        uint256 count = 0;
        for (uint256 i = 0; i < nextRequestId; i++) {
            if (requests[i].status == Status.Cancelled) {
                count++;
            }
        }
        
        Request[] memory cancelled = new Request[](count);
        uint256 index = 0;
        for (uint256 i = 0; i < nextRequestId; i++) {
            if (requests[i].status == Status.Cancelled) {
                cancelled[index] = requests[i];
                index++;
            }
        }
        return cancelled;
    }
}