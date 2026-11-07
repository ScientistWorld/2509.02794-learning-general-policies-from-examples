from method.audit_support import write_policy
write_policy({'selected_features': ['optimal_distance'],
              'rules': [{'condition': [], 'effects': [['optimal_distance', 'down']]}]})
