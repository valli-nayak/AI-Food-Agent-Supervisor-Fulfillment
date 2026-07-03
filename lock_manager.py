import os
import time
import pandas as pd

class CSVInventoryLockManager:
    def __init__(self, csv_path:str="inventory.csv", lock_name:str="inventory_lock.lock"):
        self.csv_path = csv_path
        self.lock_path = lock_name

    def acquire_lease(self, dish_name:str, client_token:str, timeout_sec:float=15.0) -> str:
        """Attempts an exclusive local file system lock to isolate the CSV record."""
        start_time = time.time()
        normalized_dish = dish_name.lower().strip()

        while time.time() - start_time < timeout_sec:
            try:
                # 'x' mode fails atomically if file already exists (Concurrency Barrier)
                with open(self.lock_path, "x") as f:
                    f.write(client_token)

                df = pd.read_csv(self.csv_path)
                row = df[df['dish_name'].str.lower() == normalized_dish]

                if row.empty:
                    self.release_lock(client_token)
                    return "OUT_OF_STOCK"
                
                available_stock = int(row['total_available'].values[0])

                if available_stock <= 0:
                    self.release_lock(client_token)
                    return "OUT_OF_STOCK"
                
                return "SUCCESS"
            except FileExistsError:
                print("File Exists")
                time.sleep(0.05)
            except Exception as e:
                print(f"❌ Internal Lock Manager Crash: {e}")
                self.release_lock(client_token)
                return "CONFLICT_LOCKED"
            
        return "CONFLICT_LOCKED"
    
    def commit_deduction(self, dish_name:str, client_token:str):
        """Deducts stock balances permanently inside the csv record and frees the lock."""
        normalized_dish = dish_name.lower().strip()
        try:
            if os.path.exists(self.csv_path):
                df = pd.read_csv(self.csv_path)
                df.loc[df['dish_name'].str.lower() == normalized_dish, 'total_available'] -= 1
                df.to_csv(self.csv_path, index=False)
        finally:
            self.release_lock(client_token)

    def release_lock(self, client_token:str):
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r") as f:
                    current_owner = f.read().strip()

                if current_owner == client_token:
                    os.remove(self.lock_path)
                    print(f"✅ Lock safely released for token: {client_token}")
                else:
                    print(f"🛑 Security Blocked: Token {client_token} tried to delete a lock owned by {current_owner}!")
            except OSError as e:
                print(f"⚠️ Warning: Failed to delete lock file on the hard drive. Reason: {e}")
                