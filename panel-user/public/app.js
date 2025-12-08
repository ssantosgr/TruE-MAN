let deployerKey = "";

function showLoading(msg = "Processing transaction...") {
  document.getElementById("loadingMessage").textContent = msg;
  document.getElementById("loadingOverlay").style.display = "flex";
}
function hideLoading() {
  document.getElementById("loadingOverlay").style.display = "none";
}

function setDeployerKey() {
  const key = document.getElementById("deployerKeyModalInput").value.trim();
  if (!key) return alert("Private key is required!");
  deployerKey = key;
  document.getElementById("keyModal").style.display = "none";
}

function getContractAddressCreate() {
  return document.getElementById("contractAddressInputCreate").value.trim();
}

async function createRequest() {
  const contractAddress = getContractAddressCreate();
  if (!contractAddress) {
    alert("Please enter contract address!");
    return;
  }

  const numUsers = parseInt(document.getElementById("numUsers").value);
  const durationMins = parseInt(document.getElementById("durationMins").value);
  const offChainData = document.getElementById("offChainData").value;

  if (!numUsers || !durationMins) {
    alert("Please fill all fields!");
    return;
  }

  showLoading("Creating request...");

  try {
    const res = await fetch("/api/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        privateKey: deployerKey,
        contractAddress,
        numUsers,
        durationMins,
        offChainData
      })
    });

    const data = await res.json();
    alert(JSON.stringify(data, null, 2));
    
  } finally {
    hideLoading();
  }
}

window.onload = () => {
  document.getElementById("keyModal").style.display = "flex";
};
