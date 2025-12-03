const express = require("express");
const fs = require("fs");
const { ethers } = require("ethers");
const bodyParser = require("body-parser");
const path = require("path");

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, "public")));

const provider = new ethers.JsonRpcProvider("http://localhost:8545");
const abiPath = "./contracts/contract1/contract1.abi.json";
const contractAbi = JSON.parse(fs.readFileSync(abiPath, "utf8"));

function getWallet(privateKey) {
  return new ethers.Wallet(privateKey.trim(), provider);
}

function getContract(contractAddress, privateKey) {
  const wallet = getWallet(privateKey);
  return new ethers.Contract(contractAddress, contractAbi, wallet);
}

function formatRequests(requests) {
  return requests.map(r => ({
    id: r.id.toString(),
    buyer: r.buyerOperator,
    numUsers: r.numUsers.toString(),
    durationMins: r.durationMins.toString(),
    amount: ethers.formatEther(r.amountPaid),
    status: r.status === 0 ? "Created" : r.status === 1 ? "Confirmed" : "Cancelled",
    createdAt: new Date(Number(r.createdAt) * 1000).toLocaleString(),
  }));
}

// --- CREATE request ---
app.post("/api/create", async (req, res) => {
  try {
    const { privateKey, contractAddress, numUsers, durationMins, offChainData } = req.body;
    if(!contractAddress) return res.status(400).json({ success:false, error:"Contract address required" });

    const contract = getContract(contractAddress, privateKey);
    const wallet = getWallet(privateKey);

    const requestHash = ethers.keccak256(ethers.toUtf8Bytes(offChainData || ""));
    const ratePerMinuteWei = ethers.parseEther("0.00012");
    const requiredPayment = ratePerMinuteWei * BigInt(durationMins) * BigInt(numUsers);

    const tx = await contract.createRequest(wallet.address, numUsers, durationMins, requestHash, {
      value: requiredPayment,
      gasLimit: 5_000_000,
    });
    await tx.wait();
    const requestId = (await contract.nextRequestId()) - 1n;

    res.json({ success: true, requestId: requestId.toString(), txHash: tx.hash, message: "Request Successful" });
  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, error: err.message, message: "Request Failed" });
  }
});

// --- CONFIRM request ---
app.post("/api/confirm", async (req, res) => {
  try {
    const { privateKey, contractAddress, requestId } = req.body;
    if(!contractAddress) return res.status(400).json({ success:false, error:"Contract address required" });

    const contract = getContract(contractAddress, privateKey);
    const pendingRequests = await contract.getPendingRequests();
    const exists = pendingRequests.some(r => r.id.toString() === requestId.trim());
    if (!exists) return res.status(400).json({ success: false, error: "Request not found" });

    const tx = await contract.confirmRequest(BigInt(requestId), { gasLimit: 200_000 });
    await tx.wait();
    res.json({ success: true, txHash: tx.hash });
  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, error: err.message });
  }
});

// --- CANCEL request ---
app.post("/api/cancel", async (req, res) => {
  try {
    const { privateKey, contractAddress, requestId, reason } = req.body;
    if(!contractAddress) return res.status(400).json({ success:false, error:"Contract address required" });

    const contract = getContract(contractAddress, privateKey);
    const pendingRequests = await contract.getPendingRequests();
    const exists = pendingRequests.some(r => r.id.toString() === requestId.trim());
    if (!exists) return res.status(400).json({ success: false, error: "Request not found" });

    const tx = await contract.cancelRequest(BigInt(requestId), reason, { gasLimit: 200_000 });
    await tx.wait();
    res.json({ success: true, txHash: tx.hash });
  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, error: err.message });
  }
});

// --- PENDING requests ---
app.post("/api/pending", async (req, res) => {
  try {
    const { privateKey, contractAddress } = req.body;
    if(!privateKey || !contractAddress) return res.status(400).json({ error: "Private key and contract address required" });

    const contract = getContract(contractAddress, privateKey);
    const pendingRequests = await contract.getPendingRequests();
    res.json(formatRequests(pendingRequests));
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// --- COMPLETED requests ---
app.post("/api/completed", async (req, res) => {
  try {
    const { privateKey, contractAddress } = req.body;
    if(!privateKey || !contractAddress) return res.status(400).json({ error: "Private key and contract address required" });

    const contract = getContract(contractAddress, privateKey);
    const confirmedRequests = await contract.getConfirmedRequests();
    res.json(formatRequests(confirmedRequests));
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// --- CANCELLED requests ---
app.post("/api/cancelled", async (req, res) => {
  try {
    const { privateKey, contractAddress } = req.body;
    if(!privateKey || !contractAddress) return res.status(400).json({ error: "Private key and contract address required" });

    const contract = getContract(contractAddress, privateKey);
    const cancelledRequests = await contract.getCancelledRequests();
    res.json(formatRequests(cancelledRequests));
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

app.listen(3000, () => console.log("Server running on http://localhost:3000"));
