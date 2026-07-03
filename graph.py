from langgraph.graph import StateGraph, END, START
from config import FulfillmentState
from nodes import (
    supervisor_node, 
    parse_and_validate_track, 
    kitchen_node, 
    shipping_node, 
    compensation_router_node, 
    rollback_inventory_node
)

def route_supervisor_next_step(state:FulfillmentState):
    if state["next_action"] == "FINISH":
        return "FINISH"
    else:
        return state["next_action"]  
    
workflow = StateGraph(FulfillmentState)
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("ParallelValidate", parse_and_validate_track)
workflow.add_node("Kitchen", kitchen_node)
workflow.add_node("Shipping", shipping_node)
workflow.add_node("Compensation", compensation_router_node)
workflow.add_node("RollbackInventory", rollback_inventory_node)

workflow.add_edge(START, "Supervisor")
workflow.add_edge("ParallelValidate", "Supervisor")
workflow.add_edge("Kitchen", "Supervisor")
workflow.add_edge("Shipping", "Supervisor")
workflow.add_edge("RollbackInventory", "Supervisor")
workflow.add_edge("Compensation", "Supervisor")

workflow.add_conditional_edges(
    "Supervisor",
    route_supervisor_next_step,
    {
        "ParallelValidate": "ParallelValidate",
        "Kitchen": "Kitchen",
        "Compensation": "Compensation",
        "Shipping":"Shipping",
        "FINISH": END
    }
)

app = workflow.compile()
