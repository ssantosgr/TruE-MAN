const fs = require("fs");
const { ethers } = require("ethers");
const path = require("path");

const provider = new ethers.JsonRpcProvider("http://localhost:8545"); // blockchain's RPC node

const abiPath = path.join(__dirname, "../contracts/contract1/contract1.abi.json");
const contractAbi = JSON.parse(fs.readFileSync(abiPath, "utf8"));

function getWallet(privateKey) {
  return new ethers.Wallet(privateKey.trim(), provider);
}

function getContract(contractAddress, privateKey) {
  return new ethers.Contract(contractAddress, contractAbi, getWallet(privateKey));
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

module.exports = {
  provider,
  getWallet,
  getContract,
  formatRequests
};
