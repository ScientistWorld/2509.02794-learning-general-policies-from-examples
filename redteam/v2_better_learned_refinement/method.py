from method.audit_support import reference_policy, write_policy
from method.audit_refine import refine
write_policy(refine(reference_policy()))
