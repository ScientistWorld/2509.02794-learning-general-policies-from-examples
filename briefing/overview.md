# Overview

- **Paper ID:** 2509.02794
- **Title:** Learning General Policies From Examples
- **Domain:** Symbolic AI planning / generalized planning
- **TL;DR:** The paper learns compact rule-based planning policies from example
  plans using a hitting-set algorithm with built-in structural termination.

## Short Summary

The paper targets generalized planning: learning one policy that solves a whole
family of planning instances. It replaces earlier SAT/ASP policy learners with
GENEX, a greedy hitting-set method that selects features and preserves
stratified termination. A WRAPPER procedure supplies positive and negative
transitions from planner rollouts until the policy is closed and safe on the
training set.

## Key Results

- The paper reports policies for 20 of 34 evaluated planning domains.
- Gripper is solved in the paper with one outer and one inner WRAPPER iteration,
  three selected features, four rules, and 100% large-instance coverage.
- Many learned policies retain effective width 0 on larger instances, meaning
  they act as direct policies rather than sketches needing additional search.
