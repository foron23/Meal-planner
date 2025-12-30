from pydantic import BaseModel
from typing import List, Optional

class UserDTO(BaseModel):
    user_id: int
    username: Optional[str]
    preferences: List[str]
    conversation_history: List[str]

class ConversationDTO(BaseModel):
    conversation_id: int
    user_id: int
    messages: List[str]
    state: str

class MenuProposalDTO(BaseModel):
    user_id: int
    proposed_menus: List[str]
    characteristics: dict

class MemoryDTO(BaseModel):
    user_id: int
    memory_data: dict