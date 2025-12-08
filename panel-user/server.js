const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const { ethers } = require("ethers");
const { getWallet, getContract } = require("../shared/shared");

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, "public")));

app.post("/api/create", async (req, res) => {
  try {
    const { privateKey, contractAddress, numUsers, durationMins, offChainData } = req.body;

    const contract = getContract(contractAddress, privateKey);
    const wallet = getWallet(privateKey);

    const requestHash = ethers.keccak256(ethers.toUtf8Bytes(offChainData || ""));
    const ratePerMinuteWei = ethers.parseEther("0.00012");
    const requiredPayment =
      ratePerMinuteWei * BigInt(durationMins) * BigInt(numUsers);

    const tx = await contract.createRequest(wallet.address, numUsers, durationMins, requestHash, {
      value: requiredPayment,
    });

    await tx.wait();
    const requestId = (await contract.nextRequestId()) - 1n;

    res.json({
      success: true,
      requestId: requestId.toString(),
      txHash: tx.hash,
      message: "Request created"
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(3020, () =>
  console.log("User panel running at http://localhost:3020")
);
