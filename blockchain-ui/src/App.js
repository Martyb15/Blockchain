import React, { useState, useEffect } from "react";
import axios from "axios";
import wallet from "./wallet.json";
import "./App.css";

function App() {
  const miner = wallet.pub;
  const [faucetAddr, setFaucetAddr] = useState(miner);
  const [balance, setBalance]       = useState(null);
  const [chain, setChain]           = useState([]);
  const [recipient, setRecipient]   = useState("");
  const [amount, setAmount]         = useState("");
  const [fee, setFee]               = useState("");

  useEffect(() => {
    fetchChain();
    fetchBalance();
  }, []);

  const fetchChain = () => {
    axios.get("/chain").then((res) => setChain(res.data));
  };
  const fetchBalance = () => {
    axios.get(`/balance/${miner}`).then((res) => setBalance(res.data.balance));
  };

  const handleFaucet = () => {
    if (!faucetAddr) return alert("Please enter an address to fund.");
    axios.post("/faucet", { address: faucetAddr, amount: 50000000 })
      .then(res => {
        setBalance(res.data.amount);
        alert(`Funded ${faucetAddr} with 50 000 000 units`);
      });
  };

  const handleSendAndMine = async () => {
    const balanceRes = await axios.get(`/balance/${wallet.pub}`};
    const currentNonce = balanceRes.data.nonce || 0;
  
    await axios.post("/tx", {
      tx_type: "PAY",
      sender:  wallet.pub,
      recipient,
      amount:   Number(amount),
      fee:      Number(fee),
      nonce:    1,
      payload:  null,
      signature: wallet.priv,
    });
    await axios.post("/mine", null, { params: { miner } });
    alert("Transaction sent & mined!");
    fetchChain();
    fetchBalance();
  };

  return (
    <div className="App">
      <h1>Mini Blockchain UI</h1>

      <section>
        <h2>Faucet</h2>
        <div className="flex">
          <input
            placeholder="Address to fund"
            value={faucetAddr}
            onChange={e => setFaucetAddr(e.target.value)}
          />
          <button onClick={handleFaucet}>Fund</button>
        </div>
        {balance !== null && (
          <p className="balance">Balance: {balance}</p>
        )}
      </section>

      <section>
        <h2>Blockchain</h2>
        <ul className="chain-list">
          {chain.map((h, i) => (
            <li key={i} className="text-mono">
              {h}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Send &amp; Mine Transaction</h2>
        <div className="flex-column">
          <input
            placeholder="Recipient address"
            value={recipient}
            onChange={e => setRecipient(e.target.value)}
          />
          <input
            type="number"
            placeholder="Amount"
            value={amount}
            onChange={e => setAmount(e.target.value)}
          />
          <input
            type="number"
            placeholder="Fee"
            value={fee}
            onChange={e => setFee(e.target.value)}
          />
          <button onClick={handleSendAndMine}>Send &amp; Mine</button>
        </div>
      </section>
    </div>
  );
}

export default App;
