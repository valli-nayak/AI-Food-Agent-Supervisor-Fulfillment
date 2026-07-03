import streamlit as st
import httpx
import pandas as pd

st.title("AI Food Fulfillment Supervisor Concurrency Monitor")
st.sidebar.subheader("📊 Live Database State")

BACKEND_URL="http://localhost:8000"

try:
    inv_data = httpx.get(f"{BACKEND_URL}/inventory").json()
    st.sidebar.dataframe(pd.DataFrame(inv_data), use_container_width=True)
except Exception:
    st.sidebar.warning("API Connection offline.")


dish1 = st.text_input("User 1 Request:", "Surnali")
dish2 = st.text_input("User 2 Request:", "Surnali")

if st.button("Trigger Concurrency Test", type="primary"):
    with st.spinner("Firing workflows... Watch backend terminal logs for console output!"):
        payload = [
            {"user_id": 1, "dish": dish1},
            {"user_id": 2, "dish": dish2}
        ]
        
        # Execute the simulation across the network
        response = httpx.post(f"{BACKEND_URL}/simulate", json=payload, timeout=60.0)
        
        st.success("Simulation Complete! Payloads returned below:")
        results = response.json()

        user_1_output = results[0]
        user_2_output = results[1] 

        col1,col2 = st.columns(2)

        with col1:
            st.subheader("👤 User1 Results") 
            st.metric(label="Inventory Status", value=user_1_output.get("inventory_log"))
            st.json(user_1_output)

        with col2:
            st.subheader("👤 User 2 Results")
            st.metric(label="Inventory Status", value=user_2_output.get("inventory_log"))
            st.json(user_2_output)
