#!/usr/bin/env python3
"""
Quick test of new security frameworks.
"""

from pathlib import Path
from pillars.owasp_agentic import check_owasp_agentic
from pillars.nist_ai_rmf import check_nist_ai_rmf
from pillars.mlsec_top10 import check_mlsec_top10

# Create test skill with various issues
test_skill = Path("/tmp/test_agentic_skill")
test_skill.mkdir(exist_ok=True)

# Test file with agentic issues
(test_skill / "agent.py").write_text("""
import pickle

def agent_loop():
    # AGENT01: Unbounded autonomy
    while True:
        action = llm.generate(prompt)  # No cost limit
        execute(action)

# AGENT02: No tool auth
def delete_file(path):
    os.remove(path)  # No authorization!

# AGENT03: Planning injection
user_goal = input()
plan = f"Your goal is: {user_goal}"

# AGENT07: Credential leak
api_key = "sk-..."
memory.append(api_key)

# MLSEC07: Unsafe deserialization
model = pickle.load(open('model.pkl', 'rb'))

# NIST: No transparency
prediction = model.predict(data)
return prediction  # No explanation
""")

print("Testing OWASP Agentic...")
agentic_findings = check_owasp_agentic(test_skill)
print(f"  Found {len(agentic_findings)} issues:")
for f in agentic_findings[:5]:
    print(f"    - {f.type}: {f.message}")

print("\nTesting NIST AI RMF...")
nist_findings = check_nist_ai_rmf(test_skill)
print(f"  Found {len(nist_findings)} issues:")
for f in nist_findings[:5]:
    print(f"    - {f.type}: {f.message}")

print("\nTesting ML Security...")
mlsec_findings = check_mlsec_top10(test_skill)
print(f"  Found {len(mlsec_findings)} issues:")
for f in mlsec_findings[:5]:
    print(f"    - {f.type}: {f.message}")

total = len(agentic_findings) + len(nist_findings) + len(mlsec_findings)
print(f"\n✅ Total findings from new frameworks: {total}")
print(f"   OWASP Agentic: {len(agentic_findings)}")
print(f"   NIST AI RMF: {len(nist_findings)}")
print(f"   ML Security: {len(mlsec_findings)}")
