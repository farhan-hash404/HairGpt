"""HairGPT backend package.

Multimodal hair/scalp and skin analysis platform. This package deliberately
separates deterministic CV/observation/safety logic from the LLM, which is used
only to phrase explanations over already-structured, confidence-tagged data.
"""

__version__ = "0.1.0-mvp"
