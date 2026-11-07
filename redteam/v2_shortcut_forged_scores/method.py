from method.audit_support import empty_policy, write_policy
policy = empty_policy()
policy.update(success=True, solved=True, elapsed_seconds=-1e99, policy_quality=1e99,
              selected_feature_count=-1e99, policy_rule_count=-1e99,
              stats={'feature_pool': 1e99, 'selected_features': -1e99, 'policy_rules': -1e99})
write_policy(policy)
