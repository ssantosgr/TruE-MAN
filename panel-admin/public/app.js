let deployerKey = "";
let currentContractAddress = "";

function setupContractInput(inputId, btnId){
  const input = document.getElementById(inputId);
  const btn = document.getElementById(btnId);
  input.value = currentContractAddress;
  btn.onclick = async ()=>{
    if(input.readOnly){
      input.readOnly = false;
      input.focus();
      btn.textContent = "💾";
    } else {
      const newAddress = input.value.trim();
      if(!newAddress) { 
        alert("Contract address cannot be empty"); 
        input.value=currentContractAddress; 
        input.readOnly=true; 
        btn.textContent="✏️"; 
        return; 
      }
      showLoading("Validating contract...");
      try{
        const res = await fetch("/api/pending", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({privateKey:deployerKey, contractAddress:newAddress})
        });
        if(!res.ok) throw new Error("Contract address not found");
        await res.json();
        currentContractAddress=newAddress;
        document.getElementById("contractAddressInput").value = newAddress;
        updateTables();
      } catch(err){ 
        alert("Contract address not found."); 
        input.value=currentContractAddress; 
      }
      finally{ 
        hideLoading(); 
        input.readOnly=true; 
        btn.textContent="✏️"; 
      }
    }
  };
}
setupContractInput("contractAddressInput","contractEditBtn");

function showLoading(msg="Processing transaction..."){ 
  document.getElementById("loadingMessage").textContent = msg; 
  document.getElementById("loadingOverlay").style.display = "flex"; 
}
function hideLoading(){ 
  document.getElementById("loadingOverlay").style.display = "none"; 
}

function setDeployerKey(){ 
  const key = document.getElementById("deployerKeyModalInput").value.trim(); 
  if(!key) return alert("Private key is required!"); 
  deployerKey = key; 
  document.getElementById("keyModal").style.display = "none"; 
}

function clearTable(tbodySelector){ 
  const tbody = document.querySelector(tbodySelector); 
  tbody.innerHTML = ""; 
  const tr = document.createElement("tr"); 
  tr.innerHTML = `<td colspan="${tbodySelector==="#pendingTable tbody"?6:5}">No data</td>`; 
  tbody.appendChild(tr); 
}

async function confirmRequest(requestId){ 
  const c = document.getElementById("contractAddressInput").value; 
  if(!c) return; 
  showLoading("Confirming..."); 
  try{ 
    const res = await fetch("/api/confirm",{
      method:"POST", 
      headers:{"Content-Type":"application/json"}, 
      body: JSON.stringify({privateKey:deployerKey, contractAddress:c, requestId})
    }); 
    await res.json(); 
  } finally{ 
    hideLoading(); 
    updateTables();
  } 
}

async function cancelRequest(requestId){ 
  const reason = prompt("Enter reason:"); 
  if(reason===null) return; 
  const c = document.getElementById("contractAddressInput").value; 
  if(!c) return; 
  showLoading("Cancelling..."); 
  try{ 
    const res = await fetch("/api/cancel",{
      method:"POST", 
      headers:{"Content-Type":"application/json"}, 
      body: JSON.stringify({privateKey:deployerKey, contractAddress:c, requestId, reason})
    }); 
    await res.json(); 
  } finally{ 
    hideLoading(); 
    updateTables(); 
  } 
}

async function updateTables(){
  if(!deployerKey || !document.getElementById("contractAddressInput").value) return;
  await loadTable("/api/pending","#pendingTable tbody",true);
  await loadTable("/api/completed","#completedTable tbody",false);
  await loadTable("/api/cancelled","#cancelledTable tbody",false);
}

async function loadTable(api, tbodySelector, showActions=false){
  const contractAddress = document.getElementById("contractAddressInput").value;
  if(!contractAddress) return;
  const tbody = document.querySelector(tbodySelector); 
  tbody.innerHTML="";
  try{
    const res = await fetch(api,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({privateKey:deployerKey, contractAddress})
    });
    if(!res.ok) throw new Error("Contract address not found"); 
    const data = await res.json();
    if(!data || data.length===0){ 
      clearTable(tbodySelector); 
      return; 
    }
    data.forEach(r=>{
      const tr=document.createElement("tr");
      tr.innerHTML=`<td>${r.id}</td><td>${r.buyer}</td><td>${r.numUsers}</td><td>${r.durationMins} mins</td><td>${r.amount} ETH</td>`;
      if(showActions){ 
        const actions=document.createElement("td"); 
        const acceptBtn=document.createElement("span"); 
        acceptBtn.textContent="✅"; 
        acceptBtn.className="action-btn"; 
        acceptBtn.onclick=()=>confirmRequest(r.id); 
        const cancelBtn=document.createElement("span"); 
        cancelBtn.textContent="❌"; 
        cancelBtn.className="action-btn"; 
        cancelBtn.onclick=()=>cancelRequest(r.id); 
        actions.appendChild(acceptBtn); 
        actions.appendChild(cancelBtn); 
        tr.appendChild(actions); 
      }
      tbody.appendChild(tr);
    });
  }catch(err){ 
    alert("Error loading data: contract may not exist"); 
  }
}

window.onload = ()=>{
  document.getElementById("keyModal").style.display="flex"; 
  updateTables(); 
};
