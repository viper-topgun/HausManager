// MongoDB init script – creates the hausmanager user and sets up collections
db = db.getSiblingDB('hausmanager');

db.createCollection('owners');
db.createCollection('accounts');
db.createCollection('transactions');

print('HausManager database initialized.');
