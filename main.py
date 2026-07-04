import os
import asyncio
import pandas as pd
from fastapi import FastAPI
from config import OrderPayload
from graph import app

backend_app = FastAPI()

async def run_single_user_graph(user_id: int, dish:str):
    """Simulates one independent customer firing a request into the graph pipeline."""
    print(f"🚀 [User {user_id}] Entering the graph pipeline loop...")
    
    initial_state = { 
        "request": f"User {user_id} wants to order one {dish}.", 
        "dish_name": f"{dish}", 
        "order_parsed": None, 
        "inventory_log": "PENDING", 
        "billing_log": "PENDING", 
        "inventory_token": "", 
        "next_action": "ParallelValidate",  
        "order_shipped": None, 
        "cooked": None 
    } 

    config = {"configurable":{"thread_id":f"session_{user_id}"}}
    
    # Run this specific user through the graph asynchronously
    final_output = await app.ainvoke(initial_state, config=config) 
    
    print(f"🏁 [User {user_id}] Workflow Closed. Final Inventory Status: {final_output.get('inventory_log')}")
    return final_output

@backend_app.post("/simulate")
async def simulate_dual_users(payloads: list[OrderPayload]):
    # 1. Clear out any old lock remnants from previous testing crashes
    if os.path.exists("inventory_lock.lock"):
        os.remove("inventory_lock.lock")
        
    print("📊 Current starting database numbers before the rush:")
    print(pd.read_csv("inventory.csv").to_string(index=False))
    print("\n💥 Colliding User 1 and User 2 at the exact same millisecond...\n")

    # 2. Fire BOTH users into the compiled graph engine at the exact same fraction of a second
    results = await asyncio.gather(
        run_single_user_graph(user_id=payloads[0].user_id, dish=payloads[0].dish),
        run_single_user_graph(user_id=payloads[1].user_id, dish=payloads[1].dish)
    )
    
    print("\n📊 Final state of inventory.csv database after both workflows settled:")
    print(pd.read_csv("inventory.csv").to_string(index=False))

    return results

@backend_app.get("/inventory")
def get_inventory():
    if os.path.exists("inventory.csv"):
        return pd.read_csv("inventory.csv").to_dict(orient="records")
    return []  
