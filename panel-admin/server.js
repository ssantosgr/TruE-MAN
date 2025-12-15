const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const { getContract, formatRequests } = require("../shared/shared");

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, "public")));

// --- GET PENDING requests ---
app.post("/api/pending", async (req, res) => {
  try {
    const { privateKey, contractAddress } = req.body;
    const contract = getContract(contractAddress, privateKey);
    const pending = await contract.getPendingRequests();
    res.json(formatRequests(pending));
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// --- CONFIRM request ---
app.post("/api/confirm", async (req, res) => {
  try {
    const { privateKey, contractAddress, requestId } = req.body;
    const contract = getContract(contractAddress, privateKey);
    const tx = await contract.confirmRequest(BigInt(requestId));
    await tx.wait();

    // Update middleware status
    try {
      await fetch("http://localhost:5000/api/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accepted: true, requestId: requestId.toString() }),
      });
    } catch (err) {
      console.error("Failed to update middleware status:", err);
    }

    res.json({ success: true, txHash: tx.hash });
  } catch (e) { res.status(500).json({ error: e.message }); }
  
});

// --- CANCEL request ---
app.post("/api/cancel", async (req, res) => {
  try {
    const { privateKey, contractAddress, requestId, reason } = req.body;
    const contract = getContract(contractAddress, privateKey);
    const tx = await contract.cancelRequest(BigInt(requestId), reason);
    await tx.wait();
    res.json({ success: true, txHash: tx.hash });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// --- GET COMPLETED requests ---
app.post("/api/completed", async (req, res) => {
  try {
    const { privateKey, contractAddress } = req.body;
    const contract = getContract(contractAddress, privateKey);
    const done = await contract.getConfirmedRequests();
    res.json(formatRequests(done));
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// --- GET CANCELLED requests ---
app.post("/api/cancelled", async (req, res) => {
  try {
    const { privateKey, contractAddress } = req.body;
    const contract = getContract(contractAddress, privateKey);
    const cancelled = await contract.getCancelledRequests();
    res.json(formatRequests(cancelled));
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.listen(3010, () =>
  console.log("Admin panel running at http://localhost:3010")
);
