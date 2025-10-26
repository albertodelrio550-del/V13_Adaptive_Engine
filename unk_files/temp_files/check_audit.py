from V13_CommandMatrix import V13_CommandMatrix

matrix = V13_CommandMatrix()
audit = matrix.check_audit_state()

print("Audit State:")
for component, details in audit.items():
    print(f"{component}: {details['status']} - {details['description']}")
