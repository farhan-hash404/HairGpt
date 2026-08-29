"""Stratified model evaluation.

A model is not promoted on aggregate accuracy. It is promoted only when its
WORST subgroup is good enough, because an aggregate number can hide a model
that works well for most people and badly for some — which in a health product
is the failure that matters.
"""
