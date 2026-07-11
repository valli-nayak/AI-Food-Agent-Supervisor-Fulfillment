from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Literal, TypedDict, Optional
from pydantic import BaseModel, Field
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LANG_CHAIN_API_KEY = os.getenv("LANG_CHAIN_API_KEY")

if not GOOGLE_API_KEY:
    st.error("❌ Missing GOOGLE_API_KEY in the environment setup.")
    st.stop() 

if not os.getenv("LANG_CHAIN_API_KEY"):
    st.error("❌ Misiing LANG_CHAIN_API_KEY in the environment setup.")
    st.stop()    

llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", max_retries=6)

class OrderPayload(BaseModel):
    user_id:int
    dish:str

InventoryStatus = Literal["SUCCESS", "CONFLICT_LOCKED", "OUT_OF_STOCK", "PENDING"]
BillingStatus = Literal["SUCCESS", "DECLINED", "PENDING"]
GraphNodeTargets = Literal["ParallelValidate", "Kitchen", "Shipping", "RollbackInventory", "FINISH"]

class FulfillmentState(TypedDict):
    request: str                                   # The raw text order input
    dish_name: str                                 # Target recipe name
    order_parsed: Optional[bool]                   # Data parsing completion tracking flag
    inventory_log: InventoryStatus                 
    billing_log: BillingStatus     
    inventory_token: str                           # Tracks client ownership of the lease                
    next_action: GraphNodeTargets                  
    order_shipped: Optional[bool]
    cooked: Optional[bool]

class ParallelSupervisorRouter(BaseModel):
    reasoning: str = Field(description="Business logic explanation.")
    next_action: GraphNodeTargets = Field(description="Next node target")
   
