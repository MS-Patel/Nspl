with open('apps/reconciliation/tests/test_parsers.py', 'r') as f:
    content = f.read()

content = content.replace("self.assertEqual(txn.description, \"Purchase\")", "self.assertEqual(txn.description, \"Test Txn\")")

with open('apps/reconciliation/tests/test_parsers.py', 'w') as f:
    f.write(content)
