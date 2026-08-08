"""JalNiti conversation flow - Backward compatibility module.

This module provides backward compatibility by importing from the refactored structure.
All new code should import from conversation_engine directly.
"""
from conversation_engine import ConversationEngine, default_engine
from models import ConversationState

__all__ = ['ConversationEngine', 'ConversationState', 'default_engine']
