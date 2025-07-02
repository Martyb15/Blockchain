from block import Block

class Blockchain: 
    def __init__(self):
        # Initialize blockchain with a genesis block
        self.chain = [self.create_genesis_block()]
        self.difficulty = 2                           # difficulty determined by leading zeros
        self.pending_transactions = []
        self.mining_reward = 50 

    def create_genesis_block(self): 
        return Block(0,[], "0")

    def get_latest_block(self):
        return self.chain[-1]
    
    def create_transaction(self, tx): 
        self.pending_transactions.append(tx)

    def mine_block(self, block): 
        ''' Mine block by adjusting the "number_used_once" untile hash meets difficulty '''
        target = "0" * self.difficulty
        while block.hash[:self.difficulty] != target:
            block.self.number_used_once += 1
            block.hash = block.calculate_hash()

        print(f"Block mined: {block.hash}")

    def mine_pending_transaction(self, miner_address):
        ''' Mine new block with pending transactions (rewards miner)'''
        reward_tx = Transaction("SYSTEM", miner_address, self.mining_reward)
        block = Block(len(self.chain), transaction=self.pending_transactions, previous_hash=self.get_latest_block().hash)

        self.pending_transactions = []

    def is_chain_valid(self): 
        ''' Verifies the integrity of the blockchain'''
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False
            
            if current.previous_hash != prev.hash:
                return False
            
            if not current.hash.startswith("0" * self.difficulty):
                return False
            
        return True


