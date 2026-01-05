const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const { getContract, formatRequests } = require("../shared/shared");

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, "public")));

// Helper function to retry fetch with exponential backoff
async function fetchWithRetry(url, options, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return response;
      throw new Error(`HTTP ${response.status}`);
    } catch (err) {
      if (i === retries - 1) throw err;
      const delay = Math.pow(2, i) * 1000; // 1s, 2s, 4s
      console.log(`Retry ${i + 1}/${retries} after ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

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
    
    // Update middleware state to accepted
    try {
      await fetchWithRetry(`http://localhost:5000/api/request/${tx.hash}/accepted`, {
        method: 'PATCH'
      });
    } catch (err) {
      console.error("Failed to update middleware state after 3 retries:", err.message);
    }
    
    res.json({ success: true, txHash: tx.hash, message: "Request confirmed" });
  } catch (e) { res.status(500).json({ error: e.message }); }
  
});

// --- CANCEL request ---
app.post("/api/cancel", async (req, res) => {
  try {
    const { privateKey, contractAddress, requestId, reason } = req.body;
    const contract = getContract(contractAddress, privateKey);
    const tx = await contract.cancelRequest(BigInt(requestId), reason);
    await tx.wait();
    
    // Update middleware state to rejected
    try {
      await fetchWithRetry(`http://localhost:5000/api/request/${tx.hash}/rejected`, {
        method: 'PATCH'
      });
    } catch (err) {
      console.error("Failed to update middleware state after 3 retries:", err.message);
    }
    
    res.json({ success: true, txHash: tx.hash, message: "Request cancelled" });
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
