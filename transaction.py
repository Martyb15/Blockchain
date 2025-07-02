class Transaction():
    def __init__(self, sender, receiver, amount): 
        self.sender = sender
        self.receiver = receiver
        self.amount = amount

    def to_dict(self): 
        ''' Convert transaction to dictionary for consistent serialization '''
        return {
            'sender':   self.sender, 
            'receiver': self.receiver,
            'amount':   self.amount
        }