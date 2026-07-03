import uuid
import asyncio
from langchain_core.messages import HumanMessage
from config import FulfillmentState, ParallelSupervisorRouter, llm
from lock_manager import CSVInventoryLockManager

def supervisor_node(state:FulfillmentState) -> FulfillmentState:
    print(f"\n🧠 [Supervisor Node] Telemetry Auditing: Parsed={state.get('order_parsed')}, Billing={state.get('billing_log')}, Inventory={state.get('inventory_log')}, Cooked={state.get('cooked')}, Shipped={state.get('order_shipped')}")

    if state.get("next_action") == "FINISH":
        return state
    
    prompt = (
        f"Analyze this context: {state.get('request', '')}. "
        f"Current Order Parsed Token State: {state.get('order_parsed')}. "
        f"Current Billing Log: {state.get('billing_log')}. "
        f"Current Inventory Log: {state.get('inventory_log')}. "
        f"Current Cooking State: {state.get('cooked')}. "
        f"Current Order Shipped State: {state.get('order_shipped')}. "
        "Rules:\n"
        "1. If order_parsed is missing or None, you MUST select next_action='ParallelValidate' and suggested_compensation='NONE'.\n"
        "2. If inventory_log is 'CONFLICT_LOCKED' or 'OUT_OF_STOCK' you MUST select next_action='Compensation' and suggested_compensation='NONE'.\n"
        "3. If billing_log is 'DECLINED' and inventory_log is 'SUCCESS', you MUST select next_action='Compensation' and suggested_compensation='RELEASE_INVENTORY_LEASE'.\n"
        "4. If BOTH inventory_log and billing_log are 'SUCCESS' and cooked is NOT True, you MUST select next_action='Kitchen' and suggested_compensation='NONE'.\n"
        "5. If cooked is True and order_shipped is NOT True, you MUST select next_action='Shipping' and suggested_compensation='NONE'.\n"
        "6. If order_shipped is True, you MUST select next_action='FINISH' and suggested_compensation='NONE'.")
    
    
    # Constrain the model natively to the router schema
    structured_llm = llm.with_structured_output(ParallelSupervisorRouter)
    decision = structured_llm.invoke([HumanMessage(content=prompt)])
    state["next_action"] = decision.next_action
    state["suggested_compensation"] = decision.suggested_compensation

    print(f" |- LLM Reasoning: {decision.reasoning}")
    print(f" |- Route Target: {decision.next_action}")
    print(f" |- Rollback Rule: {decision.suggested_compensation}")
    return state

async def check_inventory(lock_manager, dish_name, client_token):
    return lock_manager.acquire_lease(dish_name, client_token)

async def check_billing():
    await asyncio.sleep(0.1)
    return "SUCCESS"

async def parse_and_validate_track(state:FulfillmentState):
    state["order_parsed"] = True
    lock_manager = CSVInventoryLockManager()
    client_token = str(uuid.uuid4())
    
    inv_res, bill_res = await asyncio.gather(check_inventory(lock_manager, state["dish_name"], client_token), check_billing())

    if inv_res == 'SUCCESS':
        state["inventory_token"] = client_token

    state["inventory_log"] = inv_res
    state["billing_log"] = bill_res 

    return state

def kitchen_node(state: FulfillmentState):
    print(f"🍳 [Kitchen Node] Plating dish '{state['dish_name']}'. Decrementing CSV count rows...")
    lock_manager = CSVInventoryLockManager()
    lock_manager.commit_deduction(state["dish_name"], state["inventory_token"])
    state["cooked"] = True
    return state
    
def shipping_node(state: FulfillmentState) -> FulfillmentState:
    print("🚚 [Shipping Node] Transport carrier routed. Manifest complete.")
    state["order_shipped"] = True
    return state

def compensation_router_node(state:FulfillmentState):
    print(f"🛑 [HUMAN_EXCEPTION] Structural exception node hit. State locked down.")
    if state["suggested_compensation"] == 'RELEASE_INVENTORY_LEASE':
        state["next_action"] = "RollbackInventory"
    else:
        state["next_action"] = "FINISH"
    return state        

def rollback_inventory_node(state:FulfillmentState):
    print(f"🔄 [RollbackInventory] Initializing Saga Compensation. Tearing down file lock footprints...")
    lock_manager = CSVInventoryLockManager()
    lock_manager.release_lock(state.get("inventory_token", "NONE"))
    state["inventory_log"] = "RELEASED_VIA_ROLLBACK"
    state["next_action"] = "FINISH"
    return state
