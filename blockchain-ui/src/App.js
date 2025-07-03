import React, { useState, useEffect } from "react";
import axios from "axios";
import wallet from "./wallet.json"; 

function App() {
  const miner = wallet.pub;

  // Faucet
  const [faucetAddr, setFaucetAddr] = useState(miner);
  const [balance, setBalance]       = useState(null);

  // Chain
  const [chain, setChain] = useState([]);

  // Send form
  const [recipient, setRecipient] = useState("");
  const [amount, setAmount]       = useState("");
  const [fee, setFee]             = useState("");

  // Load chain & balance on mount
  useEffect(() => {
    fetchChain();
    fetchBalance();
  }, []);

  const fetchChain = () => {
    axios
      .get("/chain")
      .then((res) => setChain(res.data))
      .catch((err) => console.error("Error fetching chain:", err));
  };

  const fetchBalance = () => {
    axios
      .get(`/balance/${miner}`)
      .then((res) => setBalance(res.data.balance))
      .catch((err) => console.error("Error fetching balance:", err));
  };

  // Faucet handler
  const handleFaucet = () => {
    if (!faucetAddr) return alert("Please enter an address to fund.");
    axios
      .post("/faucet", { address: faucetAddr, amount: 50000000 })
      .then((res) => {
        setBalance(res.data.amount);
        alert(`Funded ${faucetAddr} with 50 000 000 units`);
      })
      .catch((err) => {
        console.error(err);
        alert("Faucet failed");
      });
  };

  // Send & mine (placeholder—backend must sign/validate)
  const handleSendAndMine = async () => {
    try {
      // 1) Submit transaction to backend
      await axios.post("/tx", {
        tx_type:   "PAY",
        sender:    wallet.pub,
        recipient: recipient,
        amount:    Number(amount),
        fee:       Number(fee),
        nonce:     1,          // for demo;
        payload:   null,
        signature: wallet.priv, // 
      });
      // 2) Trigger mining
      await axios.post("/mine", null, { params: { miner } });

      alert("Transaction sent & mined!");
      fetchChain();
      fetchBalance();
    } catch (err) {
      console.error(err);
      alert("Send/Mine error: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div style={{ padding: 20, maxWidth: 600, margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1>Mini Blockchain UI</h1>

      {/* Faucet */}
      <section style={{ marginBottom: 32 }}>
        <h2>Faucet</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="text"
            placeholder="Address to fund"
            value={faucetAddr}
            onChange={(e) => setFaucetAddr(e.target.value)}
            style={{ flexGrow: 1, padding: 8, fontSize: 14 }}
          />
          <button onClick={handleFaucet} style={{ padding: "8px 16px", fontSize: 14 }}>
            Fund
          </button>
        </div>
        {balance !== null && (
          <p style={{ marginTop: 8, fontWeight: "bold" }}>Balance: {balance}</p>
        )}
      </section>

      {/* Chain */}
      <section style={{ marginBottom: 32 }}>
        <h2>Blockchain</h2>
        <ul style={{ paddingLeft: 16 }}>
          {chain.map((h, i) => (
            <li key={i} style={{ fontFamily: "monospace", fontSize: 12, margin: "4px 0" }}>
              {h}
            </li>
          ))}
        </ul>
      </section>

      {/* Send & Mine */}
      <section style={{ marginBottom: 32 }}>
        <h2>Send & Mine Transaction</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 400 }}>
          <input
            type="text"
            placeholder="Recipient address"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            style={{ padding: 8, fontSize: 14 }}
          />
          <input
            type="number"
            placeholder="Amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            style={{ padding: 8, fontSize: 14 }}
          />
          <input
            type="number"
            placeholder="Fee"
            value={fee}
            onChange={(e) => setFee(e.target.value)}
            style={{ padding: 8, fontSize: 14 }}
          />
          <button onClick={handleSendAndMine} style={{ padding: "8px 16px", fontSize: 14 }}>
            Send & Mine
          </button>
        </div>
      </section>
    </div>
  );
}

export default App;
