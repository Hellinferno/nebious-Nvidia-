export type SampleProjectDef = {
  id: string
  name: string
  tag: 'Bug Fix' | 'Feature' | 'Prepared Fixture'
  description: string
  isFixture?: boolean
  fixtureId?: string
  files: Record<string, string>
  suggestedPrompt: string
  defaultEditablePaths: string[]
  runnerProfile: string
}

export const SAMPLE_PROJECTS: SampleProjectDef[] = [
  {
    id: 'sample-calc',
    name: 'StringCalculator',
    tag: 'Bug Fix',
    description: 'StringCalculator service with negative number exception handling bug',
    suggestedPrompt:
      "Fix the bug in add(): negative numbers must raise a ValueError with message 'negatives not allowed: [...]' containing the list of negative numbers.",
    defaultEditablePaths: ['app/calculator.py'],
    runnerProfile: 'unittest',
    files: {
      'app/calculator.py': `def add(numbers: str) -> int:
    if not numbers.strip():
        return 0
    parts = [int(p.strip()) for p in numbers.split(',') if p.strip()]
    # Bug: ignores negative check and returns sum anyway
    return sum(parts)
`,
      'tests/test_calculator.py': `import unittest
from app.calculator import add

class TestStringCalculator(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(add(''), 0)

    def test_single_and_two_numbers(self):
        self.assertEqual(add('1'), 1)
        self.assertEqual(add('1, 2'), 3)

    def test_negative_raises_value_error(self):
        with self.assertRaises(ValueError):
            add('1, -2, 3')

if __name__ == '__main__':
    unittest.main()
`,
    },
  },
  {
    id: 'sample-bank',
    name: 'BankAccount',
    tag: 'Feature',
    description: 'BankAccount domain model requiring transfer method with balance bounds',
    suggestedPrompt:
      'Implement the transfer(target: BankAccount, amount: int) method on BankAccount: withdraw from self and deposit into target, raising ValueError on insufficient funds or non-positive amount.',
    defaultEditablePaths: ['app/account.py'],
    runnerProfile: 'unittest',
    files: {
      'app/account.py': `class BankAccount:
    def __init__(self, owner: str, initial_balance: int = 0) -> None:
        if initial_balance < 0:
            raise ValueError('Initial balance cannot be negative')
        self.owner = owner
        self.balance = initial_balance

    def deposit(self, amount: int) -> int:
        if amount <= 0:
            raise ValueError('Deposit amount must be positive')
        self.balance += amount
        return self.balance

    def withdraw(self, amount: int) -> int:
        if amount <= 0:
            raise ValueError('Withdrawal amount must be positive')
        if amount > self.balance:
            raise ValueError('Insufficient funds')
        self.balance -= amount
        return self.balance
`,
      'tests/test_account.py': `import unittest
from app.account import BankAccount

class TestBankAccountFeature(unittest.TestCase):
    def test_transfer_to_another_account(self):
        alice = BankAccount('Alice', 100)
        bob = BankAccount('Bob', 50)
        alice.transfer(bob, 40)
        self.assertEqual(alice.balance, 60)
        self.assertEqual(bob.balance, 90)

    def test_transfer_insufficient_funds(self):
        alice = BankAccount('Alice', 30)
        bob = BankAccount('Bob', 50)
        with self.assertRaises(ValueError):
            alice.transfer(bob, 40)

if __name__ == '__main__':
    unittest.main()
`,
    },
  },
  {
    id: 'sample-mc01',
    name: 'MC-01 Invoice',
    tag: 'Prepared Fixture',
    description: 'Prepared invoice fixture evaluated under protected contract rules',
    isFixture: true,
    fixtureId: 'MC-01',
    suggestedPrompt:
      'Fix invoice total calculation to respect item quantities and unit price boundaries without modifying protected checks.',
    defaultEditablePaths: ['app/invoice.py'],
    runnerProfile: 'unittest',
    files: {
      'app/invoice.py': `# Prepared MC-01 Invoice service module
def calculate_invoice_total(items: list[dict]) -> float:
    total = 0.0
    for item in items:
        # Bug: incorrectly calculates tax and discounts at boundary
        total += item.get('price', 0.0) * item.get('quantity', 1)
    return round(total, 2)
`,
      'tests/test_invoice.py': `# Protected acceptance verification checks
import unittest
from app.invoice import calculate_invoice_total

class TestInvoice(unittest.TestCase):
    def test_item_total_boundary(self):
        self.assertEqual(calculate_invoice_total([{'price': 10.0, 'quantity': 2}]), 20.0)

if __name__ == '__main__':
    unittest.main()
`,
    },
  },
]
